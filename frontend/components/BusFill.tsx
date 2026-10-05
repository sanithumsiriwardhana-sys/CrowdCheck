// A top-down floor plan of a Route 177 bus that fills up with the predicted crowd.
const COLS = 11;
const SEAT = 22;
const GAP = 6;

// Deterministic "random" seat pattern so the picture doesn't flicker
const seatTaken = (i: number) => (i * 7 + 3) % 10 < 6;

export default function BusFill({ level }: { level: number }) {
  const width = 40 + COLS * (SEAT + GAP) + 30;
  const rowsY = [16, 16 + SEAT + GAP, 16 + 3 * (SEAT + GAP) + 10, 16 + 4 * (SEAT + GAP) + 10];
  const height = rowsY[3] + SEAT + 22;
  const aisleY = (rowsY[1] + SEAT + rowsY[2]) / 2 - 4;
  const standing = [0, 4, COLS, COLS * 2][level] ?? 0;
  const outside = level === 3 ? 3 : 0;

  const seats = [];
  let n = 0;
  for (const y of rowsY) {
    for (let c = 0; c < COLS; c++) {
      const taken = level >= 1 || seatTaken(n);
      seats.push(
        <rect key={`s${n}`} x={40 + c * (SEAT + GAP)} y={y} width={SEAT} height={SEAT} rx={5}
          className={taken ? "seat taken" : "seat"} />
      );
      n++;
    }
  }

  const people = [];
  for (let i = 0; i < standing; i++) {
    const col = i % COLS;
    const row = Math.floor(i / COLS);
    people.push(
      <circle key={`p${i}`} cx={40 + col * (SEAT + GAP) + SEAT / 2 + (row ? 7 : -3)}
        cy={aisleY + (row ? 8 : 2)} r={6} className="stander" />
    );
  }
  for (let i = 0; i < outside; i++) {
    people.push(<circle key={`o${i}`} cx={14} cy={aisleY - 14 + i * 14} r={6} className="stander outside" />);
  }

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="bus" role="img"
      aria-label={`Bus floor plan showing ${["seats free", "standing room", "a packed bus", "a bus too full to board"][level]}`}>
      <rect x={30} y={6} width={width - 40} height={height - 12} rx={14} className="hull" />
      <rect x={26} y={aisleY - 18} width={8} height={36} rx={2} className="door" />
      <rect x={width - 22} y={16} width={6} height={height - 32} rx={3} className="windscreen" />
      {seats}
      {people}
    </svg>
  );
}
