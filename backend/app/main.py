"""
CrowdCheck 177 - FastAPI backend.

Run locally:  uvicorn app.main:app --reload --port 8000
Docs:         http://localhost:8000/docs
"""
import json
import os
import time as _time
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

import httpx
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.db import CrowdReport, SessionLocal, count_reports, init_db, recent_reports
from ml.features import (CROWD_LABELS, DEPARTURE_STEP_MIN, ROUTES, SERVICE_END,
                         SERVICE_START, build_features, departures_around,
                         features_frame, snap_to_departure)

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "crowd_model.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"

SL_TZ = timezone(timedelta(hours=5, minutes=30))
MALABE = (6.9147, 79.9729)  # SLIIT Malabe, for weather

app = FastAPI(title="CrowdCheck 177 API", version="0.2.0")

origins = [o.strip() for o in os.getenv("FRONTEND_ORIGIN", "*").split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"],
                   allow_headers=["*"])

model = None
_weather_cache: dict[str, tuple[float, dict[int, float]]] = {}


@app.on_event("startup")
def startup():
    global model
    init_db()
    if not MODEL_PATH.exists():
        raise RuntimeError("Model not found. Run: python -m ml.generate_seed_data && python -m ml.train")
    model = joblib.load(MODEL_PATH)


# ---------------------------------------------------------------- helpers
def now_sl() -> datetime:
    return datetime.now(SL_TZ)


def parse_hhmm(s: str) -> time:
    try:
        hh, mm = map(int, s.split(":")[:2])
        return time(hh, mm)
    except Exception:
        raise HTTPException(422, "time must be HH:MM (24h), e.g. 07:40")


def check_route(route: str, direction: str):
    if route not in ROUTES:
        raise HTTPException(404, f"Route {route} is not covered yet. Available: {list(ROUTES)}")
    if direction not in ROUTES[route]["directions"]:
        raise HTTPException(422, "direction must be 'to_sliit' or 'from_sliit'")


def hourly_rain(d: date) -> tuple[dict[int, float], str]:
    """Hourly precipitation (mm) for Malabe from Open-Meteo. Cached 30 min."""
    key = d.isoformat()
    cached = _weather_cache.get(key)
    if cached and _time.time() - cached[0] < 1800:
        return cached[1], "open-meteo"
    try:
        r = httpx.get("https://api.open-meteo.com/v1/forecast", timeout=4, params={
            "latitude": MALABE[0], "longitude": MALABE[1], "hourly": "precipitation",
            "timezone": "Asia/Colombo", "start_date": key, "end_date": key})
        r.raise_for_status()
        h = r.json()["hourly"]
        rain = {int(t[11:13]): float(p or 0) for t, p in zip(h["time"], h["precipitation"])}
        _weather_cache[key] = (_time.time(), rain)
        return rain, "open-meteo"
    except Exception:
        return {}, "unavailable (assumed dry)"


def predict_probs(route, direction, d, slots: list[time], rain: dict[int, float]) -> np.ndarray:
    rows = [build_features(route, direction, d, t, rain.get(t.hour, 0.0)) for t in slots]
    return model.predict_proba(features_frame(rows))


def live_blend(route, direction, d, t, probs: np.ndarray):
    """Blend model output with rider reports from the last 30 min,
    only when the user asks about a bus close to right now."""
    now = now_sl()
    target = datetime.combine(d, t, tzinfo=SL_TZ)
    if abs((target - now).total_seconds()) > 45 * 60:
        return probs, 0
    with SessionLocal() as s:
        reps = recent_reports(s, route, direction, datetime.now(timezone.utc) - timedelta(minutes=30))
    if not reps:
        return probs, 0
    live = np.zeros(4)
    for rep in reps:
        ts = rep.created_at if rep.created_at.tzinfo else rep.created_at.replace(tzinfo=timezone.utc)
        age_min = (datetime.now(timezone.utc) - ts).total_seconds() / 60
        live[rep.crowd_level] += max(0.2, 1 - age_min / 30)  # newer reports count more
    live /= live.sum()
    w = min(0.7, 0.25 * len(reps))
    return (1 - w) * probs + w * live, len(reps)


def expected_level(p: np.ndarray) -> float:
    return float(np.dot(p, np.arange(4)))


def make_tip(level: int) -> str:
    return {
        0: "You should get a seat.",
        1: "Expect to stand for part of the trip.",
        2: "Expect a packed bus. Leave early if you have a lecture or exam.",
        3: "High chance you won't get on. Plan for an earlier bus or another route.",
    }[level]


# ---------------------------------------------------------------- schemas
class PredictIn(BaseModel):
    route: str = "177"
    direction: Literal["to_sliit", "from_sliit"]
    time: str = Field(..., examples=["07:40"])
    date: Optional[str] = Field(None, description="YYYY-MM-DD, defaults to today (Sri Lanka time)")


