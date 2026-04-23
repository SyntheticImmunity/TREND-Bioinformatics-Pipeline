import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { HistogramJSON } from "@/lib/api";

interface HistogramProps {
  data: HistogramJSON;
  xLabel: string;
  yLabel?: string;
  formatXTick?: (v: number) => string;
}

/** Generic histogram renderer. Bin edges are converted to bin centers for x-axis ticks. */
export function Histogram({ data, xLabel, yLabel = "Count", formatXTick }: HistogramProps) {
  const rows = data.counts.map((count, i) => {
    const lo = data.bin_edges[i];
    const hi = data.bin_edges[i + 1] ?? lo;
    const center = (lo + hi) / 2;
    return {
      bin: center,
      binLabel: formatXTick ? formatXTick(center) : `${Math.round(lo)}–${Math.round(hi)}`,
      count,
    };
  });

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 12, right: 12, bottom: 28, left: 8 }}>
          <CartesianGrid stroke="#eceae4" vertical={false} />
          <XAxis
            dataKey="binLabel"
            tick={{ fill: "#5f5f5d", fontSize: 12 }}
            interval="preserveStartEnd"
            label={{
              value: xLabel,
              position: "bottom",
              offset: 12,
              fill: "#5f5f5d",
              fontSize: 12,
            }}
          />
          <YAxis
            tick={{ fill: "#5f5f5d", fontSize: 12 }}
            label={{
              value: yLabel,
              angle: -90,
              position: "insideLeft",
              fill: "#5f5f5d",
              fontSize: 12,
            }}
          />
          <Tooltip
            cursor={{ fill: "rgba(28,28,28,0.04)" }}
            contentStyle={{
              backgroundColor: "#f7f4ed",
              border: "1px solid #eceae4",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value: number) => [value.toLocaleString(), "Count"]}
          />
          <Bar dataKey="count" fill="#1c1c1c" fillOpacity={0.82} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
