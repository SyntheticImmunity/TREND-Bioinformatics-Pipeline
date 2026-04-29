import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api, type SelectivityPoint } from "@/lib/api";
import { cn } from "@/lib/cn";
import { SequenceLogo } from "./SequenceLogo";

interface Props {
  rows: SelectivityPoint[];
  project: string;
  /** Project metric label, e.g. "OV8/IOSE" for OvCa or "Stim/Rest" for T-cell. */
  title: string;
  /**
   * Fires whenever the in-table column filters change which rows are visible.
   * Used by the parent strip plot to mirror the filter — non-matching red
   * dots are hidden so the chart and table stay in sync as the user types.
   */
  onFilteredRowsChange?: (rows: SelectivityPoint[]) => void;
}

type SortCol =
  | "naturalRank"
  | "tf"
  | "promoter_name"
  | "by_ppm_name"
  | "rank"
  | "selectivity_ratio"
  | "ov8_activity"
  | "iose_activity";

type SortDir = "asc" | "desc";

interface Sort {
  col: SortCol;
  dir: SortDir;
}

interface ColumnDef {
  id: SortCol | "logo";
  header: string;
  align?: "left" | "right";
  sortable: boolean;
  filterable?: boolean;
  width?: string;
}

interface RankedPoint extends SelectivityPoint {
  naturalRank: number;
}

type PageSize = 50 | 100 | 500 | "all";
const PAGE_SIZE_OPTIONS: PageSize[] = [50, 100, 500, "all"];
const DEFAULT_PAGE_SIZE: PageSize = 100;

function cmp(a: unknown, b: unknown): number {
  if (a === b) return 0;
  if (a === null || a === undefined) return 1;
  if (b === null || b === undefined) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b));
}

function SortIndicator({ priority, dir }: { priority: number | null; dir: SortDir | null }) {
  if (priority === null || dir === null) return <span className="text-charcoal-40">↕</span>;
  return (
    <span className="text-charcoal inline-flex items-baseline gap-0.5">
      {dir === "asc" ? "↑" : "↓"}
      {priority > 0 && <sup className="text-[9px] text-muted">{priority + 1}</sup>}
    </span>
  );
}

