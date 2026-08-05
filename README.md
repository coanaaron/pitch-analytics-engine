# Baseball Analytics Pipeline

A full-stack tool for ingesting TrackMan pitch-tracking CSV exports, calculating pitch metrics and box scores, storing them in PostgreSQL, and generating printable pitcher scouting/report cards through a React frontend.

Built for University of Minnesota baseball to turn raw TrackMan data into coaching- and scouting-ready reports.

## Live Demo

https://pitch-analytics-engine.vercel.app/

## Features

- **CSV Upload & Parsing** — Upload a raw TrackMan export and automatically parse, clean, and normalize column names.
- **Pitch Metrics** — Per-pitcher, per-pitch-type aggregation: velocity, spin rate, movement (IVB/HB), release point, extension, whiff%, CSW%, hard-hit rate, and more.
- **Box Scores** — Innings pitched, hits, runs, walks, strikeouts, HBP, extra-base hits, and pitch count per outing.
- **Start Grade** — A regression-based letter grade (A through F) for starting pitcher outings.
- **Game History** — Browse and reload any previously uploaded game from the database, searchable by date, opponent, or team.
- **Printable Reports** — Clean, print-friendly report layout for handing to coaches/scouts.

## Screenshots
**Pitch Report Dashboard Preview**

<p align="center">
  <img src="assets/stats_dashboard.png" alt="Dashboard Preview" width="90%" />
</p>

**Past Games Dashboard Preview**

<p align="center">
  <img src="assets/past_games.png" alt="Past Games Preview" width="90%" />
</p>

## Tech Stack

**Backend**
- FastAPI (REST API)
- SQLAlchemy + PostgreSQL (Neon-compatible)
- pandas / numpy (data processing)
- Pydantic (schema validation)

**Frontend**
- React
- react-dropzone (CSV upload)
- Tailwind CSS (utility classes used in components)

## Project Structure

```text
.
├── assets/
│   ├── dataflow_diagram.png        # Data flow diagram
│   ├── stats_dashboard.png         # Report card dashboard preview
│   └── past_games.png              # Past games dashboard preview
├── backend/
│   ├── database.py                 # SQLAlchemy connection & session manager
│   ├── main.py                     # FastAPI routes, endpoints & CORS configuration
│   ├── parser.py                   # TrackMan CSV parsing, metric aggregation & grading
│   ├── run_pipeline.py             # Database schema setup & SQL upsert pipeline
│   ├── schemas.py                  # Pydantic models for API request/response validation
│   └── requirements.txt            # Python backend dependencies
└── frontend/
    ├── public/                     # Static assets (favicon, index.html)
    ├── src/
    │   ├── App.jsx                 # React UI, upload logic, state & print view
    │   └── main.jsx                # Application root entry point
    ├── package.json                # Node.js dependencies & scripts
    └── vite.config.js              # Vite build tool configuration
```

## Data Flow

<p align="center">
  <img src="assets/dataflow_diagram.png" alt="Dataflow Diagram" width="40%" />
</p>

## Prerequisites

- Python 3.10+
- Node.js 18+ (for the frontend)
- A PostgreSQL database (e.g. Neon)

## Backend Setup

1. Create and activate a virtual environment:
```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
   pip install -r requirements.txt
```

3. Create a `.env` file in the project root:
```bash
   DATABASE_URL=postgresql://user:password@ep-cool-db.neon.tech/neondb?sslmode=require
```

(`postgres://` URLs are also accepted and auto-converted.)

4. Run the API server:
```bash
   uvicorn main:app --reload
```
   The API will be available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

Database tables (`metadata`, `pitch_metrics`, `box_scores`) are created automatically on first upload/pipeline run — no manual migration needed.

## Frontend Setup

1. Install dependencies:
```bash
   npm install
```

2. (Optional) Set a custom API URL by creating `.env`:
```bash
   VITE_API_URL=http://localhost:8000
```

Defaults to `http://localhost:8000` if not set.

3. Start the dev server:
```bash
   npm run dev
```

## Running the Pipeline from the CLI

You can process a TrackMan CSV directly without the API/frontend:

```bash
python run_pipeline.py --file path/to/trackman_export.csv
```

This parses the file, calculates metrics/box scores/grades for every pitcher found, and upserts the results into PostgreSQL.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/upload` | Upload a TrackMan CSV, process it, and store results |
| `GET` | `/api/v1/metadata` | Get game metadata (filter by `game_i_d` or `game_date`) |
| `GET` | `/api/v1/box-score` | Get box score data (filter by `game_i_d` or `game_date`) |
| `GET` | `/api/v1/pitch-metrics` | Get pitch metrics (filter by `game_i_d` or `game_date`) |

Full interactive documentation is available at `/docs` while the server is running.

## Notes

- `calculate_earned_runs` in `parser.py` is a work in progress (inning-reconstruction logic for earned vs. unearned runs) and is not yet wired into the pipeline or API.
- Pitch types with fewer than 5% of a pitcher's total pitches are filtered out as likely misreads when a pitcher has thrown more than 15 pitches.
- The start grade is only calculated for pitchers who started the game (first inning pitched = inning 1).

