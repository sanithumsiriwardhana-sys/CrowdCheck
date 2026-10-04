"""
Shared feature engineering for training AND prediction.
Both ml/train.py and app/main.py import from here so features always match.
"""
from datetime import date, datetime, time, timedelta

import pandas as pd

ROUTES = {
    "177": {
        "name": "Kollupitiya - Kaduwela",
        "directions": {
            "to_sliit": "Towards Kaduwela (to SLIIT)",
            "from_sliit": "Towards Kollupitiya (from SLIIT)",
        },
    },
}

CROWD_LABELS = ["Seats free", "Standing room", "Packed", "Can't board"]

# Departure window the app covers (every 10 minutes)
SERVICE_START = time(5, 30)
SERVICE_END = time(21, 0)
DEPARTURE_STEP_MIN = 10

# ---------------------------------------------------------------------------
# Calendar config.
# VERIFY these against the official government holiday list and the SLIIT
# academic calendar before final submission. They are editable on purpose.
# ---------------------------------------------------------------------------
PUBLIC_HOLIDAYS = {
    # Format: "YYYY-MM-DD"  -> fill in Poya days / public holidays for the period
    "2026-08-27",
    "2026-09-25",
    "2026-10-25",
}

# (start, end) inclusive date ranges when mid/final exams run at SLIIT
EXAM_WEEKS = [
    ("2026-09-07", "2026-09-13"),
]

FEATURE_COLUMNS = [
    "route_code",
    "direction_code",
    "hour",
    "minute_of_day",
    "day_of_week",
    "is_weekend",
    "is_lecture_day",
    "is_exam_week",
    "is_public_holiday",
    "rain_mm",
]


def _to_date(d) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        return date.fromisoformat(d)
    return d


def is_public_holiday(d) -> int:
    return int(_to_date(d).isoformat() in PUBLIC_HOLIDAYS)


def is_exam_week(d) -> int:
    d = _to_date(d)
    for start, end in EXAM_WEEKS:
        if date.fromisoformat(start) <= d <= date.fromisoformat(end):
            return 1
    return 0


def is_lecture_day(d) -> int:
    d = _to_date(d)
    return int(d.weekday() < 5 and not is_public_holiday(d))


def build_features(route: str, direction: str, d, t: time, rain_mm: float) -> dict:
    d = _to_date(d)
    return {
        "route_code": int(route),
        "direction_code": 0 if direction == "to_sliit" else 1,
        "hour": t.hour,
        "minute_of_day": t.hour * 60 + t.minute,
        "day_of_week": d.weekday(),
        "is_weekend": int(d.weekday() >= 5),
        "is_lecture_day": is_lecture_day(d),
        "is_exam_week": is_exam_week(d),
        "is_public_holiday": is_public_holiday(d),
        "rain_mm": float(rain_mm),
    }


def features_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)[FEATURE_COLUMNS]


def departures_around(t: time, window_min: int = 30) -> list[time]:
    """Departure slots within +/- window_min of t, clipped to service hours."""
    base = datetime.combine(date.today(), t)
    out = []
    for offset in range(-window_min, window_min + 1, DEPARTURE_STEP_MIN):
        cand = (base + timedelta(minutes=offset)).time()
        if SERVICE_START <= cand <= SERVICE_END and cand != t:
            out.append(cand)
    return out


def snap_to_departure(t: time) -> time:
    """Round a time to the nearest 10-minute departure slot."""
    total = t.hour * 60 + t.minute
    snapped = int(round(total / DEPARTURE_STEP_MIN) * DEPARTURE_STEP_MIN)
    snapped = max(SERVICE_START.hour * 60 + SERVICE_START.minute,
                  min(snapped, SERVICE_END.hour * 60 + SERVICE_END.minute))
    return time(snapped // 60, snapped % 60)
