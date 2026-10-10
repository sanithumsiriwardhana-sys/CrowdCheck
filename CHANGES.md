# v0.4 - Holidays + Colombo rush pattern (on top of v0.3 multi-route)

## What changed in v0.4
- **Colombo rush pattern.** Morning rush now goes into Colombo and evening rush out of Colombo on every route (177: towards Kollupitiya in the morning, towards Kaduwela in the evening; 170/190: towards Pettah in the morning; 17: towards Panadura in the morning, towards Kandy in the evening). SLIIT students still add a smaller morning bump in the other direction.
- **Holidays.** New `backend/ml/holidays.py` reads Sri Lankan Poya and public holidays from Google Calendar (`GOOGLE_API_KEY`), saved in `backend/data/holidays_lk.json`. The file ships with the official 2026 list so it works without a key. The API refreshes it on startup and daily.
- New model features: to_colombo, is_poya, is_long_weekend, is_day_before_holiday, is_day_after_holiday. Seed data now covers March-September 2026 (New Year, Vesak, Poson, Esala, Nikini, Binara). Model retrained.
- Fixed a wrong placeholder date: Binara Poya 2026 is 26 Sep, not 25 Sep.
- API: `/predict` returns a `day` object with a holiday note; new `GET /holidays`.
- App: holiday note on the prediction and "Next holiday" link under the date picker.
- Render build now runs `python -m ml.holidays` first; add `GOOGLE_API_KEY` in Render's environment.

## v0.3 - Multi-route (177, 170, 190, 17)
- Route buttons at the top; directions named by destination; seed data and model for all four routes; database auto-upgrade; mobile layout fix.

## Files changed (v0.3 + v0.4), by owner
Sanithu (model and data)
- backend/ml/features.py, backend/ml/generate_seed_data.py
- backend/ml/holidays.py (new), backend/data/holidays_lk.json (new)
- backend/data/seed_trips.csv, backend/data/FIELD_LOG_GUIDE.md
- backend/models/crowd_model.joblib, backend/models/metrics.json

Ushan (backend API)
- backend/app/main.py, backend/app/db.py
- backend/.gitignore, backend/.env.example, render.yaml

Janidu (frontend)
- frontend/lib/routes.ts (new), frontend/lib/api.ts, frontend/components/ReportPanel.tsx
- frontend/app/page.tsx, frontend/app/layout.tsx, frontend/app/globals.css, frontend/package.json

Senuth (database and docs)
- supabase/schema.sql, supabase/migration_002_multi_route.sql (new)
- README.md, .gitignore, CHANGES.md, docs/architecture.svg, docs/architecture.png
