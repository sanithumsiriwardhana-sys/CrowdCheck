"""
Sri Lankan holidays (Poya days, public holidays) for the crowd model.

Where the dates come from:
  1. Google Calendar "Holidays in Sri Lanka" public calendar, using GOOGLE_API_KEY.
     Fetched results are saved to data/holidays_lk.json.
  2. If there's no key or Google can't be reached, the saved data/holidays_lk.json
     is used as-is. The file in the repo starts with the official 2026 list
     (Government calendar, as published by Ada Derana).

Usage:
  python -m ml.holidays            # fetch from Google now and update the file
  python -m ml.holidays --list     # print what's in the file

The API refreshes the file automatically once a day (see app/main.py).
"""
import argparse
import json
import os
import threading
from urllib.parse import quote
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "holidays_lk.json"
CALENDAR_ID = "en.lk#holiday@group.v.calendar.google.com"
GOOGLE_URL = "https://www.googleapis.com/calendar/v3/calendars/{cid}/events"
REFRESH_AFTER = timedelta(hours=24)


def _load_dotenv():
    """Read backend/.env.local (and .env) so local runs pick up GOOGLE_API_KEY."""
    for name in (".env.local", ".env"):
        p = ROOT / name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

# ---------------------------------------------------------------- file I/O
_lock = threading.Lock()
_state = {"mtime": None, "by_date": {}, "version": 0}


def _read_file() -> dict:
    if not CACHE.exists():
        return {"source": "none", "fetched_at": None, "holidays": []}
    return json.loads(CACHE.read_text(encoding="utf-8"))


def _write_file(data: dict):
    tmp = CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CACHE)


def _index(holidays: list[dict]) -> dict[str, list[dict]]:
    by_date: dict[str, list[dict]] = {}
    for h in holidays:
        by_date.setdefault(h["date"], []).append(h)
    return by_date


def _ensure_loaded():
    """(Re)load the file into memory if it changed on disk."""
    mtime = CACHE.stat().st_mtime if CACHE.exists() else None
    if mtime == _state["mtime"]:
        return
    with _lock:
        data = _read_file()
        _state["by_date"] = _index(data.get("holidays", []))
        _state["mtime"] = mtime
        _state["version"] += 1


def version() -> int:
    """Changes whenever the holiday list changes (used to reset feature caches)."""
    _ensure_loaded()
    return _state["version"]


def holidays_on(d: date) -> list[dict]:
    _ensure_loaded()
    return _state["by_date"].get(d.isoformat(), [])


def upcoming(start: date, days: int) -> list[dict]:
    _ensure_loaded()
    end = start + timedelta(days=days)
    out = []
    for ds in sorted(_state["by_date"]):
        if start.isoformat() <= ds <= end.isoformat():
            out.extend(_state["by_date"][ds])
    return out


# ---------------------------------------------------------------- Google fetch
def is_poya_name(name: str) -> bool:
    n = name.lower()
    return "poya" in n and "after" not in n and "before" not in n


def fetch_google(api_key: str, start: date, end: date) -> list[dict]:
    """Return [{date, name, poya}] from Google's Sri Lanka holiday calendar."""
    items, page = [], None
    while True:
        params = {
            "key": api_key,
            "timeMin": f"{start.isoformat()}T00:00:00Z",
            "timeMax": f"{end.isoformat()}T00:00:00Z",
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 250,
        }
        if page:
            params["pageToken"] = page
        r = httpx.get(GOOGLE_URL.format(cid=quote(CALENDAR_ID, safe="")), params=params, timeout=10)
        r.raise_for_status()
        body = r.json()
        items.extend(body.get("items", []))
        page = body.get("nextPageToken")
        if not page:
            break

    out = []
    for ev in items:
        day = ev.get("start", {}).get("date")
        name = (ev.get("summary") or "").strip()
        desc = (ev.get("description") or "").lower()
        if not day or not name or "observance" in desc:
            continue  # skip observances (not days off)
        out.append({"date": day, "name": name, "poya": is_poya_name(name)})
    return out


def refresh(force: bool = False) -> str:
    """Fetch from Google and merge into the file. Never raises; returns a status line."""
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return "skipped: GOOGLE_API_KEY not set (using saved holidays file)"

    data = _read_file()
    fetched_at = data.get("fetched_at")
    if not force and fetched_at and data.get("source", "").startswith("google"):
        age = datetime.now(timezone.utc) - datetime.fromisoformat(fetched_at)
        if age < REFRESH_AFTER:
            return "skipped: fetched less than 24h ago"

    today = date.today()
    start, end = date(today.year - 1, 1, 1), date(today.year + 2, 1, 1)
    try:
        fresh = fetch_google(api_key, start, end)
    except Exception as e:  # network down, bad key, quota...
        return f"failed: {e.__class__.__name__}: {str(e)[:160]} (using saved holidays file)"
    if not fresh:
        return "failed: Google returned no holidays (using saved holidays file)"

    # Keep saved dates outside the fetched range (e.g. older training dates)
    kept = [h for h in data.get("holidays", [])
            if not (start.isoformat() <= h["date"] < end.isoformat())]
    merged = sorted(kept + fresh, key=lambda h: (h["date"], h["name"]))
    with _lock:
        _write_file({
            "source": "google_calendar:" + CALENDAR_ID,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "holidays": merged,
        })
    _ensure_loaded()
    return f"ok: {len(fresh)} holidays from Google ({start} to {end})"


def refresh_in_background():
    threading.Thread(target=lambda: print("[holidays]", refresh()), daemon=True).start()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--list", action="store_true", help="print the saved holidays")
    args = p.parse_args()
    if args.list:
        data = _read_file()
        print(f"source: {data.get('source')}  fetched_at: {data.get('fetched_at')}")
        for h in data.get("holidays", []):
            print(f"  {h['date']}  {'POYA ' if h['poya'] else '     '} {h['name']}")
    else:
        print(refresh(force=True))
