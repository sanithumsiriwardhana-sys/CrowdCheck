"""
Shared feature engineering for training AND prediction.
Both ml/train.py and app/main.py import from here so features always match.
"""
from datetime import date, datetime, time, timedelta
from functools import lru_cache

import pandas as pd

from ml import holidays

# ---------------------------------------------------------------------------
# Routes covered. Each route has two directions, named by where the bus is
# heading. The FIRST direction is code 0, the second is code 1 (model feature).
# "to_colombo" is the direction that carries the morning rush INTO Colombo;
# the other direction carries the evening rush OUT of Colombo.
# Keep frontend/lib/routes.ts in sync if you change this.
# ---------------------------------------------------------------------------
ROUTES = {
    "177": {
        "name": "Kollupitiya - Kaduwela",
        "directions": {
            "to_kaduwela": "Towards Kaduwela",
            "to_kollupitiya": "Towards Kollupitiya",
        },
        "to_colombo": "to_kollupitiya",
    },
    "170": {
        "name": "Athurugiriya - Pettah",
        "directions": {
            "to_athurugiriya": "Towards Athurugiriya",
            "to_pettah": "Towards Pettah",
        },
        "to_colombo": "to_pettah",
    },
    "190": {
        "name": "Meegoda - Pettah",
        "directions": {
            "to_meegoda": "Towards Meegoda",
            "to_pettah": "Towards Pettah",
        },
        "to_colombo": "to_pettah",
    },
    "17": {
        "name": "Panadura - Kandy",
        "directions": {
            "to_kandy": "Towards Kandy",
            "to_panadura": "Towards Panadura",
        },
        # 17 doesn't enter Colombo; towards Panadura runs through the Colombo
        # suburbs (Maharagama, Piliyandala), so it gets the morning rush.
        "to_colombo": "to_panadura",
    },
}

# Old direction names (before multi-route) -> new names for Route 177
LEGACY_DIRECTIONS = {"to_sliit": "to_kaduwela", "from_sliit": "to_kollupitiya"}


def direction_code(route: str, direction: str) -> int:
    direction = LEGACY_DIRECTIONS.get(direction, direction) if route == "177" else direction
    return list(ROUTES[str(route)]["directions"]).index(direction)


CROWD_LABELS = ["Seats free", "Standing room", "Packed", "Can't board"]

# Departure window the app covers (every 10 minutes)
SERVICE_START = time(5, 30)
SERVICE_END = time(21, 0)
DEPARTURE_STEP_MIN = 10

# ---------------------------------------------------------------------------
# Calendar config.
# Holidays (Poya + public) come from ml/holidays.py (Google Calendar, saved to
# data/holidays_lk.json). SLIIT exam weeks are not in Google's calendar, so
# they stay here. VERIFY against the SLIIT academic calendar.
# ---------------------------------------------------------------------------
# (start, end) inclusive date ranges when mid/final exams run at SLIIT
EXAM_WEEKS = [
    ("2026-09-07", "2026-09-13"),
]

FEATURE_COLUMNS = [
    "route_code",
    "direction_code",
    "to_colombo",
    "hour",
    "minute_of_day",
    "day_of_week",
    "is_weekend",
    "is_lecture_day",
    "is_exam_week",
    "is_public_holiday",
    "is_poya",
    "is_long_weekend",
    "is_day_before_holiday",
    "is_day_after_holiday",
    "rain_mm",
]


def _to_date(d) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        return date.fromisoformat(d)
    return d


def is_exam_week(d) -> int:
    d = _to_date(d)
    for start, end in EXAM_WEEKS:
        if date.fromisoformat(start) <= d <= date.fromisoformat(end):
            return 1
    return 0


def _holiday(d: date) -> bool:
    return bool(holidays.holidays_on(d))


def _day_off(d: date) -> bool:
    return d.weekday() >= 5 or _holiday(d)


def _off_block(d: date) -> list[date]:
    """The run of consecutive days off (weekends + holidays) that contains d."""
    if not _day_off(d):
        return []
    start = d
    while _day_off(start - timedelta(days=1)):
        start -= timedelta(days=1)
    end = d
    while _day_off(end + timedelta(days=1)):
        end += timedelta(days=1)
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


@lru_cache(maxsize=4096)
def _calendar_flags(d: date, _version: int) -> dict:
    names = [h["name"] for h in holidays.holidays_on(d)]
    poya = any(h["poya"] for h in holidays.holidays_on(d))
    block = _off_block(d)
    long_weekend = len(block) >= 3 and any(_holiday(x) for x in block)

    # Working day right before / after a break that includes a holiday
    # (an ordinary Saturday-Sunday weekend doesn't count).
    before = after = False
    if not _day_off(d):
        nxt = _off_block(d + timedelta(days=1))
        prv = _off_block(d - timedelta(days=1))
        before = any(_holiday(x) for x in nxt)
        after = any(_holiday(x) for x in prv)

    return {
        "holiday_names": names,
        "is_public_holiday": int(bool(names)),
        "is_poya": int(poya),
        "is_long_weekend": int(long_weekend),
        "is_day_before_holiday": int(before),
        "is_day_after_holiday": int(after),
    }


def calendar_flags(d) -> dict:
    d = _to_date(d)
    return _calendar_flags(d, holidays.version())


def is_public_holiday(d) -> int:
    return calendar_flags(d)["is_public_holiday"]


def is_lecture_day(d) -> int:
    d = _to_date(d)
    return int(d.weekday() < 5 and not is_public_holiday(d))


def is_to_colombo(route: str, direction: str) -> int:
    direction = LEGACY_DIRECTIONS.get(direction, direction) if str(route) == "177" else direction
    return int(ROUTES[str(route)]["to_colombo"] == direction)


def build_features(route: str, direction: str, d, t: time, rain_mm: float) -> dict:
    d = _to_date(d)
    cal = calendar_flags(d)
    return {
        "route_code": int(route),
        "direction_code": direction_code(str(route), direction),
        "to_colombo": is_to_colombo(route, direction),
        "hour": t.hour,
        "minute_of_day": t.hour * 60 + t.minute,
        "day_of_week": d.weekday(),
        "is_weekend": int(d.weekday() >= 5),
        "is_lecture_day": int(d.weekday() < 5 and not cal["is_public_holiday"]),
        "is_exam_week": is_exam_week(d),
        "is_public_holiday": cal["is_public_holiday"],
        "is_poya": cal["is_poya"],
        "is_long_weekend": cal["is_long_weekend"],
        "is_day_before_holiday": cal["is_day_before_holiday"],
        "is_day_after_holiday": cal["is_day_after_holiday"],
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
