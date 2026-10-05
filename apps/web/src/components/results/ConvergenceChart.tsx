import type { ConvergenceIteration } from "@/types/api";

interface Props {
  trace: ConvergenceIteration[];
  toleranceK?: number;
}

const WIDTH = 560;
const HEIGHT = 170;
const PADDING = { top: 12, right: 12, bottom: 28, left: 52 };

/**
 * The residual history, on a log scale.
 *
 * Convergence is a decay over orders of magnitude: on a linear axis the
 * last decade — the part that decides whether the answer is trustworthy —
 * is a flat line on the floor. Inline SVG rather than a charting library,
 * because one series of a few dozen points does not justify the dependency.
 */
export function ConvergenceChart({ trace, toleranceK }: Props) {
  if (trace.length < 2) {
    return null;
  }

  const deltas = trace.map((row) => Math.max(row.max_delta_T_K, 1e-9));
  const floor = toleranceK ? Math.min(toleranceK, ...deltas) : Math.min(...deltas);
  const logMin = Math.log10(Math.max(floor, 1e-9)) - 0.3;
  const logMax = Math.log10(Math.max(...deltas)) + 0.1;
  const span = Math.max(logMax - logMin, 1e-6);

  const plotWidth = WIDTH - PADDING.left - PADDING.right;
  const plotHeight = HEIGHT - PADDING.top - PADDING.bottom;

  const x = (index: number) =>
    PADDING.left + (index / Math.max(trace.length - 1, 1)) * plotWidth;
  const y = (value: number) =>
    PADDING.top + ((logMax - Math.log10(value)) / span) * plotHeight;

  const path = deltas
    .map((value, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(value)}`)
    .join(" ");

  const decades: number[] = [];
  for (let e = Math.ceil(logMin); e <= Math.floor(logMax); e += 1) {
    decades.push(10 ** e);
  }

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      width="100%"
      role="img"
      aria-label={
        `Convergence history: maximum temperature change fell from ` +
        `${deltas[0]!.toPrecision(3)} K to ${deltas[deltas.length - 1]!.toPrecision(3)} K ` +
        `over ${trace.length} iterations.`
      }
    >
      {decades.map((value) => (
        <g key={value}>
          <line
            x1={PADDING.left}
            x2={WIDTH - PADDING.right}
            y1={y(value)}
            y2={y(value)}
            stroke="#e2e8f0"
            strokeWidth={1}
          />
          <text
            x={PADDING.left - 6}
            y={y(value) + 3}
            textAnchor="end"
            fontSize={9}
            fill="#718096"
          >
            {value >= 1 ? value.toString() : value.toExponential(0)}
          </text>
        </g>
      ))}

      {toleranceK !== undefined && toleranceK > 0 && (
        <g>
          <line
            x1={PADDING.left}
            x2={WIDTH - PADDING.right}
            y1={y(toleranceK)}
            y2={y(toleranceK)}
            stroke="#38a169"
            strokeWidth={1.5}
            strokeDasharray="4 3"
          />
          <text
            x={WIDTH - PADDING.right}
            y={y(toleranceK) - 4}
            textAnchor="end"
            fontSize={9}
            fill="#276749"
          >
            tolerance
          </text>
        </g>
      )}

      <path d={path} fill="none" stroke="#2b6cb0" strokeWidth={2} />
      {deltas.map((value, index) => (
        <circle
          key={trace[index]!.iteration}
          cx={x(index)}
          cy={y(value)}
          r={2}
          fill="#2b6cb0"
        />
      ))}

      <line
        x1={PADDING.left}
        x2={WIDTH - PADDING.right}
        y1={HEIGHT - PADDING.bottom}
        y2={HEIGHT - PADDING.bottom}
        stroke="#cbd5e0"
      />
      <text
        x={PADDING.left}
        y={HEIGHT - 8}
        fontSize={9}
        fill="#718096"
      >
        iteration 1
      </text>
      <text
        x={WIDTH - PADDING.right}
        y={HEIGHT - 8}
        fontSize={9}
        fill="#718096"
        textAnchor="end"
      >
        iteration {trace[trace.length - 1]!.iteration}
      </text>
      <text
        x={10}
        y={PADDING.top + 4}
        fontSize={9}
        fill="#718096"
      >
        max ΔT [K]
      </text>
    </svg>
  );
}
