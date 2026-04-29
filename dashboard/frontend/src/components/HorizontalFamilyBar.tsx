/**
 * Panels B and C of Figure 1: horizontal bar chart of DBD families.
 *
 *   variant="tfs"     — # TFs per family   (Panel B; sort-by-TF-count desc)
 *   variant="sensors" — # sensors per family (Panel C; sort-by-sensor-count desc)
 *
 * Each family carries a stable color from the backend so Panels B and C are
 * visually keyed to the same hue per family. Click any bar to set the active
 * library filter to that DBD family.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api, type DbdFamily } from "@/lib/api";
import { useLibraryFilter } from "@/components/LibraryFilters";

interface Props {
  variant: "tfs" | "sensors";
}

export function HorizontalFamilyBar({ variant }: Props) {
  const { data, isPending, error } = useQuery({
    queryKey: ["dbd-families"],
    queryFn: api.dbdFamilies,
  });
  const { filter, setFilter } = useLibraryFilter();

  const sorted = useMemo(() => {
    if (!data) return [];
    const key = variant === "tfs" ? "n_tfs" : "n_sensors";
    return [...data.families].sort((a, b) => b[key] - a[key]);
  }, [data, variant]);

  const dataKey = variant === "tfs" ? "n_tfs" : "n_sensors";
  const xLabel = variant === "tfs" ? "Number of TFs in TREND library" : "Total number of enhancer-reporter constructs (sensors)";

  if (isPending) return <p className="text-muted">Loading…</p>;
  if (error) return <p className="text-charcoal-82">{String(error)}</p>;

  // Chart height scales with row count so each bar has a consistent ~22px slot.
  const ROW_HEIGHT = 22;
  const chartHeight = Math.max(380, sorted.length * ROW_HEIGHT + 60);

  return (
    <div style={{ width: "100%", height: chartHeight }}>
      <ResponsiveContainer>
        <BarChart
          data={sorted}
          layout="vertical"
          margin={{ top: 8, right: 56, bottom: 36, left: 24 }}
        >
          <CartesianGrid stroke="#eceae4" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: "#5f5f5d", fontSize: 11 }}
            tickFormatter={(v) => Number(v).toLocaleString()}
            label={{
              value: xLabel,
              position: "bottom",
              offset: 16,
              fill: "#5f5f5d",
              fontSize: 12,
            }}
          />
          <YAxis
            type="category"
            dataKey="family"
            width={260}
            interval={0}
            tick={({ x, y, payload }) => (
              <text
                x={x}
                y={y}
                dy={4}
                textAnchor="end"
                fill="#1c1c1c"
                fontSize={11}
              >
                {payload.value}
              </text>
            )}
          />
          <Tooltip
            cursor={{ fill: "rgba(28,28,28,0.04)" }}
            content={({ active, payload }) => {
              if (!active || !payload || !payload.length) return null;
              const f = payload[0].payload as DbdFamily;
              return (
                <div className="rounded-comfortable border border-cream-border bg-cream-light px-3 py-2 text-xs text-charcoal-82">
                  <div className="font-semibold text-charcoal mb-0.5">{f.family}</div>
                  <div>{f.n_tfs.toLocaleString()} TFs · {f.n_sensors.toLocaleString()} sensors</div>
                  <div className="text-muted mt-1 text-[10px]">click to filter</div>
                </div>
              );
            }}
          />
          <Bar
            dataKey={dataKey}
            radius={[0, 3, 3, 0]}
            onClick={(d: DbdFamily) =>
              setFilter({ kind: "dbd_family", value: d.family, label: d.family })
            }
            style={{ cursor: "pointer" }}
          >
            {sorted.map((f) => (
              <Cell
                key={f.family}
                fill={f.color}
                fillOpacity={
                  filter.kind === "dbd_family" && filter.value && filter.value !== f.family ? 0.3 : 1
                }
                stroke={filter.kind === "dbd_family" && filter.value === f.family ? "#1c1c1c" : "none"}
                strokeWidth={1.5}
              />
            ))}
            <LabelList
              dataKey={dataKey}
              position="right"
              fill="#1c1c1c"
              fontSize={11}
              fontWeight={600}
              formatter={(v: number) => Number(v).toLocaleString()}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
