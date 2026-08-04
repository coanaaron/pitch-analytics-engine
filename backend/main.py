from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import date, time
import pandas as pd
import numpy as np

from database import get_db
from schemas import MetaDataResponse, BoxScoreResponse, PitchMetricsResponse
from run_pipeline import process_dataframe_and_store

app = FastAPI(
    title="Baseball Analytics Pipeline API",
    description="REST API for serving pitch tracking, box score, and metadata analytics",
    version="1.0.0"
)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://*.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get(
    "/api/v1/metadata",
    response_model=List[MetaDataResponse],
    summary="Get Game Metadata",
    tags=["Metadata"]
)

def get_metadata(
    game_i_d: Optional[str] = Query(None, description="Filter by Game ID"),
    game_date: Optional[date] = Query(None, description="Filter by game date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Retrieves game metadata. Optionally filter by a specific date or game ID.
    """
    query = "SELECT * FROM metadata WHERE 1=1"
    params = {}

    if game_i_d:
        query += " AND game_i_d = :game_i_d"
        params["game_i_d"] = game_i_d
    elif game_date:
        query += " AND date = :game_date"
        params["game_date"] = game_date

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
    game_i_d: Optional[str] = Query(None, description="Filter by Game ID"),
    game_date: Optional[date] = Query(None, description="Game date"),
    db: Session = Depends(get_db)
):
    """
    Retrieves game box score. Optionally filter by a specific date or game ID.
    """

    query = "SELECT * FROM box_scores WHERE 1=1"
    params = {}

    if game_i_d:
        query += " AND game_i_d = :game_i_d"
        params["game_i_d"] = game_i_d
    elif game_date:
        query += " AND date = :game_date"
        params["game_date"] = game_date
    
    df = pd.read_sql(text(query), con=db.connection(), params=params)

    if df.empty:
        return []
    
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
    game_i_d: Optional[str] = Query(None, description="Filter by Game ID"),
    game_date: Optional[date] = Query(None, description="Game date"),
    db: Session = Depends(get_db)
):
    """
    Retrieves pitch metrics. Optionally filter by a specific date or game ID.
    """

    query = "SELECT * FROM pitch_metrics WHERE 1=1"
    params = {}

    if game_i_d:
        query += " AND game_i_d = :game_i_d"
        params["game_i_d"] = game_i_d
    elif game_date:
        query += " AND date = :game_date"
        params["game_date"] = game_date
    
    df = pd.read_sql(text(query), con=db.connection(), params=params)

    if df.empty:
        return[]
    
    df["date"] = df["date"].astype(str)
    df["time"] = df["time"].astype(str)
    
    return df.to_dict(orient="records")


@app.post(
    "/api/v1/upload",
    summary="Upload and Process TrackMan CSV",
    tags=["Ingestion"]
)

async def upload_trackman_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    '''
    Parses an uploaded TrackMan CSV file, calculates pitch metrics/box scores,
    upserts all records into PostgreSQL, and returns the parsed report data.
    '''

    df = pd.read_csv(file.file)
    processed_pitchers = process_dataframe_and_store(df)

    if not processed_pitchers:
        raise HTTPException(
            status_code=400,
            detail="No valid pitcher data found in the uploaded CSV."
        )

    game_id = None
    if "GameID" in df.columns:
        game_id = str(df["GameID"].iloc[0])
    elif "game_i_d" in df.columns:
        game_id = str(df["game_i_d"].iloc[0])

    metadata_list = get_metadata(game_i_d=game_id, game_date=None, db=db) 
    box_score_list = get_box_score(game_i_d=game_id, game_date=None, db=db)
    pitch_metrics_list = get_pitch_metrics(game_i_d=game_id, game_date=None, db=db)

    return {
        "metadata": metadata_list if metadata_list else [],
        "box_score": box_score_list if box_score_list else [],
        "pitch_metrics": pitch_metrics_list
    }