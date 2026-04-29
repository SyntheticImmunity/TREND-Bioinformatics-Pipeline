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

export type RankMetric = "selectivity_ratio" | "ov8_activity" | "iose_activity";

interface Props {
  /** All rows for THIS PPM, across every TFBS variant rank 1–10. */
  pwmRows: SelectivityPoint[];
  metric: RankMetric;
  onMetricChange: (m: RankMetric) => void;
  pwmName: string;
  project: string;
  /** TFBS variant rank the user clicked through from; null if unknown. */
  currentRank: number | null;
}

const MAX_RANK = 10;
const BAR_COLOR = "#1c1c1c";
const HIGHLIGHT_COLOR = "#E63946";
const MISSING_STROKE = "#cfcdc6";

function getMetricConfig(project: string): Record<
  RankMetric,
  { tab: string; axis: string }
> {
  if (project === "T_cell_activation") {
    return {
      selectivity_ratio: { tab: "Selectivity", axis: "Stim/Rest Selectivity" },
      ov8_activity: { tab: "Stim Activity", axis: "Stim Activity (RD ratio)" },
      iose_activity: { tab: "Rest Activity", axis: "Rest Activity (RD ratio)" },
    };
  }
  return {
    selectivity_ratio: { tab: "Selectivity", axis: "OV8/IOSE Selectivity" },
    ov8_activity: { tab: "OV8 Activity", axis: "OV8 Activity (RD ratio)" },
    iose_activity: { tab: "IOSE Activity", axis: "IOSE Activity (RD ratio)" },
  };
}

function formatValue(v: number, metric: RankMetric): string {
  if (metric === "selectivity_ratio") return `${v.toFixed(1)}×`;
  return v.toFixed(2);
}

// Pick a "nice" linear axis: a step (1, 2, 2.5, 5, or 10 × 10^n) yielding
// roughly `targetTicks` evenly spaced ticks, an upper bound that's the smallest
// multiple of step >= rawMax, and the corresponding tick array (including 0).
function niceScale(
  rawMax: number,
  targetTicks: number = 5,
): { max: number; ticks: number[] } {
  if (!Number.isFinite(rawMax) || rawMax <= 0) return { max: 1, ticks: [0, 1] };
  const rough = rawMax / targetTicks;
  const exponent = Math.floor(Math.log10(rough));
  const power = Math.pow(10, exponent);
  const fraction = rough / power;
  let stepFraction: number;
  if (fraction <= 1) stepFraction = 1;
  else if (fraction <= 2) stepFraction = 2;
  else if (fraction <= 2.5) stepFraction = 2.5;
  else if (fraction <= 5) stepFraction = 5;
  else stepFraction = 10;
  const step = stepFraction * power;
  const max = Math.ceil(rawMax / step) * step;
  const ticks: number[] = [];
  for (let v = 0; v <= max + 1e-9; v += step) {
    ticks.push(Number(v.toFixed(10)));
  }
  return { max, ticks };
}

interface BarDatum {
  rank: number;
  value: number;
  isMissing: boolean;
  origValue: number | null;
  promoterName: string | null;
  tfbs: string | null;
}

