import pandas as pd
import numpy as np
import re

class BaseballParser:

    def __init__(self, file_path: str):
        """
        Initializes the parser with the path to the user's raw Trackman file.
        """
        self.file_path = file_path
        self.df = None

    def load_data(self) -> pd.DataFrame:
        """
        Loads the raw CSV into a pandas DataFrame.
        """
        try:
            self.df = pd.read_csv(self.file_path)
            self.df.columns = [
                re.sub(r'(?<!^)(?=[A-Z])', '_', col).lower().replace(' ', '_')
                for col in self.df.columns
            ]
            return self.df
        except Exception as e:
            print(f"Error reading file {self.file_path}: {e}")
            raise

    # So user can choose pitcher from dropdown in UI
    def get_pitcher_names(self) -> list:
        """
        Helper to return a list of unique pitcher names found in the dataset.
        """
        if self.df is None or 'pitcher' not in self.df.columns:
            return []
        return sorted(self.df['pitcher'].dropna().unique().tolist())
    

    def calculate_pitch_metrics(self, pitcher_name: str) -> pd.DataFrame:
        """
        Filters data for a specific pitcher, applies trackman data filtering,
        aggregates pitch-type metrics, and calculates advanced stats in a clean layout.
        """

        if self.df is None or self.df.empty:
            return pd.DataFrame()
        
        filtered_df = self.df[self.df['pitcher'] == pitcher_name]
        total_pitches = len(filtered_df)

        if total_pitches == 0:
            return pd.DataFrame(columns=['tagged_pitch_type', 'pitch_count', 'avg_velo', 'max_velo', 'strike_count', 'whiff_count', 'whiff_pct', 'csw_pct', 'avg_spin', 'avg_ver_break', 'avg_hor_break', 'avg_vaa', 'horz_rel', 'vert_rel', 'ext', 'hard_hit', 'in_play', 'spin_axis'])
        
        # Filter out potential misreads (low pitch count threshold)
        if total_pitches > 15:
            pitch_counts = filtered_df['tagged_pitch_type'].value_counts()
            valid_p_types = pitch_counts[pitch_counts >= (total_pitches * 0.05)].index
            filtered_df = filtered_df[filtered_df['tagged_pitch_type'].isin(valid_p_types)].copy()

        # Define custom categorical row order for pitch types
        pitch_order = ['Fastball', 'Sinker', 'Cutter', 'Slider', 'Sweeper', 'Curveball', 'ChangeUp', 'Splitter']
        filtered_df['tagged_pitch_type'] = pd.Categorical(
            filtered_df['tagged_pitch_type'], 
            categories=pitch_order, 
            ordered=True
        )

        swings = ['StrikeSwinging', 'InPlay', 'FoulBallNotFieldable']
        filtered_df['is_swing'] = filtered_df['pitch_call'].isin(swings)
        filtered_df['is_swinging_strike'] = filtered_df['pitch_call'] == 'StrikeSwinging'
        filtered_df['is_called_strike'] = filtered_df['pitch_call'] == 'StrikeCalled'
        
        strikes = ['StrikeSwinging', 'StrikeCalled', 'InPlay', 'FoulBallNotFieldable']
        filtered_df['is_strike'] = filtered_df['pitch_call'].isin(strikes)
        filtered_df['is_in_play'] = filtered_df['pitch_call'] == 'InPlay'
        
        if 'exit_speed' in filtered_df.columns:
            filtered_df["is_hard_hit"] = filtered_df["exit_speed"] >= 95
        else:
            filtered_df["is_hard_hit"] = False

        summary = filtered_df.groupby(['pitcher', 'date', 'tagged_pitch_type'], observed=True).agg(
            time=('time', 'first'),
            pitch_count=('rel_speed', 'count'),
            avg_velo=('rel_speed', 'mean'),
            max_velo=('rel_speed', 'max'),
            strike_count=('is_strike', 'sum'),
            whiff_count=('is_swinging_strike', 'sum'),
            swing_count=('is_swing', 'sum'),
            called_strike_count=('is_called_strike', 'sum'),
            avg_spin=('spin_rate', 'mean'),
            avg_ver_break=('induced_vert_break', 'mean'),
            avg_hor_break=('horz_break', 'mean'),
            avg_vaa=('vert_appr_angle', 'mean'),
            horz_rel=('rel_side', 'mean'),
            vert_rel=('rel_height', 'mean'),
            ext=('extension', 'mean'),
            hard_hit=('is_hard_hit', 'sum'),
            in_play=('is_in_play', 'sum'),
            spin_axis=('spin_axis', 'mean')
        ).reset_index()

        summary['whiff_pct'] = (summary['whiff_count'] / summary['swing_count'].replace(0, 1) * 100).round(1)
        summary['csw_pct'] = ((summary['whiff_count'] + summary['called_strike_count']) / summary['pitch_count'].replace(0, 1) * 100).round(1)

        ordered_columns = [
            'pitcher', 'date', 'time', 'tagged_pitch_type', 'pitch_count', 'avg_velo', 'max_velo',
            'strike_count', 'whiff_count', 'whiff_pct', 'csw_pct',
            'avg_spin', 'avg_ver_break', 'avg_hor_break', 'avg_vaa',
            'horz_rel', 'vert_rel', 'ext', 'hard_hit', 'in_play', 'spin_axis'
        ]
        summary = summary[ordered_columns]

        rounding_map = {
            'avg_velo': 1, 'max_velo': 1, 'avg_spin': 0,
            'avg_ver_break': 1, 'avg_hor_break': 1, 'avg_vaa': 1,
            'horz_rel': 2, 'vert_rel': 2, 'ext': 2, 'spin_axis': 0
        }
        summary = summary.round(rounding_map)

        return summary.sort_index().reset_index(drop=True)





    # Work in progress
    def calculate_earned_runs(self) -> int:
        """
        Implements a sequential state machine that reconstructs baseball half-innings 
        to accurately distinguish between earned and unearned runs by evaluating 
        actual versus expected outs on a row-by-row basis.
        """

        filtered_df = self.df

        current_half_inning = None
        actual_outs = 0
        expected_outs = 0
        earned_runs = 0

        for index, row in filtered_df.iterrows():
            inning_num = row['Inning']
            half = row['Top/Bottom']

            this_row_half_inning = f"{inning_num}_{half}"

            if this_row_half_inning != current_half_inning:
                current_half_inning = this_row_half_inning
                actual_outs = 0
                expected_outs = 0
            
            outs_this_play = int(row['OutsOnPlay'])

            if row["PlayResult"] == 'Error':
                expected_outs_this_play = outs_this_play + 1
            else:
                expected_outs_this_play = outs_this_play

            actual_outs += outs_this_play
            expected_outs += expected_outs_this_play

            if expected_outs >= 3 and actual_outs < 3:
                is_inning_reconstructed = True
            else:
                is_inning_reconstructed = False

            runs_on_play = int(row['RunsScored'])

            if runs_on_play > 0:
                if is_inning_reconstructed == False:
                    earned_runs += runs_on_play
                

            if actual_outs >= 3:
                actual_outs = 0
                expected_outs = 0
        
        return earned_runs





    def start_grade_calculator(self, pitcher_df: pd.DataFrame) -> str:
        """
        Calculates a game start grade using the performance regression equation.
        Maps a calculated numerical score to a letter grade array scale from 0 to 12.
        """

        if pitcher_df.empty:
            return ""

        total_outs = pitcher_df["outs_on_play"].sum()
        ip_decimal = total_outs / 3.0

        r = pitcher_df["runs_scored"].sum()
        k = pitcher_df["kor_bb"].eq("Strikeout").sum()
        bb = pitcher_df["kor_bb"].eq("Walk").sum()
        hbp = pitcher_df["pitch_call"].eq("HitByPitch").sum()

        h = pitcher_df["play_result"].isin(["Single", "Double", "Triple", "HomeRun"]).sum()
        two_b = pitcher_df["play_result"].eq("Double").sum()
        three_b = pitcher_df["play_result"].eq("Triple").sum()
        hr = pitcher_df["play_result"].eq("HomeRun").sum()

        raw_score = (
            4.03 +
            (0.95 * ip_decimal) +
            (-0.79 * r) +
            (0.16 * k) +
            (-0.22 * bb) +
            (0.02 * hbp) +
            (-0.15 * h) +
            (-0.08 * two_b) +
            (-0.22 * three_b) +
            (-0.14 * hr)
        )

        integer_grade = int(np.clip(round(raw_score), 0, 12))

        grade_mapping = {
            12: "A",
            11: "A-",
            10: "B+",
            9: "B",
            8: "B-",
            7: "C+",
            6: "C",
            5: "C-",
            4: "D+",
            3: "D",
            2: "D-",
            1: "F+",
            0: "F"
        }

        return grade_mapping.get(integer_grade)




    def calculate_box_score(self, pitcher_name: str, is_starter: bool = False) -> pd.DataFrame:
        """
        Filters data for a specific pitcher, applies trackman data filtering,
        aggregates box-score metrics, and integrates a start grade in a clean layout.
        """
        if self.df is None or self.df.empty:
            return pd.DataFrame()

        filtered_df = self.df[self.df['pitcher'] == pitcher_name]

        if filtered_df.empty:
            return pd.DataFrame(columns=[
                'pitcher', 'ip', 'h', 'r', '2b', '3b', 'hr', 'bb', 'hbp', 'k', 'pitches', 'start_grade'
            ])

        total_outs = filtered_df['outs_on_play'].sum()
        ip_full = total_outs // 3
        ip_partial = total_outs % 3
        ip_str = f"{ip_full}.{ip_partial}" if ip_partial > 0 else f"{ip_full}"

        h = filtered_df["play_result"].isin(["Single", "Double", "Triple", "HomeRun"]).sum()
        two_b = filtered_df["play_result"].eq("Double").sum()
        three_b = filtered_df["play_result"].eq("Triple").sum()
        hr = filtered_df["play_result"].eq("HomeRun").sum()

        bb = filtered_df["kor_bb"].eq("Walk").sum()
        k = filtered_df["kor_bb"].eq("Strikeout").sum()
        hbp = filtered_df["pitch_call"].eq("HitByPitch").sum()
        r = filtered_df["runs_scored"].sum()

        pitches = len(filtered_df)

        start_grade = self.start_grade_calculator(filtered_df) if is_starter else None

        box_score_df = pd.DataFrame([{
            "pitcher": pitcher_name,
            "ip": ip_str,
            "h": h,
            "r": r,
            "2b": two_b,
            "3b": three_b,
            "hr": hr,
            "bb": bb,
            "hbp": hbp,
            "k": k,
            "pitches": pitches,
            "start_grade": start_grade
        }])

        return box_score_df



    def get_metadata(self, pitcher_name: str) -> list:
        """
        Extracts raw game detail values for a pitcher to populate UI text fields directly.
        Returns an empty list if the pitcher is not found or data is missing.
        """

        if self.df is None or self.df.empty or 'pitcher' not in self.df.columns:
            return []

        filtered_df = self.df[self.df['pitcher'] == pitcher_name]
        if filtered_df.empty:
            return []

        first_pitch = filtered_df.iloc[0]
        batter_team = first_pitch.get('batter_team')
        opponent_str = f"vs {batter_team}" if batter_team else None
        handedness = first_pitch.get('pitcher_throws')

        if handedness and isinstance(handedness, str):
            hand_letter = handedness[0].upper()
            pitcher_throws_str = f"({hand_letter}HP)"
        else:
            pitcher_throws_str = None

        return [
            pitcher_name,
            pitcher_throws_str,
            first_pitch.get('date'),
            first_pitch.get('time'),
            opponent_str,
            first_pitch.get('stadium')
        ]



# splits_summary = filtered_df.groupby(['TaggedPitchType', 'BatterSide']).agg(
#     Pitch_Count = ('RelSpeed', 'count')
# )

# print(splits_summary)


# filtered_df['InZone'] = (
#     (filtered_df['PlateLocHeight'] >= 1.5) & (filtered_df['PlateLocHeight'] <= 3.5) &
#     (filtered_df['PlateLocSide'] >= -0.708) & (filtered_df['PlateLocSide'] <= 0.708) 
# )