export function CancerSelectiveTable({ rows, project, title, onFilteredRowsChange }: Props) {
  const [columnFilters, setColumnFilters] = useState<Record<string, string>>({});
  const [sorts, setSorts] = useState<Sort[]>([
    { col: "naturalRank", dir: "asc" },
  ]);
  const [pageSize, setPageSize] = useState<PageSize>(DEFAULT_PAGE_SIZE);
  const [pageIndex, setPageIndex] = useState(0);

  function setColumnFilter(col: string, value: string) {
    setColumnFilters((prev) => ({ ...prev, [col]: value }));
  }

  function displayValueFor(row: RankedPoint, col: string): string {
    if (col === "selectivity_ratio") return `${row.selectivity_ratio.toFixed(1)}×`;
    if (col === "ov8_activity") return row.ov8_activity.toFixed(2);
    if (col === "iose_activity")
      return row.iose_activity != null ? row.iose_activity.toFixed(2) : "";
    const v = row[col as keyof RankedPoint];
    return v == null ? "" : String(v);
  }

  const { data: pwmData } = useQuery({
    queryKey: ["pwms"],
    queryFn: api.pwms,
    staleTime: Infinity,
  });
  const pwms = pwmData?.pwms ?? {};

  // Project labels: "OV8/IOSE" -> ["OV8", "IOSE"]; "Stim/Rest" -> ["Stim", "Rest"]
  const [expLabel, ctrlLabel] = useMemo(() => {
    const parts = title.split("/");
    return [parts[0] ?? "OV8", parts[1] ?? "IOSE"];
  }, [title]);

  const heading =
    project === "T_cell_activation"
      ? "Activation-inducible enhancers"
      : "Cancer-selective enhancers";

  const COLUMNS: ColumnDef[] = useMemo(() => [
    { id: "naturalRank", header: "Rank", sortable: true, filterable: true, align: "right", width: "52px" },
    { id: "tf", header: "TF", sortable: true, filterable: true },
    { id: "promoter_name", header: "Enhancer", sortable: true, filterable: true },
    { id: "by_ppm_name", header: "PPM", sortable: true, filterable: true, align: "left" },
    { id: "logo", header: "Sequence Logo", sortable: false, width: "120px" },
    { id: "rank", header: "PPM Rank", sortable: true, filterable: true, align: "right" },
    { id: "ov8_activity", header: `${expLabel} Activity`, sortable: true, align: "right" },
    { id: "iose_activity", header: `${ctrlLabel} Activity`, sortable: true, align: "right" },
    { id: "selectivity_ratio", header: `${expLabel}/${ctrlLabel}`, sortable: true, align: "right" },
  ], [expLabel, ctrlLabel]);

  // Assign a stable natural rank: 1 = highest selectivity_ratio in the dataset.
  // The Rank column displays this value, so toggling Asc/Desc visibly reorders
  // the table even though pagination shows the same row positions.
  const ranked: RankedPoint[] = useMemo(() => {
    const sortedDesc = [...rows].sort((a, b) => b.selectivity_ratio - a.selectivity_ratio);
    return sortedDesc.map((r, i) => ({ ...r, naturalRank: i + 1 }));
  }, [rows]);

  const filtered = useMemo(() => {
    const active = Object.entries(columnFilters)
      .map(([col, q]) => [col, q.trim().toLowerCase()] as const)
      .filter(([, q]) => q !== "");
    if (active.length === 0) return ranked;
    return ranked.filter((r) =>
      active.every(([col, q]) => displayValueFor(r, col).toLowerCase().includes(q)),
    );
  }, [ranked, columnFilters]);

  const sorted = useMemo(() => {
    if (sorts.length === 0) return filtered;
    return [...filtered].sort((a, b) => {
      for (const { col, dir } of sorts) {
        const c = cmp(a[col as keyof RankedPoint], b[col as keyof RankedPoint]);
        if (c !== 0) return dir === "asc" ? c : -c;
      }
      return 0;
    });
  }, [filtered, sorts]);

  // Reset to first page whenever filters/sorts/page-size change.
  useEffect(() => {
    setPageIndex(0);
  }, [columnFilters, sorts, pageSize, rows]);

  // Mirror the table's filtered set up to the parent so the strip plot can
  // hide non-matching red dots in real time. Only `filtered` is propagated
  // (not `sorted`), since chart visibility depends on filters, not sort order.
  useEffect(() => {
    onFilteredRowsChange?.(filtered);
  }, [filtered, onFilteredRowsChange]);

  const totalRows = sorted.length;
  const effectivePageSize = pageSize === "all" ? totalRows || 1 : pageSize;
  const totalPages = pageSize === "all" ? 1 : Math.max(1, Math.ceil(totalRows / effectivePageSize));
  const pageStart = pageSize === "all" ? 0 : pageIndex * effectivePageSize;
  const pageEnd = pageSize === "all" ? totalRows : Math.min(totalRows, pageStart + effectivePageSize);
  const visible = sorted.slice(pageStart, pageEnd);

  function handleHeaderClick(col: SortCol, ev: React.MouseEvent) {
    // Default direction on first click: ascending for Rank (1,2,3 first feels natural),
    // descending for everything else (largest values first).
    const initialDir: SortDir = col === "naturalRank" ? "asc" : "desc";
    if (ev.shiftKey) {
      setSorts((prev) => {
        const idx = prev.findIndex((s) => s.col === col);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = { col, dir: next[idx].dir === "asc" ? "desc" : "asc" };
          return next;
        }
        return [...prev, { col, dir: initialDir }];
      });
    } else {
      setSorts((prev) => {
        if (prev[0]?.col === col) {
          return [{ col, dir: prev[0].dir === "asc" ? "desc" : "asc" }];
        }
        return [{ col, dir: initialDir }];
      });
    }
  }

  function sortInfo(col: SortCol): { priority: number | null; dir: SortDir | null } {
    const idx = sorts.findIndex((s) => s.col === col);
    if (idx === -1) return { priority: null, dir: null };
    return { priority: idx, dir: sorts[idx].dir };
  }

  return (
    <div className="card border-cream-border">
      <div className="flex flex-wrap items-end gap-4">
        <div className="mr-auto">
          <h4 className="text-card-title font-semibold text-charcoal">{heading}</h4>
          <p className="mt-1 text-xs text-muted">
            {totalRows.toLocaleString()} of {rows.length.toLocaleString()} matches · click a header
            to sort, shift+click to add a secondary sort · type in any column header to filter
          </p>
        </div>
      </div>

      <div className="mt-4">
        <table className="w-full text-left border-collapse table-fixed">
          <thead className="border-b border-cream-border text-xs tracking-wide text-muted bg-cream">
            <tr>
              {COLUMNS.map((c) => {
                const info = c.sortable ? sortInfo(c.id as SortCol) : { priority: null, dir: null };
                return (
                  <th
                    key={c.id}
                    style={c.width ? { width: c.width } : undefined}
                    className="py-2.5 px-2 font-medium select-none align-middle text-center"
                  >
                    {c.sortable ? (
                      <button
                        type="button"
                        onClick={(ev) => handleHeaderClick(c.id as SortCol, ev)}
                        className={cn(
                          "inline-flex items-center gap-1 transition-colors",
                          info.priority !== null
                            ? "text-charcoal"
                            : "text-muted hover:text-charcoal-82",
                        )}
                      >
                        <span>{c.header}</span>
                        <SortIndicator priority={info.priority} dir={info.dir} />
                      </button>
                    ) : (
                      <span>{c.header}</span>
                    )}
                  </th>
                );
              })}
            </tr>
            <tr>
              {COLUMNS.map((c) => {
                if (c.filterable !== true) {
                  return <th key={`${c.id}-filter`} className="pb-2.5 px-2" />;
                }
                const filterValue = columnFilters[c.id] ?? "";
                return (
                  <th key={`${c.id}-filter`} className="pb-2.5 px-2 font-normal text-center">
                    <div className="relative w-full">
                      <input
                        type="text"
                        value={filterValue}
                        onChange={(e) => setColumnFilter(c.id, e.target.value)}
                        placeholder="Search…"
                        aria-label={`Search ${c.header}`}
                        className="w-full bg-cream border border-transparent rounded-standard px-2 py-1 text-[11px] font-normal normal-case tracking-normal text-charcoal placeholder:text-charcoal-40 focus:outline-none focus:bg-cream-light focus:border-charcoal-40 text-center"
                      />
                      {filterValue && (
                        <button
                          type="button"
                          onClick={() => setColumnFilter(c.id, "")}
                          className="absolute right-1 top-1/2 -translate-y-1/2 text-muted hover:text-charcoal text-[11px]"
                          aria-label={`Clear ${c.header} filter`}
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visible.map((row, i) => {
              const ppm = pwms[row.by_ppm_name];
              return (
                <tr
                  key={`${row.promoter_name}_${i}`}
                  className="border-b border-cream-border transition-colors hover:bg-charcoal-3"
                >
                  <td className="py-2 px-2 align-middle text-right tabular-nums text-xs text-charcoal">
                    {row.naturalRank}
                  </td>
                  <td className="py-2 px-2 align-middle">
                    <code className="font-mono text-xs break-all">{row.tf || "—"}</code>
                  </td>
                  <td className="py-2 px-2 align-middle text-left">
                    <Link
                      to={`/library/${encodeURIComponent(row.promoter_name)}?project=${encodeURIComponent(project)}`}
                      className="font-mono text-xs text-charcoal underline decoration-charcoal-40 underline-offset-2 hover:decoration-charcoal break-all"
                    >
                      {row.promoter_name}
                    </Link>
                  </td>
                  <td className="py-2 px-2 align-middle text-left">
                    {row.by_ppm_name ? (
                      <Link
                        to={`/results/pwm/${encodeURIComponent(row.by_ppm_name)}?project=${encodeURIComponent(project)}${row.rank != null ? `&rank=${row.rank}` : ""}`}
                        className="font-mono text-xs text-charcoal-82 underline decoration-charcoal-40 underline-offset-2 hover:decoration-charcoal hover:text-charcoal break-all"
                        title="Open PPM activity distribution"
                      >
                        {row.by_ppm_name}
                      </Link>
                    ) : (
                      <span className="text-xs text-muted">—</span>
                    )}
                  </td>
                  <td className="py-2 px-2 align-middle">
                    {ppm ? (
                      <SequenceLogo ppm={ppm} width={110} height={32} />
                    ) : (
                      <span className="text-xs text-muted">—</span>
                    )}
                  </td>
                  <td className="py-2 px-2 align-middle text-right tabular-nums text-xs">
                    {row.rank ?? "—"}
                  </td>
                  <td className="py-2 px-2 align-middle text-right tabular-nums text-xs">
                    {row.ov8_activity.toFixed(2)}
                  </td>
                  <td className="py-2 px-2 align-middle text-right tabular-nums text-xs">
                    {row.iose_activity != null ? row.iose_activity.toFixed(2) : "—"}
                  </td>
                  <td className="py-2 px-2 align-middle text-right tabular-nums text-xs font-semibold">
                    {row.selectivity_ratio.toFixed(1)}×
                  </td>
                </tr>
              );
            })}
            {visible.length === 0 && (
              <tr>
                <td colSpan={COLUMNS.length} className="py-8 text-center text-muted text-sm">
                  No enhancers match this filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
        <div className="flex items-center gap-2">
          <label htmlFor="rows-per-page" className="text-muted text-xs">
            Rows per page
          </label>
          <select
            id="rows-per-page"
            value={String(pageSize)}
            onChange={(e) => {
              const v = e.target.value;
              setPageSize(v === "all" ? "all" : (Number(v) as PageSize));
            }}
            className="bg-cream border border-cream-border rounded-standard px-2 py-1 text-xs focus:outline-none focus:border-charcoal-40"
          >
            {PAGE_SIZE_OPTIONS.map((opt) => (
              <option key={String(opt)} value={String(opt)}>
                {opt === "all" ? "All" : opt}
              </option>
            ))}
          </select>
        </div>

        {pageSize !== "all" && totalRows > 0 && (
          <div className="flex items-center gap-3">
            <span className="text-muted tabular-nums text-xs">
              {(pageStart + 1).toLocaleString()}–{pageEnd.toLocaleString()} of{" "}
              {totalRows.toLocaleString()}
            </span>
            <button
              type="button"
              className="btn-ghost text-sm"
              disabled={pageIndex === 0}
              onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
            >
              ← Prev
            </button>
            <span className="text-muted tabular-nums text-xs">
              Page {pageIndex + 1} / {totalPages.toLocaleString()}
            </span>
            <button
              type="button"
              className="btn-ghost text-sm"
              disabled={pageIndex + 1 >= totalPages}
              onClick={() => setPageIndex((p) => p + 1)}
            >
              Next →
            </button>
          </div>
        )}
        {pageSize === "all" && totalRows > 0 && (
          <span className="text-muted tabular-nums text-xs">
            Showing all {totalRows.toLocaleString()} rows
          </span>
        )}
      </div>
    </div>
  );
}
