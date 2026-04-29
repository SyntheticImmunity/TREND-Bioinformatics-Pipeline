import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Customized,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import { api, type SelectivityPoint } from "@/lib/api";
import { CancerSelectiveTable } from "./CancerSelectiveTable";

const RED = "#E63946";
const MUTED = "rgba(28, 28, 28, 0.18)";
const MUTED_LEGEND = "rgba(28, 28, 28, 0.18)";
const GRID_STROKE = "#eceae4";
const Y_GRID_TICKS = [-4, -2, 0, 2, 4];

const SUPERSCRIPT: Record<string, string> = {
  "-": "⁻", "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
  "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
};
function pow2Tick(v: number): string {
  return "2" + String(v).split("").map((c) => SUPERSCRIPT[c] ?? c).join("");
}

interface Props {
  project?: string;
}

interface JitteredPoint extends SelectivityPoint {
  jitter: number;
}

interface BackgroundPoint {
  jitter: number;
  x: number;
}

/**
 * Internal recharts <Customized/> child. Recharts injects layout props
 * (xAxisMap, yAxisMap, offset). We use the d3-style scale functions to
 * draw the gray cloud onto an external <canvas/> in the same coordinate
 * space — much cheaper than 37k SVG circles.
 *
 * The component renders nothing into the SVG itself; all output goes to
 * the canvas via its useEffect.
 */
interface ChartOffset {
  left: number;
  top: number;
  width: number;
  height: number;
}

function CanvasOverlay({
  background,
  canvasRef,
  xAxisMap,
  yAxisMap,
  offset,
}: {
  background: BackgroundPoint[];
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  xAxisMap?: Record<string, { scale: (v: number) => number }>;
  yAxisMap?: Record<string, { scale: (v: number) => number }>;
  offset?: ChartOffset;
}) {
  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv || !xAxisMap || !yAxisMap) return;
    const xKey = Object.keys(xAxisMap)[0];
    const yKey = Object.keys(yAxisMap)[0];
    const xScale = xAxisMap[xKey]?.scale;
    const yScale = yAxisMap[yKey]?.scale;
    if (!xScale || !yScale) return;

    const dpr = window.devicePixelRatio || 1;
    const cssW = cv.clientWidth;
    const cssH = cv.clientHeight;
    if (cssW === 0 || cssH === 0) return;

    // Match canvas backing-store size to its CSS size at the device pixel
    // ratio so points stay crisp on hi-DPI displays.
    cv.width = Math.round(cssW * dpr);
    cv.height = Math.round(cssH * dpr);
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);

    // Draw horizontal gridlines FIRST (under the cloud) so the dense cloud at
    // log2 ≈ 0 covers the gridline that crosses through it. Without this the
    // SVG-rendered gridline showed up as a bright stripe across the cloud.
    if (offset) {
      ctx.strokeStyle = GRID_STROKE;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (const yVal of Y_GRID_TICKS) {
        const py = yScale(yVal);
        if (!Number.isFinite(py)) continue;
        // Snap to a half-pixel for crisper 1px lines.
        const pyAligned = Math.round(py) + 0.5;
        ctx.moveTo(offset.left, pyAligned);
        ctx.lineTo(offset.left + offset.width, pyAligned);
      }
      ctx.stroke();
    }

    // Then draw the cloud on top of the gridlines.
    ctx.fillStyle = MUTED;
    const r = 1.6;
    for (const p of background) {
      const x = xScale(p.jitter);
      const y = yScale(p.x);
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, 2 * Math.PI);
      ctx.fill();
    }
  });

  return null;
}

