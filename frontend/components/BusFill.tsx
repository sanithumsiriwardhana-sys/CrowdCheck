// Top-down floor plan of a 54-seat Sri Lankan route bus that fills up with the
// predicted crowd. Front (driver, windscreen) is on the right, doors on the bottom.
//
// Layout: 12 rows of 2 + 2 seats either side of the aisle (48) and a
// 6-seat bench across the back = 54 seats.

const ROWS = 12;          // seat rows front to back
const SEAT = 24;          // seat size
const GAP = 5;            // gap between seats
const AISLE = 34;         // aisle width
const BENCH = 6;          // seats on the back bench

// Deterministic "random" pattern so the picture doesn't flicker between renders
const seatTaken = (i: number) => (i * 7 + 3) % 10 < 6;

// How many people stand in the aisle / hang off the footboard for each level
const STANDING = [0, 8, 26, 30];
const FOOTBOARD = [0, 0, 0, 4];

export default function BusFill({ level }: { level: number }) {
  // Vertical positions: two seat lines on top, aisle, two seat lines below
  const top = 22;
  const r1 = top;
  const r2 = r1 + SEAT + GAP;
  const aisleTop = r2 + SEAT + 4;
  const aisleBottom = aisleTop + AISLE;
  const r3 = aisleBottom + 4;
  const r4 = r3 + SEAT + GAP;
  const hullBottom = r4 + SEAT + 14;
  const aisleMid = (aisleTop + aisleBottom) / 2;

  // Horizontal positions: back bench, seat rows, driver area, windscreen
  const hullLeft = 18;
  const benchX = hullLeft + 14;
  const rowsX = benchX + SEAT + 12;
  const rowX = (c: number) => rowsX + c * (SEAT + GAP);
  const driverX = rowX(ROWS) + 14;
  const width = driverX + SEAT + 40;
  const hullRight = width - 10;
  const height = hullBottom + 22; // room for footboard riders below the hull

  const seats: JSX.Element[] = [];
  let n = 0;
  const seatEl = (x: number, y: number, w: number, h: number) => {
    const taken = level >= 1 || seatTaken(n);
    seats.push(
      <rect key={`s${n}`} x={x} y={y} width={w} height={h} rx={5}
        className={taken ? "seat taken" : "seat"} />
    );
    n++;
  };

  // 12 rows x 4 seats
  for (let c = 0; c < ROWS; c++) {
    for (const y of [r1, r2, r3, r4]) seatEl(rowX(c), y, SEAT, SEAT);
  }
  // Back bench: 6 seats across the full width
  const benchSpan = r4 + SEAT - r1;
  const benchH = (benchSpan - (BENCH - 1) * 4) / BENCH;
  for (let i = 0; i < BENCH; i++) seatEl(benchX, r1 + i * (benchH + 4), SEAT, benchH);

  // Standing passengers: aisle slots from the front (near the door) to the back
  const slots: [number, number][] = [];
  for (let c = ROWS - 1; c >= 0; c--) {
    const cx = rowX(c) + SEAT / 2;
    slots.push([cx - 4, aisleMid - 8], [cx + 6, aisleMid + 8]);
  }
  // Extra standing room by the front door, next to the driver
  slots.unshift([driverX + 6, aisleMid + 4], [driverX + 6, r3 + 12], [driverX + 18, aisleMid - 6], [driverX + 20, r3 + 16]);

  const people: JSX.Element[] = [];
  const standing = Math.min(STANDING[level] ?? 0, slots.length);
  for (let i = 0; i < standing; i++) {
    const [cx, cy] = slots[i];
    people.push(<circle key={`p${i}`} cx={cx} cy={cy} r={6} className="stander" />);
  }

  // Doors on the bottom side: front (by the driver) and middle
  const frontDoorX = driverX - 4;
  const midDoorX = rowX(5) - 2;
  const doorW = SEAT + 22;

  // People hanging off the footboard (can't board)
  const riders = FOOTBOARD[level] ?? 0;
  for (let i = 0; i < riders; i++) {
    const door = i % 2 === 0 ? frontDoorX : midDoorX;
    const off = Math.floor(i / 2) * 14 + 9;
    people.push(<circle key={`o${i}`} cx={door + off} cy={hullBottom + 9} r={6} className="stander outside" />);
  }

  const levelText = ["seats free", "standing room", "a packed bus", "a bus too full to board"][level];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="bus" role="img"
      aria-label={`54-seat bus floor plan showing ${levelText}`}>
      <rect x={hullLeft} y={8} width={hullRight - hullLeft} height={hullBottom - 8} rx={16} className="hull" />
      <rect x={hullRight - 8} y={20} width={6} height={hullBottom - 32} rx={3} className="windscreen" />
      {/* driver seat and steering wheel */}
      <rect x={driverX} y={r1} width={SEAT} height={SEAT} rx={5} className="driver" />
      <circle cx={driverX + SEAT + 12} cy={r1 + SEAT / 2} r={9} className="wheel" />
      {/* doors */}
      <rect x={frontDoorX} y={hullBottom - 4} width={doorW} height={6} rx={2} className="door" />
      <rect x={midDoorX} y={hullBottom - 4} width={doorW} height={6} rx={2} className="door" />
      {seats}
      {people}
    </svg>
  );
}
