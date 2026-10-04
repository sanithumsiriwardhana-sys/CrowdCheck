"""
Generate SEED training data for Route 177.

IMPORTANT (be honest about this in Gate 2):
There is no public ridership data for Route 177, so this script creates
SYNTHETIC trips whose shape follows what our survey found:
  - peaks around 7-9am (towards SLIIT) and 5-7pm (from SLIIT)
  - weekday/lecture days much busier than weekends and holidays
  - exam weeks concentrate the morning rush
  - rain pushes more people onto buses
Real field logs (data/field_logs.csv) and live rider reports replace this
over time. Field logs are weighted higher than synthetic rows in training.

Usage:  python -m ml.generate_seed_data
Output: data/seed_trips.csv
"""
import math
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from ml.features import (DEPARTURE_STEP_MIN, SERVICE_END, SERVICE_START,
                         build_features)

RNG = np.random.default_rng(42)
random.seed(42)

START = date(2026, 6, 1)
END = date(2026, 9, 30)
OUT = Path(__file__).resolve().parent.parent / "data" / "seed_trips.csv"


def gaussian(x, mu, sigma):
    return math.exp(-((x - mu) ** 2) / (2 * sigma ** 2))


def crowd_score(direction: str, minute: int, feats: dict) -> float:
    """Continuous 0..~1.2 crowd score before noise."""
    h = minute / 60.0
    if direction == "to_sliit":
        score = (0.95 * gaussian(h, 7.9, 0.65)       # main lecture rush
                 + 0.35 * gaussian(h, 12.5, 0.8)     # afternoon lectures
                 + 0.30 * gaussian(h, 17.8, 0.9))    # general commuters
    else:
        score = (0.95 * gaussian(h, 17.9, 0.75)      # lectures end
                 + 0.40 * gaussian(h, 13.3, 0.7)     # morning-only students
                 + 0.30 * gaussian(h, 8.0, 0.8))     # office commuters
    score += 0.20  # base load on a busy corridor

    if feats["is_public_holiday"]:
        score *= 0.45
    elif feats["is_weekend"]:
        score *= 0.50 if feats["day_of_week"] == 6 else 0.62
    if feats["is_exam_week"] and direction == "to_sliit" and 7 <= h <= 9.5:
        score *= 1.15
    if feats["day_of_week"] == 0 and 6.5 <= h <= 9.5:  # Monday morning
        score *= 1.08

    score += min(feats["rain_mm"], 15) * 0.012
    return score


def score_to_level(s: float) -> int:
    if s < 0.38:
        return 0  # seats free
    if s < 0.62:
        return 1  # standing room
    if s < 0.88:
        return 2  # packed
    return 3      # can't board


def rain_for(d: date, minute: int) -> float:
    # Afternoon showers are more common; simple synthetic pattern
    day_wet = RNG.random() < 0.35
    if not day_wet:
        return 0.0
    afternoon = 13 * 60 <= minute <= 19 * 60
    p = 0.55 if afternoon else 0.15
    return float(round(RNG.gamma(1.5, 2.5), 1)) if RNG.random() < p else 0.0


def main():
    rows = []
    d = START
    start_min = SERVICE_START.hour * 60 + SERVICE_START.minute
    end_min = SERVICE_END.hour * 60 + SERVICE_END.minute
    while d <= END:
        for direction in ("to_sliit", "from_sliit"):
            for minute in range(start_min, end_min + 1, DEPARTURE_STEP_MIN):
                t = (datetime.min + timedelta(minutes=minute)).time()
                rain = rain_for(d, minute)
                feats = build_features("177", direction, d, t, rain)
                s = crowd_score(direction, minute, feats)
                s += RNG.normal(0, 0.09)  # day-to-day noise
                if RNG.random() < 0.02:   # breakdown / skipped bus spike
                    s += 0.45
                rows.append({
                    "date": d.isoformat(),
                    "time": t.strftime("%H:%M"),
                    "route": "177",
                    "direction": direction,
                    "rain_mm": rain,
                    "crowd_level": score_to_level(s),
                    "source": "synthetic",
                })
        d += timedelta(days=1)

    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {len(df):,} synthetic rows to {OUT}")
    print("Level distribution:")
    print(df["crowd_level"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
