import argparse
from sqlalchemy import text
from database import engine
from parser import BaseballParser

def setup_database():
    """
    Creates the PostgreSQL tables in Neon if they don't already exist.
    """
    
    with engine.begin() as conn:

        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS metadata (
                game_i_d TEXT,
                pitcher TEXT,
                handedness TEXT,
                date DATE,
                time TIME,
                opponent TEXT,
                stadium TEXT,
                home_team TEXT,
                away_team TEXT,
                PRIMARY KEY (game_i_d, pitcher) 
            );
        '''))

        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS pitch_metrics (
                game_i_d TEXT,
                pitcher TEXT,
                date DATE,
                time TIME,
                tagged_pitch_type TEXT,
                pitch_count INTEGER,
                avg_velo REAL,
                max_velo REAL,
                strike_count INTEGER,
                whiff_count INTEGER,
                whiff_pct REAL,
                csw_pct REAL,
                avg_spin REAL,
                avg_ver_break REAL,
                avg_hor_break REAL,
                avg_vaa REAL,
                horz_rel REAL,
                vert_rel REAL,
                ext REAL,
                hard_hit INTEGER,
                in_play INTEGER,
                spin_axis REAL,
                PRIMARY KEY (game_i_d, pitcher, tagged_pitch_type) 
            );
        '''))

        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS box_scores (
                game_i_d TEXT,
                pitcher TEXT,
                date DATE,
                time TIME,
                ip TEXT,
                h INTEGER,
                r INTEGER,
                two_b INTEGER,
                three_b INTEGER,
                hr INTEGER,
                bb INTEGER,
                hbp INTEGER,
                k INTEGER,
                pitches INTEGER,
                start_grade TEXT,
                PRIMARY KEY (game_i_d, pitcher)
            );
        '''))



def process_dataframe_and_store(df):
    '''
    Core pipeline logic: Accepts an already loaded/cleaned DataFrame,
    calculates metrics for all pitchers, and upserts them into Postgres.
    '''
    
    parser = BaseballParser(file_path="")
    
    import re
    df.columns = [
        re.sub(r'(?<!^)(?=[A-Z])', '_', col).lower().replace(' ', '_')
        for col in df.columns
    ]
    parser.df = df
    
    pitchers = parser.get_pitcher_names()
    if not pitchers:
        print("No pitcher data found.")
        return []

    setup_database()

    with engine.begin() as conn:

        for pitcher in pitchers:

            meta = parser.get_metadata(pitcher)
            if meta:
                upsert_query = text('''
                    INSERT INTO metadata (game_i_d, pitcher, handedness, date, time, opponent, stadium, home_team, away_team)
                    VALUES (:game_i_d, :pitcher, :handedness, :date, :time, :opponent, :stadium, :home_team, :away_team)
                    ON CONFLICT (game_i_d, pitcher) 
                    DO UPDATE SET 
                        handedness = EXCLUDED.handedness,
                        date = EXCLUDED.date,
                        time = EXCLUDED.time,
                        opponent = EXCLUDED.opponent,       
                        stadium = EXCLUDED.stadium,
                        home_team = EXCLUDED.home_team,
                        away_team = EXCLUDED.away_team;
                ''')
                conn.execute(upsert_query, {
                    "game_i_d": meta[0],
                    "pitcher": meta[1],
                    "handedness": meta[2],
                    "date": str(meta[3]),
                    "time": str(meta[4]),
                    "opponent": meta[5],
                    "stadium": meta[6],
                    "home_team": meta[7],
                    "away_team": meta[8]
                })

            metrics = parser.calculate_pitch_metrics(pitcher)
            if not metrics.empty:
                metrics.columns = metrics.columns.str.lower()
                metrics['pitcher'] = pitcher

                metrics_upsert = text('''
                    INSERT INTO pitch_metrics (
                        game_i_d, pitcher, date, time, tagged_pitch_type, pitch_count, 
                        avg_velo, max_velo, strike_count, whiff_count, whiff_pct, 
                        csw_pct, avg_spin, avg_ver_break, avg_hor_break, avg_vaa, 
                        horz_rel, vert_rel, ext, hard_hit, in_play, spin_axis
                    ) VALUES (
                        :game_i_d, :pitcher, :date, :time, :tagged_pitch_type, :pitch_count, 
                        :avg_velo, :max_velo, :strike_count, :whiff_count, :whiff_pct, 
                        :csw_pct, :avg_spin, :avg_ver_break, :avg_hor_break, :avg_vaa, 
                        :horz_rel, :vert_rel, :ext, :hard_hit, :in_play, :spin_axis
                    )
                    ON CONFLICT (game_i_d, pitcher, tagged_pitch_type) 
                    DO UPDATE SET
                        date = EXCLUDED.date,
                        time = EXCLUDED.time,
                        pitch_count = EXCLUDED.pitch_count,
                        avg_velo = EXCLUDED.avg_velo,
                        max_velo = EXCLUDED.max_velo,
                        strike_count = EXCLUDED.strike_count,
                        whiff_count = EXCLUDED.whiff_count,
                        whiff_pct = EXCLUDED.whiff_pct,
                        csw_pct = EXCLUDED.csw_pct,
                        avg_spin = EXCLUDED.avg_spin,
                        avg_ver_break = EXCLUDED.avg_ver_break,
                        avg_hor_break = EXCLUDED.avg_hor_break,
                        avg_vaa = EXCLUDED.avg_vaa,
                        horz_rel = EXCLUDED.horz_rel,
                        vert_rel = EXCLUDED.vert_rel,
                        ext = EXCLUDED.ext,
                        hard_hit = EXCLUDED.hard_hit,
                        in_play = EXCLUDED.in_play,
                        spin_axis = EXCLUDED.spin_axis;
                ''')

                conn.execute(metrics_upsert, metrics.to_dict(orient='records'))

            box_score = parser.calculate_box_score(pitcher)
            if not box_score.empty:
                box_score.columns = box_score.columns.str.lower()
                box_score = box_score.rename(columns={'2b': 'two_b', '3b': 'three_b'})
                box_score['date'] = box_score['date'].astype(str)
                box_score['time'] = box_score['time'].astype(str)

                box_upsert = text('''
                    INSERT INTO box_scores (
                        game_i_d, pitcher, date, time, ip, h, r, two_b, three_b, hr, bb, hbp, k, pitches, start_grade
                    )
                    VALUES (
                        :game_i_d, :pitcher, :date, :time, :ip, :h, :r, :two_b, :three_b, :hr, :bb, :hbp, :k, :pitches, :start_grade
                    )
                    ON CONFLICT (game_i_d, pitcher)
                    DO UPDATE SET
                        date = EXCLUDED.date,
                        time = EXCLUDED.time,
                        ip = EXCLUDED.ip,
                        h = EXCLUDED.h,
                        r = EXCLUDED.r,
                        two_b = EXCLUDED.two_b,
                        three_b = EXCLUDED.three_b,
                        hr = EXCLUDED.hr,
                        bb = EXCLUDED.bb,
                        hbp = EXCLUDED.hbp,
                        k = EXCLUDED.k,
                        pitches = EXCLUDED.pitches,
                        start_grade = EXCLUDED.start_grade;
                ''')

                conn.execute(box_upsert, box_score.to_dict(orient='records'))

    return pitchers

def process_file_and_store(file_path: str):
    '''
    CLI wrapper: Loads raw file from path and runs storage pipeline.
    '''
    parser = BaseballParser(file_path)
    df = parser.load_data()
    return process_dataframe_and_store(df)
    

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Orchestrate TrackMan data to PostgreSQL pipeline.")
    arg_parser.add_argument('--file', type=str, required = True, help = "Path to raw TrackMan CSV")
    args = arg_parser.parse_args()

    print(f"Initializing parser for: {args.file}")
    process_file_and_store(args.file)
    print(f"Pipeline complete! Raw data successfully aggregated and dumped into PostgreSQL")
