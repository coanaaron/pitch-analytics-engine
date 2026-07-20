import sqlite3
import argparse
from parser import BaseballParser

def setup_database(db_name: str):
    """
    Creates the SQLite tables if they don't already exist.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            pitcher TEXT,
            handedness TEXT,
            date TEXT,
            opponent TEXT,
            stadium TEXT,
            PRIMARY KEY (pitcher, date)
        )
        ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pitch_metrics (
            pitcher TEXT,
            date TEXT,
            TaggedPitchType TEXT,
            Pitch_Count INTEGER,
            Avg_Velo REAL,
            Max_Velo REAL,
            Strike_Count INTEGER,
            Whiff_Count INTEGER,
            Whiff_Pct REAL,
            CSW_Pct REAL,
            Avg_Spin REAL,
            Avg_Ver_Break REAL,
            Avg_Hor_Break REAL,
            Avg_VAA REAL,
            Horz_Rel REAL,
            Vert_Rel REAL,
            Ext REAL,
            Hard_Hit INTEGER,
            In_Play INTEGER,
            Spin_Axis REAL,
            PRIMARY KEY (pitcher, date, TaggedPitchType),
            FOREIGN KEY(pitcher, date) REFERENCES metadata(pitcher, date)
        )
        ''')

    conn.commit()
    return conn


def main():
    arg_parser = argparse.ArgumentParser(description="Orchestrate TrackMan data to SQLite pipeline.")
    arg_parser.add_argument('--file', type=str, required = True, help = "Path to raw TrackMan CSV")
    arg_parser.add_argument('--db', type=str, default="baseball_analytics.db", help="Target SQLite database name")
    args = arg_parser.parse_args()

    print(f"Initializing parser for: {args.file}")

    parser = BaseballParser(args.file)
    parser.load_data()

    pitchers = parser.get_pitcher_names()
    if not pitchers:
        print("No pitcher data found in file. Exiting.")
        return
    
    print(f"Found {len(pitchers)} pitchers to process.")

    conn = setup_database(args.db)
    cursor = conn.cursor()

    for pitcher in pitchers:
        print(f"Processing {pitcher}...")

        meta = parser.get_metadata(pitcher)
        if meta:
            cursor.execute('''
                INSERT OR REPLACE INTO metadata (pitcher, handedness, date, opponent, stadium)
                VALUES (?, ?, ?, ?, ?)
            ''', (meta[0], meta[1], meta[2], meta[3], meta[4]))

        metrics = parser.calculate_pitch_metrics(pitcher)
        if not metrics.empty:
            metrics['pitcher'] = pitcher
            dates = metrics['Date'].unique().tolist()
            for date in dates:
                cursor.execute("DELETE FROM pitch_metrics WHERE pitcher = ? AND date = ?", (pitcher, date))
            
            metrics.to_sql('pitch_metrics', conn, if_exists='append', index=False)

    conn.commit()
    conn.close()

    print(f"Pipeline complete! Raw data successfully aggregated and dumped into '{args.db}'")

if __name__ == "__main__":
        main()
