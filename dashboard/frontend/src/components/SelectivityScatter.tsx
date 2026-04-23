/**
 * Panel F of Figure 1: cancer-selectivity scatter for the OvCa project.
 *
 * x = log2(OV8 / IOSE) RD ratio  (positive = tumor-selective)
 * y = log10(OV8 RD ratio)        (height = absolute activity in tumor)
 *
 * Cancer-selective enhancers (log2 selectivity >= threshold) are drawn in red;
 * the rest in muted grey. Hover any point for the underlying promoter, TF, and
 * raw ratios. Click to jump to that promoter in the library.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import { api, type SelectivityPoint } from "@/lib/api";

const RED = "#E63946";
const MUTED = "rgba(28, 28, 28, 0.18)";

interface Props {
  project?: string;
}

export function SelectivityScatter({ project = "ovarian_cancer" }: Props) {
  const navigate = useNavigate();
  const { data, isPending, error } = useQuery({
    queryKey: ["selectivity-scatter", project],
    queryFn: () => api.selectivityScatter(project),
  });

  const { selective, background } = useMemo(() => {
    if (!data) return { selective: [] as SelectivityPoint[], background: [] as SelectivityPoint[] };
    return {
      selective: data.rows.filter((r) => r.selective),
      background: data.rows.filter((r) => !r.selective),
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
            {data.n_selective.toLocaleString()} cancer-selective
          </span>{" "}
          (≥{Math.round(2 ** data.selectivity_threshold)}× OV8 / IOSE)
        </p>
        <span className="inline-flex items-center gap-3 text-xs text-charcoal-82">
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: RED }} />
            Cancer-selective
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: MUTED }} />
            Other
          </span>
        </span>
      </div>

      <div style={{ width: "100%", height: 480 }} className="mt-4">
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 16, right: 24, bottom: 56, left: 32 }}>
            <CartesianGrid stroke="#eceae4" />
            <XAxis
              type="number"
              dataKey="x"
              tick={{ fill: "#5f5f5d", fontSize: 11 }}
              label={{
                value: data.x_label,
                position: "insideBottom",
                offset: -36,
                fill: "#5f5f5d",
                fontSize: 12,
              }}
              domain={["auto", "auto"]}
            />
            <YAxis
              type="number"
              dataKey="y"
              tick={{ fill: "#5f5f5d", fontSize: 11 }}
              label={{
                value: data.y_label,
                angle: -90,
                position: "insideLeft",
                offset: 10,
                fill: "#5f5f5d",
                fontSize: 12,
              }}
              domain={["auto", "auto"]}
            />
            <ZAxis range={[18, 18]} />
            <ReferenceLine
              x={data.selectivity_threshold}
              stroke="#1c1c1c"
              strokeDasharray="3 3"
              strokeOpacity={0.4}
              label={{
                value: `≥${Math.round(2 ** data.selectivity_threshold)}× selective`,
                position: "top",
                fill: "#1c1c1c",
                fontSize: 10,
              }}
            />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={({ active, payload }) => {
                if (!active || !payload || !payload.length) return null;
                const p = payload[0].payload as SelectivityPoint;
                return (
                  <div className="rounded-comfortable border border-cream-border bg-cream-light px-3 py-2 text-xs text-charcoal-82 max-w-sm">
                    <div className="font-semibold text-charcoal mb-1">
                      {p.tf || "—"}
                      <span className="ml-2 font-mono text-[11px] text-muted">
                        {p.promoter_name}
                      </span>
                    </div>
                    <div>OV8 / IOSE: <span className="font-semibold text-charcoal">{p.selectivity_ratio.toFixed(1)}×</span></div>
                    <div>OV8 activity: {p.ov8_activity.toFixed(2)}</div>
                    <div>IOSE activity: {p.iose_activity?.toFixed(2) ?? "—"}</div>
                    <div className="text-muted mt-1 text-[10px]">click to view in library</div>
                  </div>
                );
              }}
            />
            {/* Background layer first (drawn underneath) */}
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

      <div className="mt-4 card border-cream-border">
        <h4 className="text-sm font-semibold text-charcoal">Top 10 cancer-selective enhancers</h4>
        <table className="mt-3 w-full text-xs">
          <thead className="text-muted uppercase tracking-wide">
            <tr>
              <th className="text-left font-medium pb-1.5">TF</th>
              <th className="text-left font-medium pb-1.5">Promoter</th>
              <th className="text-right font-medium pb-1.5">OV8 / IOSE</th>
              <th className="text-right font-medium pb-1.5">OV8 activity</th>
            </tr>
          </thead>
          <tbody>
            {data.top_selective.map((r) => (
              <tr key={r.promoter_name} className="border-t border-cream-border">
                <td className="py-1.5 font-mono">{r.tf}</td>
                <td className="py-1.5">
                  <button
                    onClick={() => navigate(`/library/${encodeURIComponent(r.promoter_name)}`)}
                    className="font-mono text-charcoal hover:underline"
                  >
                    {r.promoter_name}
                  </button>
                </td>
                <td className="py-1.5 text-right tabular-nums font-semibold">{r.selectivity_ratio.toFixed(1)}×</td>
                <td className="py-1.5 text-right tabular-nums">{r.ov8_activity.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
