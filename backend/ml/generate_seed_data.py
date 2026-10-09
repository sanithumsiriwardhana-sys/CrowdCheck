"""
Generate SEED training data for routes 177, 170, 190 and 17.

IMPORTANT (be honest about this):
There is no public ridership data for these routes, so this script creates
SYNTHETIC trips. Their shape follows our survey (50 SLIIT commuters,
21-23 Sept 2026) and how Colombo commuting works:

  Morning rush goes INTO Colombo, evening rush goes OUT of Colombo.
    177  morning: towards Kollupitiya   evening: towards Kaduwela
    170  morning: towards Pettah        evening: towards Athurugiriya
    190  morning: towards Pettah        evening: towards Meegoda
    17   morning: towards Panadura      evening: towards Kandy
         (17 runs through the Colombo suburbs on the Panadura side)
  SLIIT students add a smaller morning bump in the outbound direction
  (e.g. 177 towards Kaduwela, to reach Malabe for lectures).

  Survey ratings: 177 mostly Packed/Standing (35 ratings); 17 the most
  crowded (9 of 22 "Can't get on"); 170 and 190 only 4 ratings each,
  so their shape is a rough estimate.

Holidays (from ml/holidays.py: Google Calendar / data/holidays_lk.json):
  - Public holidays and Poya: city routes (177, 170, 190) much quieter
  - Poya and long weekends: route 17 busier (pilgrims, trips to Kandy)
  - Working day BEFORE a holiday break: heavier evening rush out of Colombo
  - Working day AFTER a holiday break: heavier morning rush back into Colombo

Also built in: quieter weekends, exam weeks, rain, Monday mornings.

Real field logs (data/field_logs.csv) and live rider reports replace this
over time. Field logs are weighted higher than synthetic rows in training.

Usage:  python -m ml.generate_seed_data
Output: data/seed_trips.csv
"""
import math
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from ml.features import (DEPARTURE_STEP_MIN, ROUTES, SERVICE_END,
                         SERVICE_START, build_features)

RNG = np.random.default_rng(42)

START = date(2026, 3, 1)   # covers New Year, Vesak, Poson, Esala, Nikini, Binara
END = date(2026, 9, 30)
OUT = Path(__file__).resolve().parent.parent / "data" / "seed_trips.csv"

# Per route, per direction: list of (peak_hour, spread_hours, strength).
# "base" is the all-day load, "scale" multiplies everything.
# The to-Colombo direction has the big MORNING peak; the other direction has
# the big EVENING peak.
PROFILES = {
    "177": {
        "base": 0.20, "scale": 1.00,
        "to_kollupitiya": [(7.7, 0.70, 0.95), (13.0, 0.8, 0.30), (17.6, 0.9, 0.30)],
        "to_kaduwela":    [(17.8, 0.75, 0.95), (8.0, 0.7, 0.45), (12.5, 0.8, 0.30)],
    },
    "17": {
        "base": 0.34, "scale": 1.12,
        "to_panadura": [(7.0, 0.8, 0.95), (17.0, 1.0, 0.60), (12.5, 1.5, 0.25)],
        "to_kandy":    [(17.3, 1.0, 0.95), (6.9, 0.9, 0.60), (13.0, 1.5, 0.25)],
    },
    "170": {
        "base": 0.18, "scale": 0.88,
        "to_pettah":       [(7.6, 0.8, 0.90), (17.5, 0.9, 0.40)],
        "to_athurugiriya": [(17.6, 0.9, 0.90), (8.0, 0.8, 0.45)],
    },
    "190": {
        "base": 0.20, "scale": 0.93,
        "to_pettah":  [(7.5, 0.8, 0.95), (17.4, 0.9, 0.40)],
        "to_meegoda": [(17.7, 0.9, 0.90), (8.1, 0.8, 0.45)],
    },
}


def gaussian(x, mu, sigma):
    return math.exp(-((x - mu) ** 2) / (2 * sigma ** 2))


def crowd_score(route: str, direction: str, minute: int, feats: dict) -> float:
    """Continuous 0..~1.2 crowd score before noise."""
    prof = PROFILES[route]
    h = minute / 60.0
    score = sum(w * gaussian(h, mu, sd) for mu, sd, w in prof[direction])
    score += prof["base"]
    score *= prof["scale"]

    intercity = route == "17"
    to_colombo = feats["to_colombo"] == 1

    if feats["is_poya"] or feats["is_public_holiday"]:
        if intercity:
            # Poya: pilgrims and family trips keep 17 busy, towards Kandy most
            score *= 1.05 if feats["is_poya"] else 0.85
            if not to_colombo and 7 <= h <= 13:
                score += 0.18
        else:
            score *= 0.45  # office and lecture commuting mostly stops
    elif feats["is_weekend"]:
        weekend = 0.75 if intercity else (0.50 if feats["day_of_week"] == 6 else 0.62)
        score *= weekend
        if intercity and feats["is_long_weekend"] and not to_colombo and 7 <= h <= 13:
            score += 0.15  # long-weekend trips out of Colombo

    # The working day before a holiday break: people leave Colombo early evening
    if feats["is_day_before_holiday"] and not to_colombo and 15 <= h <= 20:
        score *= 1.30 if intercity else 1.18
    # The working day after a holiday break: everyone comes back the same morning
    if feats["is_day_after_holiday"] and to_colombo and 5.5 <= h <= 10:
        score *= 1.25 if intercity else 1.15

    if feats["is_exam_week"] and not to_colombo and 7 <= h <= 9.5:
        score *= 1.15  # students heading to SLIIT for exams
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


def rain_for(minute: int) -> float:
    # Afternoon showers are more common; simple synthetic pattern
    if RNG.random() >= 0.35:
        return 0.0
    afternoon = 13 * 60 <= minute <= 19 * 60
    p = 0.55 if afternoon else 0.15
    return float(round(RNG.gamma(1.5, 2.5), 1)) if RNG.random() < p else 0.0


def main():
    rows = []
    start_min = SERVICE_START.hour * 60 + SERVICE_START.minute
    end_min = SERVICE_END.hour * 60 + SERVICE_END.minute
    for route, info in ROUTES.items():
        d = START
        while d <= END:
            for direction in info["directions"]:
                for minute in range(start_min, end_min + 1, DEPARTURE_STEP_MIN):
                    t = (datetime.min + timedelta(minutes=minute)).time()
                    rain = rain_for(minute)
                    feats = build_features(route, direction, d, t, rain)
                    s = crowd_score(route, direction, minute, feats)
                    s += RNG.normal(0, 0.09)  # day-to-day noise
                    if RNG.random() < 0.02:   # breakdown / skipped bus spike
                        s += 0.45
                    rows.append({
                        "date": d.isoformat(),
                        "time": t.strftime("%H:%M"),
                        "route": route,
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
    print("Level share by route (0 seats free .. 3 can't board):")
    print(pd.crosstab(df["route"], df["crowd_level"], normalize="index").round(2).to_string())


if __name__ == "__main__":
    main()