class ReportIn(BaseModel):
    route: str = "177"
    direction: Literal["to_sliit", "from_sliit"]
    crowd_level: int = Field(..., ge=0, le=3)
    stop_name: Optional[str] = Field(None, max_length=80)


# ---------------------------------------------------------------- routes
@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None}


@app.get("/routes")
def routes():
    return {"routes": ROUTES, "levels": CROWD_LABELS,
            "service_hours": [SERVICE_START.strftime("%H:%M"), SERVICE_END.strftime("%H:%M")]}


@app.get("/model-info")
def model_info():
    info = json.loads(METRICS_PATH.read_text()) if METRICS_PATH.exists() else {}
    with SessionLocal() as s:
        info["rider_reports_collected"] = count_reports(s)
    return info


@app.post("/predict")
def predict(body: PredictIn):
    check_route(body.route, body.direction)
    d = date.fromisoformat(body.date) if body.date else now_sl().date()
    t = snap_to_departure(parse_hhmm(body.time))
    rain, weather_src = hourly_rain(d)

    probs = predict_probs(body.route, body.direction, d, [t], rain)[0]
    probs, n_live = live_blend(body.route, body.direction, d, t, probs)
    level = int(np.argmax(probs))

    # Look at nearby departures for a less-crowded option
    alts = departures_around(t, 30)
    best = None
    if alts:
        alt_probs = predict_probs(body.route, body.direction, d, alts, rain)
        cands = [{"time": a.strftime("%H:%M"), "expected": expected_level(p),
                  "level": int(np.argmax(p)), "label": CROWD_LABELS[int(np.argmax(p))]}
                 for a, p in zip(alts, alt_probs)]
        best = min(cands, key=lambda c: (c["expected"], abs(int(c["time"][:2]) * 60 + int(c["time"][3:]) - (t.hour * 60 + t.minute))))
        if best["level"] >= level:
            best = None

    if best:
        when = "earlier" if best["time"] < t.strftime("%H:%M") else "later"
        tip = f"The {best['time']} bus ({when}) should be better: {best['label'].lower()}."
    else:
        tip = make_tip(level)

    return {
        "route": body.route,
        "direction": body.direction,
        "date": d.isoformat(),
        "departure": t.strftime("%H:%M"),
        "level": level,
        "label": CROWD_LABELS[level],
        "confidence": round(float(probs[level]), 3),
        "probabilities": {CROWD_LABELS[i]: round(float(p), 3) for i, p in enumerate(probs)},
        "rain_mm": rain.get(t.hour, 0.0),
        "weather_source": weather_src,
        "live_reports_used": n_live,
        "better_option": best,
        "tip": tip,
    }


@app.get("/forecast/day")
def forecast_day(direction: Literal["to_sliit", "from_sliit"], route: str = "177",
                 day: Optional[str] = Query(None, alias="date")):
    """Predicted level for every departure slot of a day (for the timeline strip)."""
    check_route(route, direction)
    d = date.fromisoformat(day) if day else now_sl().date()
    rain, weather_src = hourly_rain(d)
    slots = []
    m = SERVICE_START.hour * 60 + SERVICE_START.minute
    end = SERVICE_END.hour * 60 + SERVICE_END.minute
    while m <= end:
        slots.append(time(m // 60, m % 60))
        m += DEPARTURE_STEP_MIN
    probs = predict_probs(route, direction, d, slots, rain)
    return {"date": d.isoformat(), "route": route, "direction": direction,
            "weather_source": weather_src,
            "slots": [{"time": t.strftime("%H:%M"), "level": int(np.argmax(p)),
                       "confidence": round(float(p.max()), 3)} for t, p in zip(slots, probs)]}


@app.post("/report", status_code=201)
def report(body: ReportIn):
    check_route(body.route, body.direction)
    with SessionLocal() as s:
        rep = CrowdReport(route=body.route, direction=body.direction,
                          crowd_level=body.crowd_level, stop_name=body.stop_name)
        s.add(rep)
        s.commit()
        s.refresh(rep)
        total = count_reports(s)
    return {"id": rep.id, "saved": True, "label": CROWD_LABELS[body.crowd_level],
            "total_reports": total}


@app.get("/reports/recent")
def reports_recent(route: str = "177", direction: Optional[str] = None, minutes: int = 120):
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    with SessionLocal() as s:
        q = s.query(CrowdReport).filter(CrowdReport.route == route, CrowdReport.created_at >= since)
        if direction:
            q = q.filter(CrowdReport.direction == direction)
        reps = q.order_by(CrowdReport.created_at.desc()).limit(20).all()
    out = []
    for r in reps:
        ts = r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc)
        out.append({"id": r.id, "direction": r.direction, "level": r.crowd_level,
                    "label": CROWD_LABELS[r.crowd_level], "stop_name": r.stop_name,
                    "reported_at": ts.astimezone(SL_TZ).strftime("%H:%M")})
    return {"reports": out}
