"use client";
import { useEffect, useState } from "react";

// Live digital clock in Sri Lanka time, whatever timezone the viewer's device uses.
const timeFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Colombo", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
});
const dateFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Colombo", weekday: "short", day: "numeric", month: "short",
});

export default function LiveClock() {
  // Starts empty so the server-rendered HTML matches the first browser render
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    let timer: ReturnType<typeof setTimeout>;
    const tick = () => {
      setNow(new Date());
      // line up with the start of each second so it doesn't drift
      timer = setTimeout(tick, 1000 - (Date.now() % 1000));
    };
    timer = setTimeout(tick, 1000 - (Date.now() % 1000));
    return () => clearTimeout(timer);
  }, []);

  const [hh, mm, ss] = now ? timeFmt.format(now).split(":") : ["--", "--", "--"];

  return (
    <div className="clock" role="timer" aria-label={now ? `Sri Lanka time ${hh}:${mm}` : "Sri Lanka time"}>
      <span className="clock-time" aria-hidden>
        {hh}<span className="clock-colon">:</span>{mm}<span className="clock-sec">{ss}</span>
      </span>
      <span className="clock-date">{now ? `${dateFmt.format(now)}, Sri Lanka time` : "Sri Lanka time"}</span>
    </div>
  );
}
