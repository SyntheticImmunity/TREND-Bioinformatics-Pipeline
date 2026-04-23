/**
 * Panels D and E of Figure 1: stacked vertical bars of TREND coverage.
 *
 *   variant="cacts"     — Panel D (CaCTS cancer MTFs across TCGA tumor types)
 *   variant="dalessio"  — Panel E (D'Alessio identity TFs across anatomical systems)
 *
 * Red = "In TREND", light grey = "Not in TREND". Percentage label above each bar.
 * Sorted by coverage % descending. Click any bar to apply the corresponding
 * library filter (tumor type or anatomical system).
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

import { api, type CactsRow, type CoverageBundle, type DalessioRow } from "@/lib/api";
import { useLibraryFilter, type LibraryFilterKind } from "@/components/LibraryFilters";

const RED_COVERED = "#E63946";
const GREY_MISSING = "#D6D3CD";

type CoverageRow = (CactsRow | DalessioRow) & { name: string };

interface Props {
  variant: "cacts" | "dalessio";
}

export function StackedCoverageBar({ variant }: Props) {
  const isCacts = variant === "cacts";
  const cactsQuery = useQuery({
    queryKey: ["coverage", "cacts"],
    queryFn: api.cactsCoverage,
    enabled: isCacts,
  });
  const dalessioQuery = useQuery({
    queryKey: ["coverage", "dalessio"],
    queryFn: api.dalessioCoverage,
    enabled: !isCacts,
  });
  const data = isCacts ? cactsQuery.data : dalessioQuery.data;
  const isPending = isCacts ? cactsQuery.isPending : dalessioQuery.isPending;
  const error = isCacts ? cactsQuery.error : dalessioQuery.error;

  const { filter, setFilter } = useLibraryFilter();
  const filterKind: LibraryFilterKind = isCacts ? "cacts_tumor" : "dalessio_system";

  // Always sort by coverage % descending (matches the published figure).
  const rows: CoverageRow[] = useMemo(() => {
    if (!data) return [];
    const list: (CactsRow | DalessioRow)[] = isCacts
      ? ((data as CoverageBundle<CactsRow>).per_tumor ?? [])
      : ((data as CoverageBundle<DalessioRow>).per_system ?? []);
    const named: CoverageRow[] = list.map((r) => ({
      ...r,
      name: isCacts ? (r as CactsRow).tumor : (r as DalessioRow).system,
    }));
    return [...named].sort((a, b) => b.pct - a.pct || b.n_total - a.n_total);
  }, [data, isCacts]);

  if (isPending) return <p className="text-muted">Loading…</p>;
  if (error) return <p className="text-charcoal-82">{String(error)}</p>;

  return (
    <div>
      <div className="flex items-center justify-end gap-3 mb-3 text-xs text-charcoal-82">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: RED_COVERED }} />
          In TREND
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: GREY_MISSING }} />
          Not in TREND
        </span>
      </div>

      <div style={{ width: "100%", height: 380 }}>
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 28, right: 16, bottom: 80, left: 32 }}>
            <CartesianGrid stroke="#eceae4" vertical={false} />
            <XAxis
              dataKey="name"
              interval={0}
              angle={-45}
              textAnchor="end"
              height={70}
              tick={{ fill: "#1c1c1c", fontSize: 10 }}
              label={{
                value: isCacts ? "TCGA tumor type" : "Anatomical system",
                position: "insideBottom",
                offset: -64,
                fill: "#5f5f5d",
                fontSize: 12,
              }}
            />
            <YAxis
              tick={{ fill: "#5f5f5d", fontSize: 11 }}
              label={{
                value: isCacts ? "Number of candidate MTFs" : "Number of candidate core identity TFs",
                angle: -90,
                position: "insideLeft",
                fill: "#5f5f5d",
                fontSize: 12,
                offset: 10,
              }}
              allowDecimals={false}
            />
            <Tooltip
              cursor={{ fill: "rgba(28,28,28,0.04)" }}
              contentStyle={{
                backgroundColor: "#fcfbf8",
                border: "1px solid #eceae4",
                borderRadius: 8,
                fontSize: 12,
              }}
              content={({ active, payload }) => {
                if (!active || !payload || !payload.length) return null;
                const r = payload[0].payload as CoverageRow;
                return (
                  <div className="rounded-comfortable border border-cream-border bg-cream-light px-3 py-2 text-xs text-charcoal-82 max-w-sm">
                    <div className="font-semibold text-charcoal mb-1">{r.name}</div>
                    <div>
                      In TREND:{" "}
                      <span className="font-semibold text-charcoal">
                        {r.n_in}/{r.n_total} ({r.pct}%)
                      </span>
                    </div>
                    {r.in_tfs.length > 0 && (
                      <div className="mt-1.5">
                        <div className="text-[10px] uppercase tracking-wide text-muted">Covered ({r.in_tfs.length})</div>
                        <div className="font-mono text-[10px] leading-snug break-all">
                          {r.in_tfs.slice(0, 12).join(", ")}
                          {r.in_tfs.length > 12 ? ` … +${r.in_tfs.length - 12} more` : ""}
                        </div>
                      </div>
                    )}
                    {r.missing_tfs.length > 0 && (
                      <div className="mt-1.5">
                        <div className="text-[10px] uppercase tracking-wide text-muted">Missing ({r.missing_tfs.length})</div>
                        <div className="font-mono text-[10px] leading-snug break-all">
                          {r.missing_tfs.slice(0, 12).join(", ")}
                          {r.missing_tfs.length > 12 ? ` … +${r.missing_tfs.length - 12} more` : ""}
                        </div>
                      </div>
                    )}
                  </div>
                );
              }}
            />
            <Bar
              dataKey="n_in"
              stackId="cov"
              onClick={(d: CoverageRow) =>
                setFilter({ kind: filterKind, value: d.name, label: d.name })
              }
              style={{ cursor: "pointer" }}
            >
              {rows.map((r) => (
                <Cell
                  key={`in-${r.name}`}
                  fill={RED_COVERED}
                  fillOpacity={
                    filter.kind === filterKind && filter.value && filter.value !== r.name ? 0.3 : 1
                  }
                  stroke={
                    filter.kind === filterKind && filter.value === r.name ? "#1c1c1c" : "none"
                  }
                  strokeWidth={1.5}
                />
              ))}
            </Bar>
            <Bar
              dataKey="n_missing"
              stackId="cov"
              onClick={(d: CoverageRow) =>
                setFilter({ kind: filterKind, value: d.name, label: d.name })
              }
              style={{ cursor: "pointer" }}
            >
              {rows.map((r) => (
                <Cell
                  key={`miss-${r.name}`}
                  fill={GREY_MISSING}
                  fillOpacity={
                    filter.kind === filterKind && filter.value && filter.value !== r.name ? 0.3 : 1
                  }
                />
              ))}
              <LabelList
                dataKey="pct"
                position="top"
                fill="#1c1c1c"
                fontSize={9}
                formatter={(v: number) => `${Math.round(v)}%`}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