export function PpmRankChart({
  pwmRows,
  metric,
  onMetricChange,
  pwmName,
  project,
  currentRank,
}: Props) {
  const config = getMetricConfig(project);

  const bars: BarDatum[] = useMemo(() => {
    const out: BarDatum[] = [];
    for (let rk = 1; rk <= MAX_RANK; rk++) {
      const matches = pwmRows.filter((r) => r.rank === rk);
      let best: SelectivityPoint | null = null;
      let bestVal = -Infinity;
      for (const m of matches) {
        const v = m[metric];
        if (v == null) continue;
        if (v > bestVal) {
          bestVal = v;
          best = m;
        }
      }
      if (best === null) {
        out.push({
          rank: rk,
          value: 0,
          isMissing: true,
          origValue: null,
          promoterName: null,
          tfbs: null,
        });
      } else {
        out.push({
          rank: rk,
          value: bestVal,
          isMissing: false,
          origValue: bestVal,
          promoterName: best.promoter_name,
          tfbs: best.tfbs_sequence,
        });
      }
    }
    return out;
  }, [pwmRows, metric]);

  const visibleMax = useMemo(() => {
    let m = 0;
    for (const b of bars) {
      if (b.origValue !== null && b.origValue > m) m = b.origValue;
    }
    return m;
  }, [bars]);
  const { max: yMax, ticks: yTicks } = niceScale(visibleMax, 5);

  const tabs: RankMetric[] = [
    "selectivity_ratio",
    "ov8_activity",
    "iose_activity",
  ];

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2 className="text-card-title font-semibold">
            Activity per TFBS variant rank
          </h2>
          <p className="text-xs text-muted mt-1">
            Each bar shows an enhancer at one TFBS variant rank of this PPM
            (<span className="font-mono">{pwmName}</span>).
            {currentRank !== null && (
              <>
                {" "}· clicked variant is{" "}
                <span className="text-charcoal font-semibold">
                  rank {currentRank}
                </span>
              </>
            )}
          </p>
        </div>
        <div
          role="radiogroup"
          aria-label="Activity metric"
          className="inline-flex rounded-standard border border-cream-border overflow-hidden text-xs"
        >
          {tabs.map((m, i) => (
            <button
              key={m}
              type="button"
              role="radio"
              aria-checked={metric === m}
              onClick={() => onMetricChange(m)}
              className={cn(
                "px-3 py-1.5 transition-colors",
                i > 0 && "border-l border-cream-border",
                metric === m
                  ? "bg-charcoal-82 text-cream-light"
                  : "bg-cream text-charcoal-82 hover:bg-charcoal-3",
              )}
            >
              {config[m].tab}
            </button>
          ))}
        </div>
      </div>

      <div style={{ width: "100%", height: 320 }} className="mt-4">
        <ResponsiveContainer>
          <BarChart data={bars} margin={{ top: 8, right: 24, bottom: 36, left: 32 }}>
            <CartesianGrid stroke="#eceae4" vertical={false} />
            <XAxis
              dataKey="rank"
              type="category"
              tickFormatter={(rk) => `Rank ${rk}`}
              tick={{ fill: "#5f5f5d", fontSize: 11 }}
              label={{
                value: "TFBS Variant Rank Within This PPM",
                position: "insideBottom",
                offset: -20,
                fill: "#5f5f5d",
                fontSize: 12,
              }}
            />
            <YAxis
              domain={[0, yMax]}
              ticks={yTicks}
              tick={{ fill: "#5f5f5d", fontSize: 11 }}
              label={{
                value: config[metric].axis,
                angle: -90,
                position: "insideLeft",
                offset: 4,
                fill: "#5f5f5d",
                fontSize: 12,
                style: { textAnchor: "middle" },
              }}
            />
            <Tooltip
              cursor={{ fill: "rgba(28, 28, 28, 0.04)" }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const datum = payload[0].payload as BarDatum;
                return (
                  <div className="rounded-comfortable border border-cream-border bg-cream-light px-3 py-2 text-xs text-charcoal-82">
                    <div className="font-semibold text-charcoal mb-1">
                      Variant rank {datum.rank}
                      {datum.rank === currentRank && (
                        <span className="ml-1.5 text-[10px] font-normal text-muted">
                          · clicked variant
                        </span>
                      )}
                    </div>
                    {datum.isMissing || datum.origValue === null ? (
                      <div className="text-muted">N/A — not in library</div>
                    ) : (
                      <>
                        <div>
                          {config[metric].axis}:{" "}
                          <span className="text-charcoal">
                            {formatValue(datum.origValue, metric)}
                          </span>
                        </div>
                        {datum.tfbs && (
                          <div className="font-mono text-[10px] text-muted mt-1">
                            {datum.tfbs}
                          </div>
                        )}
                        {datum.promoterName && (
                          <div className="font-mono text-[10px] text-muted">
                            {datum.promoterName}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                );
              }}
            />
            <Bar dataKey="value" name="Activity" isAnimationActive={false}>
              {bars.map((b, i) => (
                <Cell
                  key={i}
                  fill={
                    b.isMissing
                      ? "transparent"
                      : b.rank === currentRank
                        ? HIGHLIGHT_COLOR
                        : BAR_COLOR
                  }
                  stroke={b.isMissing ? MISSING_STROKE : undefined}
                  strokeDasharray={b.isMissing ? "3 3" : undefined}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
