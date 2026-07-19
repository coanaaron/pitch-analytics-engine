import pandas as pd
import numpy as np


def calculate_pitch_metrics(df: pd.DataFrame, pitcher_name: str) -> pd.DataFrame:
    """
    Filters data for a specific pitcher, applies trackman data filtering,
    aggregates pitch-type metrics, and calculates advanced stats in a clean layout.
    """
    
    filtered_df = df[df['Pitcher'] == pitcher_name].copy()
    total_pitches = len(filtered_df)
    
    # Filter out potential misreads (low pitch count threshold)
    if total_pitches > 15:
        pitch_counts = filtered_df['TaggedPitchType'].value_counts()
        valid_p_types = pitch_counts[pitch_counts >= (total_pitches * 0.05)].index
        filtered_df = filtered_df[filtered_df['TaggedPitchType'].isin(valid_p_types)].copy()

    # Define custom categorical row order for pitch types
    pitch_order = ['Fastball', 'Sinker', 'Cutter', 'Slider', 'Curveball', 'ChangeUp', 'Splitter']
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

    summary = filtered_df.groupby('TaggedPitchType', observed=True).agg(
        Pitch_Count=('RelSpeed', 'count'),
        Avg_Velo=('RelSpeed', 'mean'),
        Max_Velo=('RelSpeed', 'max'),
        Strike_Count=('IsStrike', 'sum'),
        Whiff_Count=('IsSwingingStrike', 'sum'),
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
    )

    swings_by_type = filtered_df.groupby('TaggedPitchType', observed=False)['IsSwing'].sum()
    whiffs_by_type = filtered_df.groupby('TaggedPitchType', observed=False)['IsSwingingStrike'].sum()
    called_strikes_by_type = filtered_df.groupby('TaggedPitchType', observed=False)['IsCalledStrike'].sum()

    summary['Whiff_Pct'] = (whiffs_by_type / swings_by_type.replace(0, 1) * 100).round(1)
    summary['CSW_Pct'] = ((whiffs_by_type + called_strikes_by_type) / summary['Pitch_Count'] * 100).round(1)

    ordered_columns = [
        'Pitch_Count', 'Avg_Velo', 'Max_Velo', 'Strike_Count', 'Whiff_Count', 
        'Whiff_Pct', 'CSW_Pct', 
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

    return summary.sort_index().reset_index()




def calculate_earned_runs(df):
    """
    Implements a sequential state machine that reconstructs baseball half-innings 
    to accurately distinguish between earned and unearned runs by evaluating 
    actual versus expected outs on a row-by-row basis.
    """

    filtered_df = df.copy()

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


df = pd.read_csv('raw_pitch_data.csv')

pitch_metrics = calculate_pitch_metrics(df, 'Kruzan, Marcus')
print(pitch_metrics)


# splits_summary = filtered_df.groupby(['TaggedPitchType', 'BatterSide']).agg(
#     Pitch_Count = ('RelSpeed', 'count')
# )

# print(splits_summary)


# filtered_df['InZone'] = (
#     (filtered_df['PlateLocHeight'] >= 1.5) & (filtered_df['PlateLocHeight'] <= 3.5) &
#     (filtered_df['PlateLocSide'] >= -0.708) & (filtered_df['PlateLocSide'] <= 0.708) 
# )
