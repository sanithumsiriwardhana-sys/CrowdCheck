"""
Train the Route 177 crowd-level model (LightGBM multiclass).

Data sources (combined):
  1. data/seed_trips.csv    - synthetic, survey-shaped          (weight 1)
  2. data/field_logs.csv    - real observations by the team     (weight 5)
  3. crowd_reports table    - live rider reports (--with-reports, weight 3)

Usage:
  python -m ml.generate_seed_data      # once
  python -m ml.train                   # seed + field logs
  python -m ml.train --with-reports    # also learn from rider reports in the DB

Output: models/crowd_model.joblib and models/metrics.json
"""
import argparse
import json
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

import joblib
import lightgbm as lgb
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report

from ml.features import CROWD_LABELS, FEATURE_COLUMNS, build_features

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "data" / "seed_trips.csv"
FIELD = ROOT / "data" / "field_logs.csv"
MODEL_OUT = ROOT / "models" / "crowd_model.joblib"
METRICS_OUT = ROOT / "models" / "metrics.json"

SL_TZ = timezone(timedelta(hours=5, minutes=30))
WEIGHTS = {"synthetic": 1.0, "field_log": 5.0, "rider_report": 3.0}


def rows_to_features(df: pd.DataFrame) -> pd.DataFrame:
    feats = []
    for r in df.itertuples(index=False):
        hh, mm = map(int, str(r.time).split(":")[:2])
        feats.append(build_features(str(r.route), r.direction, r.date,
                                    time(hh, mm), float(r.rain_mm or 0)))
    out = pd.DataFrame(feats)
    out["crowd_level"] = df["crowd_level"].astype(int).values
    out["source"] = df["source"].values
    out["date"] = df["date"].values
    return out


def load_reports() -> pd.DataFrame:
    from app.db import CrowdReport, SessionLocal, init_db
    init_db()
    with SessionLocal() as s:
        reports = s.query(CrowdReport).all()
    rows = []
    for rep in reports:
        ts = rep.created_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        local = ts.astimezone(SL_TZ)
        rows.append({"date": local.date().isoformat(), "time": local.strftime("%H:%M"),
                     "route": rep.route, "direction": rep.direction, "rain_mm": 0,
                     "crowd_level": rep.crowd_level, "source": "rider_report"})
    return pd.DataFrame(rows)


def main(with_reports: bool):
    frames = []
    if not SEED.exists():
        raise SystemExit("seed_trips.csv missing - run: python -m ml.generate_seed_data")
    frames.append(pd.read_csv(SEED))

    field = pd.read_csv(FIELD) if FIELD.exists() else pd.DataFrame()
    if len(field):
        field["source"] = "field_log"
        field["rain_mm"] = field.get("rain_mm", 0).fillna(0)
        frames.append(field[["date", "time", "route", "direction", "rain_mm",
                             "crowd_level", "source"]])
    if with_reports:
        rep = load_reports()
        if len(rep):
            frames.append(rep)

    raw = pd.concat(frames, ignore_index=True)
    data = rows_to_features(raw)
    counts = data["source"].value_counts().to_dict()
    print("Training rows by source:", counts)

    # Time-based split: last 14 days held out (closer to real use than random split)
    data["date"] = pd.to_datetime(data["date"])
    cutoff = data["date"].max() - pd.Timedelta(days=14)
    train, test = data[data["date"] <= cutoff], data[data["date"] > cutoff]

    model = lgb.LGBMClassifier(
        objective="multiclass", num_class=4, n_estimators=300,
        learning_rate=0.05, num_leaves=31, min_child_samples=20,
        random_state=42, verbose=-1,
    )
    model.fit(train[FEATURE_COLUMNS], train["crowd_level"],
              sample_weight=train["source"].map(WEIGHTS))

    preds = model.predict(test[FEATURE_COLUMNS])
    acc = accuracy_score(test["crowd_level"], preds)
    within_one = float((abs(preds - test["crowd_level"].values) <= 1).mean())
    print(f"Hold-out accuracy (exact level): {acc:.3f}")
    print(f"Hold-out accuracy (within 1 level): {within_one:.3f}")
    print(classification_report(test["crowd_level"], preds,
                                target_names=CROWD_LABELS, zero_division=0))

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_OUT)
    importances = dict(sorted(zip(FEATURE_COLUMNS, map(int, model.feature_importances_)),
                              key=lambda kv: -kv[1]))
    METRICS_OUT.write_text(json.dumps({
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "rows_by_source": {k: int(v) for k, v in counts.items()},
        "holdout_accuracy": round(acc, 4),
        "holdout_within_one_level": round(within_one, 4),
        "feature_importance": importances,
        "note": "Trained mostly on synthetic seed data shaped by survey results. "
                "Accuracy reflects fit to that seed pattern, not real-world accuracy yet.",
    }, indent=2))
    print(f"Saved model -> {MODEL_OUT}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--with-reports", action="store_true")
    main(p.parse_args().with_reports)
