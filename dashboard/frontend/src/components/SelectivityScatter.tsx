import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  CartesianGrid,
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

export function SelectivityScatter({ project = "ovarian_cancer" }: Props) {
  const navigate = useNavigate();
  const { data, isPending, error } = useQuery({
    queryKey: ["selectivity-scatter", project],
    queryFn: () => api.selectivityScatter(project),
  });

  // True random jitter, memoized per project so it stays stable across renders
  // (a deterministic LCG produced visible diagonal banding).
  const { selective, background } = useMemo(() => {
    if (!data) return { selective: [] as JitteredPoint[], background: [] as JitteredPoint[] };
    const jittered: JitteredPoint[] = data.rows.map((r) => ({ ...r, jitter: Math.random() }));
    return {
      selective: jittered.filter((r) => r.selective),
      background: jittered.filter((r) => !r.selective),
    };
  }, [data]);

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
            <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: MUTED }} />
            Other
          </span>
        </span>
      </div>

      <div className="mt-6 text-center text-sm font-semibold text-charcoal">{data.title}</div>
      <div style={{ width: "100%", height: 460 }} className="mt-2">
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 16, right: 32, bottom: 16, left: 56 }}>
            <CartesianGrid stroke="#eceae4" horizontal vertical={false} />
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
                    <div>OVR activity: <span className="text-charcoal">{p.ov8_activity.toFixed(2)}</span></div>
                    <div>IOSE activity: <span className="text-charcoal">{p.iose_activity?.toFixed(2) ?? "—"}</span></div>
                    <div className="text-muted mt-1 text-[10px]">click to view in library</div>
                  </div>
                );
              }}
            />
            <Scatter
              name="Other"
              data={background}
              fill={MUTED}
              fillOpacity={0.6}
              isAnimationActive={false}
            />
            <Scatter
              name="Cancer-selective"
              data={selective}
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
        <CancerSelectiveTable rows={selective} project={project} title={data.title} />
      </div>
    </div>
  );
}
