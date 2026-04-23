import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ConstructsPerTfRow } from "@/lib/api";

interface ConstructsPerTfChartProps {
  rows: ConstructsPerTfRow[];
  topN?: number;
}

/** Horizontal bar chart of constructs per TF — visually closer to a ranked stacked bar
 * than a categorical chart, since the dimension is unsorted TFs and the scale matters. */
export function ConstructsPerTfChart({ rows, topN = 20 }: ConstructsPerTfChartProps) {
  const display = rows
    .filter((r) => r.tf !== "Other")
    .slice(0, topN)
    .map((r) => ({ tf: r.tf, count: r.count }));

  return (
    <div className="h-[28rem] w-full">
      <ResponsiveContainer>
        <BarChart
          data={display}
          layout="vertical"
          margin={{ top: 8, right: 32, bottom: 8, left: 24 }}
        >
          <CartesianGrid stroke="#eceae4" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: "#5f5f5d", fontSize: 12 }}
            tickFormatter={(v) => v.toLocaleString()}
          />
          <YAxis
            type="category"
            dataKey="tf"
            width={92}
            tick={{ fill: "#1c1c1c", fontSize: 12, fontFamily: "ui-monospace, monospace" }}
            interval={0}
          />
          <Tooltip
            cursor={{ fill: "rgba(28,28,28,0.04)" }}
            contentStyle={{
              backgroundColor: "#f7f4ed",
              border: "1px solid #eceae4",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value: number) => [value.toLocaleString(), "Constructs"]}
          />
          <Bar dataKey="count" fill="#1c1c1c" fillOpacity={0.82} radius={[0, 3, 3, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
