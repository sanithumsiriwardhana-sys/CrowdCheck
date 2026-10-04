# CrowdCheck 177 - AI Bus Crowd Prediction

Predicts how crowded a Route 177 (Kollupitiya - Kaduwela) bus will be before a SLIIT Malabe student leaves, and lets riders submit a 5-second crowd report after their trip.

![Architecture](docs/architecture.png)

## Stack
- **Frontend:** Next.js 14 (TypeScript), deployed on Vercel
- **Backend:** FastAPI (Python 3.11), deployed on Render
- **Model:** LightGBM multiclass classifier (Seats free / Standing room / Packed / Can't board)
- **Database:** Supabase PostgreSQL (`crowd_reports`), SQLite fallback for local dev
- **Weather:** Open-Meteo hourly rain for Malabe (no API key)

## Folder structure
```
backend/
  app/main.py              API endpoints
  app/db.py                Database (Supabase or local SQLite)
  ml/features.py           Shared features + calendar config (holidays, exam weeks)
  ml/generate_seed_data.py Synthetic seed data (survey-shaped)
  ml/train.py              Trains and saves the model
  data/field_logs.csv      Real observations the team logs (see FIELD_LOG_GUIDE.md)
  models/                  crowd_model.joblib + metrics.json
frontend/                  Next.js app
supabase/schema.sql        Table setup
docs/                      Architecture diagram, Gate 2 answer draft, demo script
```

## Run locally

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m ml.generate_seed_data
python -m ml.train
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000/docs to try the API. Without `DATABASE_URL` it uses a local `local.db` SQLite file.

### 2. Frontend
```bash
cd frontend
cp .env.example .env.local      # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```
Open http://localhost:3000

## API
| Method | Path | What it does |
|---|---|---|
| POST | `/predict` | `{direction, time, date?}` returns crowd level, confidence, tip, better nearby bus |
| GET | `/forecast/day?direction=to_sliit&date=YYYY-MM-DD` | Predicted level for every 10-min departure |
| POST | `/report` | `{direction, crowd_level 0-3, stop_name?}` saves a rider report |
| GET | `/reports/recent` | Reports from the last few hours |
| GET | `/model-info` | Training metrics + number of reports collected |
| GET | `/health` | Health check |

`direction` is `to_sliit` (towards Kaduwela) or `from_sliit` (towards Kollupitiya).

## Deploy

### Supabase
1. Create a project, open **SQL Editor**, run `supabase/schema.sql`.
2. **Project Settings > Database > Connection string > URI**. Use the pooler string (port 6543) and put your DB password in it.

### Backend on Render
1. New > Blueprint > select this repo (uses `render.yaml`), or New > Web Service with root dir `backend`.
2. Build: `pip install -r requirements.txt && python -m ml.generate_seed_data && python -m ml.train`
3. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Env vars: `DATABASE_URL` (Supabase URI), `FRONTEND_ORIGIN` (your Vercel URL).

Free Render instances sleep after inactivity. Open the API URL once before recording the demo so it's awake.

### Frontend on Vercel
1. Import the repo, set **Root Directory** to `frontend`.
2. Env var: `NEXT_PUBLIC_API_URL=https://your-api.onrender.com`
3. Deploy, then add the Vercel URL to `FRONTEND_ORIGIN` on Render.

## Improving the model
1. Log real buses in `backend/data/field_logs.csv` (guide: `backend/data/FIELD_LOG_GUIDE.md`).
2. Update holidays and exam weeks in `backend/ml/features.py`.
3. Retrain: `python -m ml.train --with-reports` (includes rider reports from the database).

Training weights: synthetic seed x1, rider reports x3, field logs x5.

## Honest note on data
There is no public ridership data for Route 177, so the first model is trained on **synthetic seed data shaped by our survey** (50 SLIIT commuters, 20-23 Sept 2026). The hold-out accuracy in `models/metrics.json` measures fit to that seed pattern, not real-world accuracy. Real field logs and rider reports replace the seed data over time.

## Team
Siriwardhana P.K.S.M (IT25101412), Prabaswara T.H.U. (IT25101712), Nethwin S.W.S (IT25102242), Priyabashitha G.J.S (IT25101700)
