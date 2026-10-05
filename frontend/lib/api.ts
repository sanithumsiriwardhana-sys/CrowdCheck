const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Direction = "to_sliit" | "from_sliit";

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
}

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
  predict: (direction: Direction, time: string, date: string) =>
    req<Prediction>("/predict", { method: "POST", body: JSON.stringify({ route: "177", direction, time, date }) }),
  day: (direction: Direction, date: string) =>
    req<{ slots: DaySlot[] }>(`/forecast/day?route=177&direction=${direction}&date=${date}`),
  report: (direction: Direction, crowd_level: number, stop_name?: string) =>
    req<{ id: number; total_reports: number; label: string }>("/report", {
      method: "POST", body: JSON.stringify({ route: "177", direction, crowd_level, stop_name: stop_name || null }),
    }),
  recent: () => req<{ reports: RecentReport[] }>("/reports/recent?route=177&minutes=180"),
};
