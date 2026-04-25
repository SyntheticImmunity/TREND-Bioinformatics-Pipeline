import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { type SelectivityPoint } from "@/lib/api";
import { cn } from "@/lib/cn";

const RANK_COLORS = [
  "#1c1c1c", "#5f5f5d", "#9a9991", "#cfcdc6",
  "#E63946", "#F1A340", "#3DAA3D", "#1F77B4",
];

export type HistogramMetric = "selectivity_ratio" | "ov8_activity";

interface Props {
  rows: SelectivityPoint[];
  metric: HistogramMetric;
  onMetricChange: (m: HistogramMetric) => void;
  pwmName: string;
}

export function PwmHistogram({ rows, metric, onMetricChange, pwmName }: Props) {
  const { bars, ranks } = useMemo(() => {
    const values = rows.map((r) => r[metric]);
    const isLog = metric === "selectivity_ratio";
    const transformed = isLog ? values.map((v) => Math.log2(v)) : values;
    const min = Math.min(...transformed);
    const max = Math.max(...transformed);
    const nBins = 12;
    const span = max - min || 1;
    const step = span / nBins;
    const edges = Array.from({ length: nBins + 1 }, (_, i) => min + i * step);

    const ranksSet = Array.from(new Set(rows.map((r) => r.rank ?? 0))).sort((a, b) => a - b);

    const out: Array<Record<string, number | string>> = [];
    for (let b = 0; b < nBins; b++) {
      const lo = edges[b];
      const hi = edges[b + 1];
      const center = (lo + hi) / 2;
      const label = isLog ? `2^${center.toFixed(1)}` : center.toFixed(2);
      const bin: Record<string, number | string> = { x: label, _center: center };
      for (const rk of ranksSet) bin[`rank_${rk}`] = 0;
      for (let i = 0; i < transformed.length; i++) {
        const v = transformed[i];
        if (v >= lo && (v < hi || (b === nBins - 1 && v <= hi))) {
          const rk = rows[i].rank ?? 0;
          (bin[`rank_${rk}`] as number) += 1;
        }
      }
      out.push(bin);
    }
    return { bars: out, ranks: ranksSet };
  }, [rows, metric]);

  const xLabel =
    metric === "selectivity_ratio" ? "Log2(OVR / IOSE)" : "OVR activity (RD ratio)";

  return (
    <div className="mt-6 border-t border-cream-border pt-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h5 className="text-sm font-semibold text-charcoal">
            Activity distribution for{" "}
            <span className="font-mono text-charcoal-82">{pwmName}</span>
          </h5>
          <p className="text-xs text-muted mt-1">
            One bar segment per rank within this PWM. Total enhancers: {rows.length.toLocaleString()}
            {ranks.length > 1 && (
              <>
                {" "}· ranks {ranks[0]}–{ranks[ranks.length - 1]}
              </>
            )}
          </p>
        </div>
        <div
          role="radiogroup"
          aria-label="Histogram metric"
          className="inline-flex rounded-standard border border-cream-border overflow-hidden text-xs"
        >
          <button
            type="button"
            role="radio"
            aria-checked={metric === "selectivity_ratio"}
            onClick={() => onMetricChange("selectivity_ratio")}
            className={cn(
              "px-3 py-1.5 transition-colors",
              metric === "selectivity_ratio"
                ? "bg-charcoal-82 text-cream-light"
                : "bg-cream text-charcoal-82 hover:bg-charcoal-3",
            )}
          >
            Selectivity
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={metric === "ov8_activity"}
            onClick={() => onMetricChange("ov8_activity")}
            className={cn(
              "px-3 py-1.5 transition-colors border-l border-cream-border",
              metric === "ov8_activity"
                ? "bg-charcoal-82 text-cream-light"
                : "bg-cream text-charcoal-82 hover:bg-charcoal-3",
            )}
          >
            OVR activity
          </button>
        </div>
      </div>

      <div style={{ width: "100%", height: 320 }} className="mt-4">
        <ResponsiveContainer>
          <BarChart data={bars} margin={{ top: 8, right: 24, bottom: 36, left: 32 }}>
            <CartesianGrid stroke="#eceae4" vertical={false} />
            <XAxis
              dataKey="x"
              tick={{ fill: "#5f5f5d", fontSize: 10 }}
              label={{
                value: xLabel,
                position: "insideBottom",
                offset: -20,
                fill: "#5f5f5d",
                fontSize: 12,
              }}
            />
            <YAxis
              tick={{ fill: "#5f5f5d", fontSize: 11 }}
              label={{
                value: "# enhancers",
                angle: -90,
                position: "insideLeft",
                offset: 4,
                fill: "#5f5f5d",
                fontSize: 12,
              }}
              allowDecimals={false}
            />
            <Tooltip
              cursor={{ fill: "rgba(28, 28, 28, 0.04)" }}
              content={({ active, payload, label }) => {
                if (!active || !payload || !payload.length) return null;
                return (
                  <div className="rounded-comfortable border border-cream-border bg-cream-light px-3 py-2 text-xs text-charcoal-82">
                    <div className="font-semibold text-charcoal mb-1">{label}</div>
                    {payload.map((p) => (
                      <div key={String(p.dataKey)}>
                        Rank {String(p.dataKey).replace("rank_", "")}: {p.value}
                      </div>
                    ))}
                  </div>
                );
              }}
            />
            {ranks.map((rk, idx) => (
              <Bar key={rk} dataKey={`rank_${rk}`} stackId="rank" name={`Rank ${rk}`}>
                {bars.map((_, bi) => (
                  <Cell key={bi} fill={RANK_COLORS[idx % RANK_COLORS.length]} />
                ))}
              </Bar>
            ))}
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-1 flex flex-wrap justify-center gap-3 text-[10px] text-charcoal-82">
          {ranks.map((rk, idx) => (
            <span key={rk} className="inline-flex items-center gap-1">
              <span
                className="inline-block h-2 w-2 rounded-sm"
                style={{ backgroundColor: RANK_COLORS[idx % RANK_COLORS.length] }}
              />
              Rank {rk}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
