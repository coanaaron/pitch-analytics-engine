from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import date, time
import pandas as pd
import numpy as np

from database import get_db
from schemas import MetaDataResponse, BoxScoreResponse, PitchMetricsResponse

app = FastAPI(
    title="Baseball Analytics Pipeline API",
    description="REST API for serving pitch tracking, box score, and metadata analytics",
    version="1.0.0"
)

@app.get(
    "/api/v1/metadata",
    response_model=List[MetaDataResponse],
    summary="Get Game Metadata",
    tags=["Metadata"]
)

def get_metadata(
    game_date: Optional[date] = Query(None, description="Filter by game date (YYYY-MM-DD)"),
    game_time: Optional[time] = Query(None, description="Filter by start time (useful for doubleheaders)"),
    db: Session = Depends(get_db)
):
    """
    Retrieves game metadata. Optionally filter by a specific date and time.
    """
    query = "SELECT * FROM metadata WHERE 1=1"
    params = {}

    if game_date:
        query += " AND date = :game_date"
        params["game_date"] = game_date

    if game_time:
        query += " AND time = :game_time"
        params["game_time"] = game_time

    df = pd.read_sql(text(query), con=db.connection(), params=params)

    if df.empty:
        return []
    
    df["date"] = df["date"].astype(str)
    df["time"] = df["time"].astype(str)

    return df.to_dict(orient="records")



@app.get(
    "/api/v1/box-score",
    response_model=List[BoxScoreResponse],
    summary = "Calculate Game Box Score",
    tags=["Analytics"]
)

def get_box_score(
    game_date: date = Query(..., description="Game date"),
    game_time: Optional[time] = Query(None, description="Filter by start time (useful for doubleheaders)"),
    db: Session = Depends(get_db)
):
    """
    Retrieves game box score. Filter by a specific date and an optional time.
    """

    query = "SELECT * FROM box_scores WHERE date = :game_date"
    params = {"game_date": game_date}

    if game_time:
        query += " AND time = :game_time"
        params["game_time"] = game_time
    
    df = pd.read_sql(text(query), con=db.connection(), params=params)

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail="No box score found for specified date/time."
        )
    
    df["date"] = df["date"].astype(str)
    df["time"] = df["time"].astype(str)

    # For when start grade is null
    df = df.replace({np.nan: None})
    
    return df.to_dict(orient="records")


@app.get(
    "/api/v1/pitch-metrics",
    response_model=List[PitchMetricsResponse],
    summary = "Calculate Game Pitch Metrics",
    tags=["Analytics"]
)

def get_pitch_metrics(
    game_date: date = Query(..., description="Game date"),
    game_time: Optional[time] = Query(None, description="Filter by start time (useful for doubleheaders)"),
    db: Session = Depends(get_db)
):
    """
    Retrieves pitch metrics. Filter by a specific date and an optional time.
    """

    query = "SELECT * FROM pitch_metrics WHERE date = :game_date"
    params = {"game_date": game_date}

    if game_time:
        query += " AND time = :game_time"
        params["game_time"] = game_time
    
    df = pd.read_sql(text(query), con=db.connection(), params=params)

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail="No pitch metrics found for specified date/time."
        )
    
    df["date"] = df["date"].astype(str)
    df["time"] = df["time"].astype(str)
    
    return df.to_dict(orient="records")