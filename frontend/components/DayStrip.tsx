"use client";
import { DaySlot, LEVELS } from "@/lib/api";

// Every departure of the day as a coloured bar. Click one to check that bus.
export default function DayStrip({ slots, selected, onPick }: {
  slots: DaySlot[]; selected: string; onPick: (t: string) => void;
}) {
  if (!slots.length) return null;
  return (
    <div className="strip-wrap">
      <div className="strip" role="list">
        {slots.map((s) => (
          <button key={s.time} role="listitem" type="button"
            className={`tick l${s.level} ${s.time === selected ? "sel" : ""}`}
            style={{ height: `${28 + s.level * 14}px` }}
            title={`${s.time}: ${LEVELS[s.level]}`}
            aria-label={`${s.time}, ${LEVELS[s.level]}`}
            onClick={() => onPick(s.time)} />
        ))}
      </div>
      <div className="strip-hours" aria-hidden>
        {slots.filter((s) => s.time.endsWith(":00") && Number(s.time.slice(0, 2)) % 3 === 0 && s.time !== "21:00")
          .map((s) => (
            <span key={s.time} style={{ left: `${(slots.indexOf(s) / slots.length) * 100}%` }}>
              {s.time}
            </span>
          ))}
      </div>
    </div>
  );
}
