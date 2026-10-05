"use client";
import { useCallback, useEffect, useState } from "react";
import BusFill from "@/components/BusFill";
import DayStrip from "@/components/DayStrip";
import ReportPanel from "@/components/ReportPanel";
import { api, DaySlot, Direction, Prediction, RecentReport } from "@/lib/api";

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

const DIRS: { id: Direction; label: string; sub: string }[] = [
  { id: "to_sliit", label: "To SLIIT", sub: "towards Kaduwela" },
  { id: "from_sliit", label: "From SLIIT", sub: "towards Kollupitiya" },
];

export default function Home() {
  const [direction, setDirection] = useState<Direction>("to_sliit");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [pred, setPred] = useState<Prediction | null>(null);
  const [slots, setSlots] = useState<DaySlot[]>([]);
  const [recent, setRecent] = useState<RecentReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { const n = slNow(); setDate(n.date); setTime(n.time); }, []);

  const loadRecent = useCallback(() => {
    api.recent().then((r) => setRecent(r.reports)).catch(() => {});
  }, []);

  const check = useCallback(async (t = time, d = date, dir = direction) => {
    if (!t || !d) return;
    setLoading(true); setError(null);
    try {
      const [p, day] = await Promise.all([api.predict(dir, t, d), api.day(dir, d)]);
      setPred(p); setSlots(day.slots); setTime(p.departure);
    } catch (e) {
      setError(`Couldn't reach the prediction service. Start the backend and check NEXT_PUBLIC_API_URL. (${(e as Error).message})`);
    } finally {
      setLoading(false);
    }
  }, [time, date, direction]);

  useEffect(() => { if (date && time) check(); loadRecent(); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, direction]);

  return (
    <main>
      <header className="masthead">
        <div className="plate" aria-hidden>
          <span className="plate-num">177</span>
          <span className="plate-dest">Kollupitiya ↔ Kaduwela</span>
        </div>
        <h1>Will I get on the 177?</h1>
        <p className="lede">Predicted crowding for Route 177 on the SLIIT Malabe corridor, before you leave.</p>
      </header>

      <div className="grid">
        <section className="panel ask">
          <div className="seg" role="radiogroup" aria-label="Direction">
            {DIRS.map((d) => (
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
          <button type="button" className="primary" onClick={() => check()} disabled={loading}>
            {loading ? "Checking…" : "Check this bus"}
          </button>
          {error && <p className="err" role="alert">{error}</p>}
        </section>

        <section className={`panel result ${pred ? `lv${pred.level}` : "empty"}`} aria-live="polite">
          {!pred && !error && <p className="muted">Pick a direction and time, then check the bus.</p>}
          {pred && (
            <>
              <p className="when">{pred.departure} bus, {pred.direction === "to_sliit" ? "to SLIIT" : "from SLIIT"}</p>
              <p className="verdict">{pred.label}</p>
              <p className="conf">{Math.round(pred.confidence * 100)}% likely</p>
              <BusFill level={pred.level} />
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
          <h2>The whole day</h2>
          <p className="muted">Taller and darker means more crowded. Tap a bus to check it.</p>
          <DayStrip slots={slots} selected={time} onPick={(t) => check(t)} />
          <ul className="legend">
            <li className="l0">Seats free</li><li className="l1">Standing room</li>
            <li className="l2">Packed</li><li className="l3">Can&apos;t board</li>
          </ul>
        </section>
      )}

      <div className="grid">
        <ReportPanel direction={direction} onSaved={() => { loadRecent(); check(); }} />
        <section className="panel recent">
          <h2>Recent rider reports</h2>
          {recent.length === 0
            ? <p className="muted">No reports in the last three hours. Be the first.</p>
            : (
              <ul>
                {recent.map((r) => (
                  <li key={r.id}>
                    <span className={`dot l${r.level}`} aria-hidden />
                    <span>{r.reported_at}</span>
                    <span>{r.direction === "to_sliit" ? "To SLIIT" : "From SLIIT"}</span>
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
