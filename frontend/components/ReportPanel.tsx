"use client";
import { useState } from "react";
import { api, Direction, LEVELS } from "@/lib/api";

export default function ReportPanel({ direction, onSaved }: {
  direction: Direction; onSaved: () => void;
}) {
  const [stop, setStop] = useState("");
  const [busy, setBusy] = useState<number | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function send(level: number) {
    setBusy(level); setErr(null); setMsg(null);
    try {
      const r = await api.report(direction, level, stop.trim());
      setMsg(`Report saved: ${r.label}. ${r.total_reports} reports collected so far.`);
      onSaved();
    } catch (e) {
      setErr(`Couldn't save the report. Check the API is running. (${(e as Error).message})`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="panel report">
      <h2>Just got off a 177?</h2>
      <p className="muted">Tap how full it was. It takes five seconds and makes the next prediction better.</p>
      <label className="field">
        <span>Stop (optional)</span>
        <input value={stop} onChange={(e) => setStop(e.target.value)} placeholder="e.g. Malabe junction" maxLength={80} />
      </label>
      <div className="report-buttons">
        {LEVELS.map((l, i) => (
          <button key={l} type="button" className={`rbtn l${i}`} disabled={busy !== null} onClick={() => send(i)}>
            {busy === i ? "Saving…" : l}
          </button>
        ))}
      </div>
      {msg && <p className="ok" role="status">{msg}</p>}
      {err && <p className="err" role="alert">{err}</p>}
    </section>
  );
}
