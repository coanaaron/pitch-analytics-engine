import pandas as pd
import numpy as np

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
            return self.df
        except Exception as e:
            print(f"Error reading file {self.file_path}: {e}")
            raise

    # So user can choose pitcher from dropdown in UI
    def get_pitcher_names(self) -> list:
        """
        Helper to return a list of unique pitcher names found in the dataset.
        """
        if self.df is None or 'Pitcher' not in self.df.columns:
            return []
        return sorted(self.df['Pitcher'].dropna().unique().tolist())
    

    def calculate_pitch_metrics(self, pitcher_name: str) -> pd.DataFrame:
        """
        Filters data for a specific pitcher, applies trackman data filtering,
        aggregates pitch-type metrics, and calculates advanced stats in a clean layout.
        """

        if self.df is None or self.df.empty:
            return pd.DataFrame()
        
        filtered_df = self.df[self.df['Pitcher'] == pitcher_name]
        total_pitches = len(filtered_df)

        if total_pitches == 0:
            return pd.DataFrame(columns=['TaggedPitchType', 'Pitch_Count', 'Avg_Velo', 'Max_Velo', 'Strike_Count', 'Whiff_Count', 'Whiff_Pct', 'CSW_Pct', 'Avg_Spin', 'Avg_Ver_Break', 'Avg_Hor_Break', 'Avg_VAA', 'Horz_Rel', 'Vert_Rel', 'Ext', 'Hard_Hit', 'In_Play', 'Spin_Axis'])
        
        # Filter out potential misreads (low pitch count threshold)
        if total_pitches > 15:
            pitch_counts = filtered_df['TaggedPitchType'].value_counts()
            valid_p_types = pitch_counts[pitch_counts >= (total_pitches * 0.05)].index
            filtered_df = filtered_df[filtered_df['TaggedPitchType'].isin(valid_p_types)].copy()

        # Define custom categorical row order for pitch types
        pitch_order = ['Fastball', 'Sinker', 'Cutter', 'Slider', 'Sweeper', 'Curveball', 'ChangeUp', 'Splitter']
        filtered_df['TaggedPitchType'] = pd.Categorical(
            filtered_df['TaggedPitchType'], 
            categories=pitch_order, 
            ordered=True
        )

        swings = ['StrikeSwinging', 'InPlay', 'FoulBallNotFieldable']
        filtered_df['IsSwing'] = filtered_df['PitchCall'].isin(swings)
        filtered_df['IsSwingingStrike'] = filtered_df['PitchCall'] == 'StrikeSwinging'
        filtered_df['IsCalledStrike'] = filtered_df['PitchCall'] == 'StrikeCalled'
        
        strikes = ['StrikeSwinging', 'StrikeCalled', 'InPlay', 'FoulBallNotFieldable']
        filtered_df['IsStrike'] = filtered_df['PitchCall'].isin(strikes)
        filtered_df['IsInPlay'] = filtered_df['PitchCall'] == 'InPlay'
        
        if 'ExitSpeed' in filtered_df.columns:
            filtered_df["IsHardHit"] = filtered_df["ExitSpeed"] >= 95
        else:
            filtered_df["IsHardHit"] = False

        summary = filtered_df.groupby(['Pitcher', 'Date', 'TaggedPitchType'], observed=True).agg(
            Pitch_Count=('RelSpeed', 'count'),
            Avg_Velo=('RelSpeed', 'mean'),
            Max_Velo=('RelSpeed', 'max'),
            Strike_Count=('IsStrike', 'sum'),
            Whiff_Count=('IsSwingingStrike', 'sum'),
            Swing_Count=('IsSwing', 'sum'),
            Called_Strike_Count=('IsCalledStrike', 'sum'),
            Avg_Spin=('SpinRate', 'mean'),
            Avg_Ver_Break=('InducedVertBreak', 'mean'),
            Avg_Hor_Break=('HorzBreak', 'mean'),
            Avg_VAA=('VertApprAngle', 'mean'),
            Horz_Rel=('RelSide', 'mean'),
            Vert_Rel=('RelHeight', 'mean'),
            Ext=('Extension', 'mean'),
            Hard_Hit=('IsHardHit', 'sum'),
            In_Play=('IsInPlay', 'sum'),
            Spin_Axis=('SpinAxis', 'mean')
        ).reset_index()

        summary['Whiff_Pct'] = (summary['Whiff_Count'] / summary['Swing_Count'].replace(0, 1) * 100).round(1)
        summary['CSW_Pct'] = ((summary['Whiff_Count'] + summary['Called_Strike_Count']) / summary['Pitch_Count'].replace(0, 1) * 100).round(1)

        ordered_columns = [
            'Pitcher', 'Date', 'TaggedPitchType', 'Pitch_Count', 'Avg_Velo', 'Max_Velo',
            'Strike_Count', 'Whiff_Count', 'Whiff_Pct', 'CSW_Pct', 
            'Avg_Spin', 'Avg_Ver_Break', 'Avg_Hor_Break', 'Avg_VAA', 
            'Horz_Rel', 'Vert_Rel', 'Ext', 'Hard_Hit', 'In_Play', 'Spin_Axis'
        ]
        summary = summary[ordered_columns]

        rounding_map = {
            'Avg_Velo': 1, 'Max_Velo': 1, 'Avg_Spin': 0, 
            'Avg_Ver_Break': 1, 'Avg_Hor_Break': 1, 'Avg_VAA': 1,
            'Horz_Rel': 2, 'Vert_Rel': 2, 'Ext': 2, 'Spin_Axis': 0
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
        
        total_outs = pitcher_df["OutsOnPlay"].sum()
        ip_decimal = total_outs / 3.0

        r = pitcher_df["RunsScored"].sum() 
        k = pitcher_df["KorBB"].eq("Strikeout").sum()
        bb = pitcher_df["KorBB"].eq("Walk").sum()
        hbp = pitcher_df["PitchCall"].eq("HitByPitch").sum()

        h = pitcher_df["PlayResult"].isin(["Single", "Double", "Triple", "HomeRun"]).sum()
        two_b = pitcher_df["PlayResult"].eq("Double").sum()
        three_b = pitcher_df["PlayResult"].eq("Triple").sum()
        hr = pitcher_df["PlayResult"].eq("HomeRun").sum()

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
        
        filtered_df = self.df[self.df['Pitcher'] == pitcher_name]

        if filtered_df.empty:
            return pd.DataFrame(columns=['Pitcher', 'IP', 'H', 'R', '2B', '3B', 'HR', 'BB', 'HBP', 'K', 'Pitches', 'Start_Grade'])
        
        total_outs = filtered_df['OutsOnPlay'].sum()
        ip_full = total_outs // 3
        ip_partial = total_outs % 3
        ip_str = f"{ip_full}.{ip_partial}" if ip_partial > 0 else f"{ip_full}"

        h = filtered_df["PlayResult"].isin(["Single", "Double", "Triple", "HomeRun"]).sum()
        two_b = filtered_df["PlayResult"].eq("Double").sum()
        three_b = filtered_df["PlayResult"].eq("Triple").sum()
        hr = filtered_df["PlayResult"].eq("HomeRun").sum()

        bb = filtered_df["KorBB"].eq("Walk").sum()
        k = filtered_df["KorBB"].eq("Strikeout").sum()
        hbp = filtered_df["PitchCall"].eq("HitByPitch").sum()
        r = filtered_df["RunsScored"].sum()

        pitches = len(filtered_df)

        start_grade = start_grade_calculator(filtered_df) if is_starter else None

        box_score_df = pd.DataFrame([{
            "IP": ip_str,
            "H": h,
            "R": r,
            "2B": two_b,
            "3B": three_b,
            "HR": hr,
            "BB": bb,
            "HBP": hbp,
            "K": k,
            "Pitches": pitches,
            "Start_Grade": start_grade
        }])
        
        return box_score_df



    def get_metadata(self, pitcher_name: str) -> list:
        """
        Extracts raw game detail values for a pitcher to populate UI text fields directly.
        Returns an empty list if the pitcher is not found or data is missing.
        """

        if self.df is None or self.df.empty or 'Pitcher' not in self.df.columns:
            return []
        
        filtered_df = self.df[self.df['Pitcher'] == pitcher_name]
        if filtered_df.empty:
            return []
        
        first_pitch = filtered_df.iloc[0]
        batter_team = first_pitch.get('BatterTeam')
        opponent_str = f"vs {batter_team}" if batter_team else None
        handedness = first_pitch.get('PitcherThrows')
        
        if handedness and isinstance(handedness, str):
            hand_letter = handedness[0].upper()
            pitcher_throws_str = f"({hand_letter}HP)"
        else:
            pitcher_throws_str = None

        return [
            pitcher_name,
            pitcher_throws_str,
            first_pitch.get('Date'),
            opponent_str,
            first_pitch.get('Stadium')
        ]



# splits_summary = filtered_df.groupby(['TaggedPitchType', 'BatterSide']).agg(
#     Pitch_Count = ('RelSpeed', 'count')
# )

# print(splits_summary)


# filtered_df['InZone'] = (
#     (filtered_df['PlateLocHeight'] >= 1.5) & (filtered_df['PlateLocHeight'] <= 3.5) &
#     (filtered_df['PlateLocSide'] >= -0.708) & (filtered_df['PlateLocSide'] <= 0.708) 
# )
