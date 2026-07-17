import pandas as pd

try:
    df = pd.read_csv('raw_pitch_data.csv')

    print(df['Pitcher'].unique())

    filtered_df = df[df['Pitcher'] == 'Kruzan, Marcus'].copy()
    total_pitches = len(filtered_df)

    # To filter out potential misreads in trackman data
    if total_pitches > 15:
        pitch_counts = filtered_df['TaggedPitchType'].value_counts()
        valid_pitches = pitch_counts[pitch_counts >= (total_pitches * 0.05)].index
        filtered_df = filtered_df[filtered_df['TaggedPitchType'].isin(valid_pitches)]

    filtered_df['InZone'] = (
        (filtered_df['PlateLocHeight'] >= 1.5) & (filtered_df['PlateLocHeight'] <= 3.5) &
        (filtered_df['PlateLocSide'] >= -0.708) & (filtered_df['PlateLocSide'] <= 0.708) 
    )

    swings = ['StrikeSwinging', 'InPlay', 'FoulBallNotFieldable']
    filtered_df['IsSwing'] = filtered_df['PitchCall'].isin(swings)
    filtered_df['IsSwingingStrike'] = filtered_df['PitchCall'] == 'StrikeSwinging'
    filtered_df['IsCalledStrike'] = filtered_df['PitchCall'] == 'StrikeCalled'

    filtered_df['IsStrike'] = filtered_df['PitchCall'].isin(['StrikeSwinging', 'StrikeCalled', 'InPlay', 'FoulBallNotFieldable'])
    filtered_df['IsInPlay'] = filtered_df['PitchCall'] == 'InPlay'

    if 'ExitSpeed' in filtered_df.columns:
        filtered_df["IsHardHit"] = filtered_df["ExitSpeed"] >= 95
    else:
        filtered_df["IsHardHit"] = False

    summary = filtered_df.groupby('TaggedPitchType').agg(
        Pitch_Count = ('RelSpeed', 'count'),
        Avg_Velo = ('RelSpeed', 'mean'),
        Max_Velo = ('RelSpeed', 'max'),
        Strike_Count = ('IsStrike', 'sum'),
        Whiff_Count = ('IsSwingingStrike', 'sum'),
        Avg_Spin = ('SpinRate', 'mean'),
        Avg_Ver_Break = ('InducedVertBreak', 'mean'),
        Avg_Hor_Break = ('HorzBreak', 'mean'),
        Avg_VAA = ('VertApprAngle', 'mean'),
        Horz_Rel = ('RelSide', 'mean'),
        Vert_Rel = ('RelHeight', 'mean'),
        Ext = ('Extension', 'mean'),
        Hard_Hit = ('IsHardHit', 'sum'),
        In_Play = ('IsInPlay', 'sum'),
        Spin_Axis = ('SpinAxis', 'mean'),
        Zone_Pct = ('InZone', 'mean')
    )

    swings_by_type = filtered_df.groupby('TaggedPitchType')['IsSwing'].sum()
    whiffs_by_type = filtered_df.groupby('TaggedPitchType')['IsSwingingStrike'].sum()
    called_strikes_by_type = filtered_df.groupby('TaggedPitchType')['IsCalledStrike'].sum()

    summary['Whiff_Pct'] = whiffs_by_type / swings_by_type.replace(0,1)
    summary['CSW_Pct'] = (whiffs_by_type + called_strikes_by_type) / summary['Pitch_Count']

    print(summary)

    splits_summary = filtered_df.groupby(['TaggedPitchType', 'BatterSide']).agg(
        Pitch_Count = ('RelSpeed', 'count')
    )

    print(splits_summary)

except FileNotFoundError:
    print("Could not find raw_pitch_data.csv. Make sure the file is in the same" \
    "folder as this script!")

