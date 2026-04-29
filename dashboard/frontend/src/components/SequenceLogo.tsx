/**
 * Sequence logo from a position probability matrix.
 *
 * `ppm` is a 4-row matrix in A/C/G/T order. Letter heights use the standard
 * bits convention: height(letter, position) = p · IC where
 * IC = 2 - H and H = -Σ p · log2(p). Letters are stacked tallest-on-top.
 */

interface Props {
  ppm: number[][];          // [A_probs, C_probs, G_probs, T_probs]
  width?: number;
  height?: number;
  showAxis?: boolean;
}

const COLORS = ["#3DAA3D", "#1F77B4", "#F1A340", "#D62728"]; // A, C, G, T
const LETTERS = ["A", "C", "G", "T"];

// Cap-height of the rendered font as a fraction of fontSize. Tuned for
// 'ui-monospace'/'SF Mono'/Consolas — the letter occupies ~0.72em vertically.
const CAP_HEIGHT_RATIO = 0.72;

function informationContent(ppm: number[][], i: number): number {
  let h = 0;
  for (let j = 0; j < 4; j++) {
    const p = ppm[j][i];
    if (p > 0) h -= p * Math.log2(p);
  }
  return Math.max(0, 2 - h);
}

export function SequenceLogo({ ppm, width = 120, height = 40, showAxis = false }: Props) {
  if (!ppm || ppm.length !== 4 || ppm[0].length === 0) {
    return <span className="text-muted text-xs">—</span>;
  }
  const nPos = ppm[0].length;
  const axisWidth = showAxis ? 0.6 : 0;
  // Padding between the axis line and the first letter so the letter doesn't
  // visually overlap the axis (was 0 before, which let position-1 glyphs
  // cover the vertical line).
  const axisGap = showAxis ? 0.2 : 0;
  const letterStart = axisWidth + axisGap;
  const viewW = nPos + letterStart;
  const viewH = 2;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${viewW} ${viewH}`}
      preserveAspectRatio="none"
      role="img"
      aria-label={`Sequence logo, ${nPos} positions`}
    >
      {showAxis && (
        <g>
          <line
            x1={axisWidth}
            y1={0}
            x2={axisWidth}
            y2={viewH}
            stroke="#5f5f5d"
            strokeWidth={0.04}
            vectorEffect="non-scaling-stroke"
          />
          <text
            x={axisWidth - 0.1}
            y={0}
            fontSize={0.3}
            textAnchor="end"
            dominantBaseline="hanging"
            fill="#5f5f5d"
          >
            2
          </text>
          <text
            x={axisWidth - 0.1}
            y={viewH}
            fontSize={0.3}
            textAnchor="end"
            dominantBaseline="alphabetic"
            fill="#5f5f5d"
          >
            0
          </text>
        </g>
      )}
      {Array.from({ length: nPos }).map((_, i) => {
        const ic = informationContent(ppm, i);
        const letters = LETTERS.map((letter, j) => ({
          letter,
          color: COLORS[j],
          p: ppm[j][i],
        }))
          .filter((l) => l.p > 0 && ic > 0)
          .sort((a, b) => b.p - a.p);

        let yCursor = viewH - ic; // stack drawn from this y down to viewH (bottom)
        return letters.map(({ letter, color, p }) => {
          const h = p * ic;
          if (h < 0.005) return null;
          const top = yCursor;
          yCursor += h;
          return (
            <text
              key={`${i}-${letter}`}
              x={i + letterStart}
              y={top + h}
              fontSize={h / CAP_HEIGHT_RATIO}
              fontFamily="ui-monospace, 'SF Mono', Consolas, monospace"
              fontWeight={900}
              fill={color}
              textLength={1}
              lengthAdjust="spacingAndGlyphs"
              style={{ userSelect: "none" }}
            >
              {letter}
            </text>
          );
        });
      })}
    </svg>
  );
}
