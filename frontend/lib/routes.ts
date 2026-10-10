// Routes shown in the app. Keep in sync with ROUTES in backend/ml/features.py.
export interface RouteDir { id: string; label: string; sub: string }
export interface RouteInfo { code: string; from: string; to: string; dirs: [RouteDir, RouteDir] }

export const ROUTES: RouteInfo[] = [
  {
    code: "177", from: "Kollupitiya", to: "Kaduwela",
    dirs: [
      { id: "to_kaduwela", label: "To Kaduwela", sub: "via SLIIT, Malabe" },
      { id: "to_kollupitiya", label: "To Kollupitiya", sub: "into Colombo" },
    ],
  },
  {
    code: "170", from: "Athurugiriya", to: "Pettah",
    dirs: [
      { id: "to_athurugiriya", label: "To Athurugiriya", sub: "via Malabe" },
      { id: "to_pettah", label: "To Pettah", sub: "into Colombo" },
    ],
  },
  {
    code: "190", from: "Meegoda", to: "Pettah",
    dirs: [
      { id: "to_meegoda", label: "To Meegoda", sub: "via Malabe" },
      { id: "to_pettah", label: "To Pettah", sub: "into Colombo" },
    ],
  },
  {
    code: "17", from: "Panadura", to: "Kandy",
    dirs: [
      { id: "to_kandy", label: "To Kandy", sub: "via Malabe, Kaduwela" },
      { id: "to_panadura", label: "To Panadura", sub: "via Maharagama" },
    ],
  },
];

export const routeByCode = (code: string) => ROUTES.find((r) => r.code === code) ?? ROUTES[0];
export const dirLabel = (code: string, dir: string) =>
  routeByCode(code).dirs.find((d) => d.id === dir)?.label ?? dir;
