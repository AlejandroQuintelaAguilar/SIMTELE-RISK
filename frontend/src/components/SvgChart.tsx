import type { ChartPayload } from "../services/api";

const PALETTE = [
  "#38bdf8",
  "#4ade80",
  "#fbbf24",
  "#f472b6",
  "#a78bfa",
  "#fb7185",
];

function formatAxisVal(v: number, isLog: boolean): string {
  if (isLog) {
    return `1e${Math.round(v)}`;
  }
  if (Math.abs(v) >= 1000 || (Math.abs(v) > 0 && Math.abs(v) < 1e-2)) {
    return v.toExponential(1);
  }
  return v.toFixed(2);
}

export function SvgChart({ chart }: { chart: ChartPayload }) {
  const width = 540;
  const height = 290;
  const padL = 62;
  const padR = 20;
  const padT = 20;
  const padB = 42;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;
  const isLog = chart.y_scale === "log";

  const allX: number[] = [];
  const allY: number[] = [];

  for (const s of chart.series) {
    for (let i = 0; i < Math.min(s.x.length, s.y.length); i++) {
      const xv = s.x[i];
      const yv = s.y[i];
      if (!Number.isFinite(xv) || !Number.isFinite(yv)) continue;
      if (isLog && yv <= 0) continue;
      allX.push(xv);
      allY.push(isLog ? Math.log10(yv) : yv);
    }
  }

  const xMin = allX.length > 0 ? Math.min(...allX) : 0;
  const xMax = allX.length > 0 ? Math.max(...allX) : 1;
  const rawYMin = allY.length > 0 ? Math.min(...allY) : 0;
  const rawYMax = allY.length > 0 ? Math.max(...allY) : 1;

  const xSpan = xMax - xMin || 1;
  const ySpanRaw = rawYMax - rawYMin || 1;
  const yMin = rawYMin - ySpanRaw * 0.06;
  const yMax = rawYMax + ySpanRaw * 0.06;
  const ySpan = yMax - yMin || 1;

  const mapX = (x: number) => padL + ((x - xMin) / xSpan) * plotW;
  const mapY = (y: number) => padT + plotH - ((y - yMin) / ySpan) * plotH;

  const ticks = [0, 0.25, 0.5, 0.75, 1];

  return (
    <div className="card" style={{ padding: "1rem" }}>
      <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.95rem" }}>{chart.titulo}</h4>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: "100%", height: "auto", background: "#0f172a", borderRadius: "8px" }}
      >
        {ticks.map((t) => {
          const yVal = yMin + t * ySpan;
          const yPos = mapY(yVal);
          const xVal = xMin + t * xSpan;
          const xPos = mapX(xVal);
          return (
            <g key={t}>
              <line
                x1={padL}
                y1={yPos}
                x2={width - padR}
                y2={yPos}
                stroke="#1e293b"
                strokeWidth="1"
              />
              <text
                x={padL - 8}
                y={yPos + 4}
                textAnchor="end"
                fill="#94a3b8"
                fontSize="10"
              >
                {formatAxisVal(yVal, isLog)}
              </text>
              <line
                x1={xPos}
                y1={padT}
                x2={xPos}
                y2={height - padB}
                stroke="#1e293b"
                strokeWidth="1"
              />
              <text
                x={xPos}
                y={height - padB + 15}
                textAnchor="middle"
                fill="#94a3b8"
                fontSize="10"
              >
                {formatAxisVal(xVal, false)}
              </text>
            </g>
          );
        })}

        <line x1={padL} y1={padT} x2={padL} y2={height - padB} stroke="#475569" strokeWidth="1.2" />
        <line x1={padL} y1={height - padB} x2={width - padR} y2={height - padB} stroke="#475569" strokeWidth="1.2" />

        {chart.series.map((s, sIdx) => {
          const color = PALETTE[sIdx % PALETTE.length];
          const pts: { px: number; py: number }[] = [];
          for (let i = 0; i < Math.min(s.x.length, s.y.length); i++) {
            const xv = s.x[i];
            const yv = s.y[i];
            if (!Number.isFinite(xv) || !Number.isFinite(yv)) continue;
            if (isLog && yv <= 0) continue;
            pts.push({
              px: mapX(xv),
              py: mapY(isLog ? Math.log10(yv) : yv),
            });
          }

          if (pts.length === 0) return null;

          if (s.mode === "markers") {
            return (
              <g key={s.name}>
                {pts.map((pt, idx) => (
                  <circle
                    key={idx}
                    cx={pt.px}
                    cy={pt.py}
                    r={3.5}
                    fill={color}
                    stroke="#0f172a"
                    strokeWidth="1"
                  />
                ))}
              </g>
            );
          }

          const pathD = pts
            .map((pt, idx) => `${idx === 0 ? "M" : "L"}${pt.px.toFixed(2)},${pt.py.toFixed(2)}`)
            .join(" ");
          return (
            <path
              key={s.name}
              d={pathD}
              fill="none"
              stroke={color}
              strokeWidth="2"
              strokeLinejoin="round"
            />
          );
        })}

        <text
          x={padL + plotW / 2}
          y={height - 6}
          textAnchor="middle"
          fill="#cbd5e1"
          fontSize="10.5"
        >
          {chart.x_label}
        </text>
        <text
          x={14}
          y={padT + plotH / 2}
          textAnchor="middle"
          fill="#cbd5e1"
          fontSize="10.5"
          transform={`rotate(-90 14 ${padT + plotH / 2})`}
        >
          {chart.y_label}
        </text>
      </svg>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginTop: "0.4rem" }}>
        {chart.series.map((s, sIdx) => (
          <div
            key={s.name}
            style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.78rem", color: "var(--muted)" }}
          >
            <span
              style={{
                width: "10px",
                height: "10px",
                borderRadius: s.mode === "markers" ? "50%" : "2px",
                background: PALETTE[sIdx % PALETTE.length],
                display: "inline-block",
              }}
            />
            <span>{s.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