export function SelectivityScatter({ project = "ovarian_cancer" }: Props) {
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // When the cancer-selective table emits its filtered subset we stash the
  // matching promoter names in a Set; the chart's red Scatter then renders
  // only those points. `null` means "no filter applied" → render everything.
  const [activeFilterNames, setActiveFilterNames] = useState<Set<string> | null>(null);

  const { data, isPending, error } = useQuery({
    queryKey: ["selectivity-scatter", project],
    queryFn: () => api.selectivityScatter(project),
  });

  // True random jitter, memoized per project so it stays stable across renders.
  // Selective points stay as full SelectivityPoint objects (rendered in SVG —
  // hoverable, clickable). Background points are stripped to {jitter, x} so
  // we don't carry promoter metadata into the canvas pipeline.
  const { selective, background } = useMemo(() => {
    if (!data) {
      return {
        selective: [] as JitteredPoint[],
        background: [] as BackgroundPoint[],
      };
    }
    const sel: JitteredPoint[] = [];
    const bg: BackgroundPoint[] = [];
    for (const r of data.rows) {
      const j = Math.random();
      if (r.selective) {
        sel.push({ ...r, jitter: j });
      } else {
        bg.push({ jitter: j, x: r.x });
      }
    }
    return { selective: sel, background: bg };
  }, [data]);

  // Reset filter visibility whenever the underlying selective set changes
  // (e.g., switching projects).
  useEffect(() => {
    setActiveFilterNames(null);
  }, [selective]);

  // Only the subset of selective points the table currently shows.
  const visibleSelective = useMemo(() => {
    if (activeFilterNames === null) return selective;
    return selective.filter((p) => activeFilterNames.has(p.promoter_name));
  }, [selective, activeFilterNames]);

  // Stable callback so the table's effect dependency doesn't re-fire each render.
  const handleFilteredRowsChange = useCallback(
    (rows: SelectivityPoint[]) => {
      setActiveFilterNames((prev) => {
        // No filter → null. Compare to selective.length via the closure below
        // by checking whether every selective row is present.
        if (rows.length === 0) return new Set();
        // We can't reach `selective` cleanly here without making this depend
        // on it; use a name-set anyway since the chart uses Set lookup.
        const next = new Set(rows.map((r) => r.promoter_name));
        // Keep `null` (no filter) when the table is showing the full set.
        if (prev === null && rows.length === selectiveCountRef.current) return null;
        return next;
      });
    },
    [],
  );

  // Track the full selective count without making handleFilteredRowsChange
  // recreate on every render — keeps the table's effect deps stable.
  const selectiveCountRef = useRef(0);
  useEffect(() => {
    selectiveCountRef.current = selective.length;
    // If the new selective set fully matches the current filter set, treat as "no filter."
    if (activeFilterNames !== null && activeFilterNames.size === selective.length) {
      setActiveFilterNames(null);
    }
  }, [selective, activeFilterNames]);

  if (isPending) return <p className="text-muted">Loading…</p>;
  if (error) return <p className="text-charcoal-82">{String(error)}</p>;
  if (!data) return null;

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-3 text-sm">
        <p className="text-muted">
          {data.n_total.toLocaleString()} promoters passing QC ·{" "}
          <span className="text-charcoal font-semibold">
            {data.n_selective.toLocaleString()} selective
          </span>{" "}
          (≥{Math.round(2 ** data.selectivity_threshold)}× {data.title})
        </p>
        <span className="inline-flex items-center gap-3 text-xs text-charcoal-82">
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: RED }} />
            Selective
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span
              className="inline-block w-3 h-3 rounded-full"
              style={{ backgroundColor: MUTED_LEGEND }}
            />
            Other
          </span>
        </span>
      </div>

      <div className="mt-6 text-center text-sm font-semibold text-charcoal">{data.title}</div>

      {/* Canvas overlay holds the gray cloud; recharts (SVG) holds axes,
          grid, the 789 selective points, and the tooltip. They're stacked
          in the same relative wrapper so they share a coordinate space. */}
      <div
        className="mt-2"
        style={{ width: "100%", height: 460, position: "relative" }}
      >
        <canvas
          ref={canvasRef}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            pointerEvents: "none",
          }}
        />
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 16, right: 32, bottom: 16, left: 56 }}>
            <XAxis
              type="number"
              dataKey="jitter"
              domain={[0, 1]}
              tick={false}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="number"
              dataKey="x"
              tick={{ fill: "#5f5f5d", fontSize: 11 }}
              label={{
                value: "Log2 (cancer/normal)",
                angle: -90,
                position: "insideLeft",
                offset: 4,
                fill: "#5f5f5d",
                fontSize: 12,
              }}
              domain={["auto", "auto"]}
              ticks={[-4, -2, 0, 2, 4]}
              tickFormatter={pow2Tick}
            />
            <ZAxis range={[16, 16]} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={({ active, payload }) => {
                if (!active || !payload || !payload.length) return null;
                const p = payload[0].payload as SelectivityPoint;
                return (
                  <div className="rounded-comfortable border border-cream-border bg-cream-light px-3 py-2 text-xs text-charcoal-82 max-w-sm">
                    <div className="font-semibold text-charcoal mb-1">{p.tf || "—"}</div>
                    <div className="font-mono text-[11px] text-muted mb-1.5">{p.promoter_name}</div>
                    <div>OV8 activity: <span className="text-charcoal">{p.ov8_activity.toFixed(2)}</span></div>
                    <div>IOSE activity: <span className="text-charcoal">{p.iose_activity?.toFixed(2) ?? "—"}</span></div>
                    <div className="text-muted mt-1 text-[10px]">click to view in library</div>
                  </div>
                );
              }}
            />
            {/* Customized exposes recharts' layout props; we only use them to
                paint the canvas — nothing is rendered into the SVG here. */}
            <Customized
              component={(props: unknown) => {
                const p = props as {
                  xAxisMap?: Record<string, { scale: (v: number) => number }>;
                  yAxisMap?: Record<string, { scale: (v: number) => number }>;
                  offset?: ChartOffset;
                };
                return (
                  <CanvasOverlay
                    background={background}
                    canvasRef={canvasRef}
                    xAxisMap={p.xAxisMap}
                    yAxisMap={p.yAxisMap}
                    offset={p.offset}
                  />
                );
              }}
            />
            <Scatter
              name="Cancer-selective"
              data={visibleSelective}
              fill={RED}
              fillOpacity={0.85}
              isAnimationActive={false}
              onClick={(e) => {
                const p = e as unknown as SelectivityPoint;
                if (p?.promoter_name) navigate(`/library/${encodeURIComponent(p.promoter_name)}`);
              }}
              style={{ cursor: "pointer" }}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-6">
        <CancerSelectiveTable
          rows={selective}
          project={project}
          title={data.title}
          onFilteredRowsChange={handleFilteredRowsChange}
        />
      </div>
    </div>
  );
}
