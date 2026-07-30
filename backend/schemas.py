from pydantic import BaseModel, ConfigDict
from datetime import date, time
from typing import Optional

class MetaDataResponse(BaseModel):
    game_i_d: str
    pitcher: str
    handedness: Optional[str] = None
    date: date
    time: time
    opponent: Optional[str] = None
    stadium: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class BoxScoreResponse(BaseModel):
    game_i_d: str
    pitcher: str
    date: date
    time: time
    ip: Optional[str] = None
    h: Optional[int] = None
    r: Optional[int] = None
    two_b: Optional[int] = None
    three_b: Optional[int] = None
    hr: Optional[int] = None
    bb: Optional[int] = None
    hbp: Optional[int] = None
    k: Optional[int] = None
    pitches: Optional[int] = None
    start_grade: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class PitchMetricsResponse(BaseModel):
    game_i_d: str
    pitcher: str
    date: date
    time: time
    tagged_pitch_type: str
    pitch_count: Optional[int] = None
    avg_velo: Optional[float] = None
    max_velo: Optional[float] = None
    strike_count: Optional[int] = None
    whiff_count: Optional[int] = None
    whiff_pct: Optional[float] = None
    csw_pct: Optional[float] = None
    avg_spin: Optional[float] = None
    avg_ver_break: Optional[float] = None
    avg_hor_break: Optional[float] = None
    avg_vaa: Optional[float] = None
    horz_rel: Optional[float] = None
    vert_rel: Optional[float] = None
    ext: Optional[float] = None
    hard_hit: Optional[int] = None
    in_play: Optional[int] = None
    spin_axis: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)