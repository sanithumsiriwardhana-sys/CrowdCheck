"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import BusFill from "@/components/BusFill";
import DayStrip from "@/components/DayStrip";
import LiveClock from "@/components/LiveClock";
import ReportPanel from "@/components/ReportPanel";
import { api, DaySlot, Direction, Holiday, Prediction, RecentReport } from "@/lib/api";
import { dirLabel, routeByCode, ROUTES } from "@/lib/routes";

const ROUTE_KEY = "crowdcheck.route";

function slNow() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Colombo", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(new Date());
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "00";
  const mins = Math.round(Number(get("minute")) / 10) * 10;
  let hh = Number(get("hour")) % 24;
  let mm = mins;
  if (mm === 60) { hh = (hh + 1) % 24; mm = 0; }
  if (hh * 60 + mm < 330) { hh = 5; mm = 30; }
  if (hh * 60 + mm > 1260) { hh = 21; mm = 0; }
  return {
    date: `${get("year")}-${get("month")}-${get("day")}`,
    time: `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`,
  };
}

function fmtDay(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
}

export default function Home() {
  const [route, setRoute] = useState("177");
  const [direction, setDirection] = useState<Direction>(ROUTES[0].dirs[0].id);
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [pred, setPred] = useState<Prediction | null>(null);
  const [slots, setSlots] = useState<DaySlot[]>([]);
  const [recent, setRecent] = useState<RecentReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nextHoliday, setNextHoliday] = useState<Holiday | null>(null);
  const reqId = useRef(0);

  const info = routeByCode(route);

  useEffect(() => {
    const n = slNow(); setDate(n.date); setTime(n.time);
    api.holidays(n.date, 60).then((r) => setNextHoliday(r.holidays[0] ?? null)).catch(() => {});
    try {
      const saved = localStorage.getItem(ROUTE_KEY);
      if (saved && ROUTES.some((r) => r.code === saved)) {
        setRoute(saved); setDirection(routeByCode(saved).dirs[0].id);
      }
    } catch { /* storage blocked: keep default route */ }
  }, []);

  function pickRoute(code: string) {
    if (code === route) return;
    setRoute(code);
    setDirection(routeByCode(code).dirs[0].id);
    setPred(null); setSlots([]); setRecent([]);
    try { localStorage.setItem(ROUTE_KEY, code); } catch { /* ignore */ }
  }

  const loadRecent = useCallback((r = route) => {
    api.recent(r).then((res) => setRecent(res.reports)).catch(() => {});
  }, [route]);

  const check = useCallback(async (t = time, d = date, dir = direction, r = route) => {
    if (!t || !d) return;
    const id = ++reqId.current;
    setLoading(true); setError(null);
    try {
      const [p, day] = await Promise.all([api.predict(r, dir, t, d), api.day(r, dir, d)]);
      if (id !== reqId.current) return; // a newer request (e.g. route switch) won
      setPred(p); setSlots(day.slots); setTime(p.departure);
    } catch (e) {
      if (id !== reqId.current) return;
      setError(`Couldn't reach the prediction service. Start the backend and check NEXT_PUBLIC_API_URL. (${(e as Error).message})`);
    } finally {
      if (id === reqId.current) setLoading(false);
    }
  }, [time, date, direction, route]);

  useEffect(() => {
    if (date && time) check(time, date, direction, route);
    loadRecent(route);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, direction, route]);

  return (
    <main>
      <div className="topbar">
        <nav className="routes" aria-label="Choose a bus route">
        {ROUTES.map((r) => (
          <button key={r.code} type="button" aria-pressed={r.code === route}
            className={`route-btn ${r.code === route ? "on" : ""}`} onClick={() => pickRoute(r.code)}>
            <span className="route-num">{r.code}</span>
            <span className="route-ends">{r.from} – {r.to}</span>
          </button>
        ))}
        </nav>
        <LiveClock />
      </div>

      <header className="masthead">
        <h1>Will I get on the {route}?</h1>
        <p className="lede">
          Predicted crowding for Route {route}, {info.from} to {info.to}, at the SLIIT Malabe stop. Check before you leave.
        </p>
      </header>

      <div className="grid">
        <section className="panel ask">
          <div className="seg" role="radiogroup" aria-label="Direction">
            {info.dirs.map((d) => (
              <button key={d.id} type="button" role="radio" aria-checked={direction === d.id}
                className={direction === d.id ? "on" : ""} onClick={() => setDirection(d.id)}>
                <strong>{d.label}</strong><small>{d.sub}</small>
              </button>
            ))}
          </div>
          <div className="row">
            <label className="field"><span>Day</span>
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </label>
            <label className="field"><span>Bus time</span>
              <input type="time" value={time} step={600} min="05:30" max="21:00" onChange={(e) => setTime(e.target.value)} />
            </label>
          </div>
          {nextHoliday && (
            <p className="next-holiday">
              Next holiday: <button type="button" className="linkish"
                onClick={() => setDate(nextHoliday.date)}>
                {nextHoliday.name}, {fmtDay(nextHoliday.date)}
              </button>
            </p>
          )}
          <button type="button" className="primary" onClick={() => check()} disabled={loading}>
            {loading ? "Checking…" : "Check this bus"}
          </button>
          {error && <p className="err" role="alert">{error}</p>}
        </section>

        <section className={`panel result ${pred ? `lv${pred.level}` : "empty"}`} aria-live="polite">
          {!pred && !error && <p className="muted">{loading ? "Checking…" : "Pick a direction and time, then check the bus."}</p>}
          {pred && (
            <>
              <p className="when">{pred.departure} bus {dirLabel(pred.route, pred.direction).replace(/^To /, "to ")}</p>
              <p className="verdict">{pred.label}</p>
              <p className="conf">{Math.round(pred.confidence * 100)}% likely</p>
              <BusFill level={pred.level} />
              {pred.day?.note && (
                <p className={`day-note ${pred.day.holiday ? "is-holiday" : ""}`}>{pred.day.note}</p>
              )}
              <p className="tip">{pred.tip}</p>
              {pred.better_option && (
                <button type="button" className="ghost" onClick={() => check(pred.better_option!.time)}>
                  Check the {pred.better_option.time} bus
                </button>
              )}
              <dl className="facts">
                <div><dt>Rain at that hour</dt><dd>{pred.rain_mm} mm</dd></div>
                <div><dt>Live rider reports used</dt><dd>{pred.live_reports_used}</dd></div>
              </dl>
            </>
          )}
        </section>
      </div>

      {slots.length > 0 && (
        <section className="panel day">
          <h2>Route {route} across the day</h2>
          <p className="muted">{dirLabel(route, direction)}. Taller and darker means more crowded. Tap a bus to check it.</p>
          <DayStrip slots={slots} selected={time} onPick={(t) => check(t)} />
          <ul className="legend">
            <li className="l0">Seats free</li><li className="l1">Standing room</li>
            <li className="l2">Packed</li><li className="l3">Can&apos;t board</li>
          </ul>
        </section>
      )}

      <div className="grid">
        <ReportPanel route={route} direction={direction} onSaved={() => { loadRecent(); check(); }} />
        <section className="panel recent">
          <h2>Recent reports on the {route}</h2>
          {recent.length === 0
            ? <p className="muted">No reports in the last three hours. Be the first.</p>
            : (
              <ul>
                {recent.map((r) => (
                  <li key={r.id}>
                    <span className={`dot l${r.level}`} aria-hidden />
                    <span>{r.reported_at}</span>
                    <span>{dirLabel(route, r.direction)}</span>
                    <strong>{r.label}</strong>
                    {r.stop_name && <span className="muted">at {r.stop_name}</span>}
                  </li>
                ))}
              </ul>
            )}
        </section>
      </div>

      <footer>
        <p>Predictions come from a LightGBM model trained on seed data and rider reports. They get better as more people report.</p>
        <p>Built by Siriwardhana P.K.S.M, Prabaswara T.H.U., Nethwin S.W.S and Priyabashitha G.J.S, SLIIT.</p>
      </footer>
    </main>
  );
}
