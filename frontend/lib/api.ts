const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Direction = string;

export const LEVELS = ["Seats free", "Standing room", "Packed", "Can't board"] as const;

export interface Prediction {
  route: string;
  direction: Direction;
  date: string;
  departure: string;
  level: number;
  label: string;
  confidence: number;
  probabilities: Record<string, number>;
  rain_mm: number;
  weather_source: string;
  live_reports_used: number;
  better_option: { time: string; level: number; label: string } | null;
  tip: string;
  day?: DayInfo;
}

export interface DayInfo {
  holiday: string | null;
  is_poya: boolean;
  is_long_weekend: boolean;
  is_day_before_holiday: boolean;
  is_day_after_holiday: boolean;
  note: string | null;
}

export interface Holiday { date: string; name: string; poya: boolean }

export interface DaySlot { time: string; level: number; confidence: number }

export interface RecentReport {
  id: number; direction: Direction; level: number; label: string;
  stop_name: string | null; reported_at: string;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ? JSON.stringify(body.detail) : `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  predict: (route: string, direction: Direction, time: string, date: string) =>
    req<Prediction>("/predict", { method: "POST", body: JSON.stringify({ route, direction, time, date }) }),
  day: (route: string, direction: Direction, date: string) =>
    req<{ slots: DaySlot[] }>(`/forecast/day?route=${route}&direction=${direction}&date=${date}`),
  report: (route: string, direction: Direction, crowd_level: number, stop_name?: string) =>
    req<{ id: number; total_reports: number; label: string }>("/report", {
      method: "POST", body: JSON.stringify({ route, direction, crowd_level, stop_name: stop_name || null }),
    }),
  holidays: (start: string, days = 60) =>
    req<{ holidays: Holiday[] }>(`/holidays?start=${start}&days=${days}`),
  recent: (route: string) => req<{ reports: RecentReport[] }>(`/reports/recent?route=${route}&minutes=180`),
};
