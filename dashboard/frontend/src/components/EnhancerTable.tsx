import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as Tooltip from "@radix-ui/react-tooltip";

import { api, type EnhancerRow, type EnhancerSortColumn } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useLibraryFilter } from "@/components/LibraryFilters";

const PAGE_SIZE_OPTIONS = [50, 100, 500, 1000] as const;
const DEFAULT_PAGE_SIZE = 100;
type PageSize = typeof PAGE_SIZE_OPTIONS[number];
const SEARCH_DEBOUNCE_MS = 300;
const VARIABLE_REGION_PREVIEW = 24;

type SortDir = "asc" | "desc";

interface ColumnDef {
  id: EnhancerSortColumn | "DBD_family";
  header: string;
  align?: "left" | "right";
  width?: string;
}

const COLUMNS: ColumnDef[] = [
  { id: "TF", header: "TF" },
  { id: "DBD_family", header: "DBD Family" },
  { id: "TFBS_sequence", header: "TFBS" },
  { id: "variable_region", header: "Variable Region" },
  { id: "by_ppm_name", header: "PPM Name" },
  { id: "rank", header: "Rank", align: "right" },
  { id: "n_barcodes", header: "# Barcodes", align: "right" },
];

// Sortable subset — matches the backend ENHANCER_SORT_COLUMNS whitelist.
const SORTABLE_COLUMN_IDS = new Set<string>([
  "TF",
  "TFBS_sequence",
  "variable_region",
  "by_ppm_name",
  "rank",
  "n_barcodes",
]);

// Per-column filter keys → backend query param. Columns absent from this map
// (rank, n_barcodes) get no filter input.
const COLUMN_FILTER_KEYS: Record<string, "tf_contains" | "dbd_contains" | "tfbs_contains" | "vr_contains" | "ppm_contains"> = {
  TF: "tf_contains",
  DBD_family: "dbd_contains",
  TFBS_sequence: "tfbs_contains",
  variable_region: "vr_contains",
  by_ppm_name: "ppm_contains",
};

function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

function VariableRegionCell({ sequence }: { sequence: string }) {
  if (!sequence) return <span className="text-muted">—</span>;
  const truncated = sequence.length > VARIABLE_REGION_PREVIEW
    ? sequence.slice(0, VARIABLE_REGION_PREVIEW) + "…"
    : sequence;

  return (
    <Tooltip.Provider delayDuration={150}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <span className="inline-flex items-baseline gap-2 cursor-help">
            <code className="font-mono text-xs text-charcoal-82">{truncated}</code>
            <span className="text-[10px] text-muted tabular-nums">{sequence.length} bp</span>
          </span>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            sideOffset={6}
            className="max-w-md break-all rounded-comfortable border border-cream-border bg-cream-light px-3 py-2 text-xs text-charcoal-82 shadow-focus z-50"
          >
            <div className="text-[10px] uppercase tracking-wide text-muted mb-1">
              Variable region · {sequence.length} bp
            </div>
            <code className="font-mono">{sequence}</code>
            <Tooltip.Arrow className="fill-cream-border" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}

function SortIndicator({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="text-charcoal-40">↕</span>;
  return <span className="text-charcoal">{dir === "asc" ? "↑" : "↓"}</span>;
}

export function EnhancerTable() {
  const [searchInput, setSearchInput] = useState("");
  const debouncedSearch = useDebounced(searchInput, SEARCH_DEBOUNCE_MS);
  const [colFilters, setColFilters] = useState<Record<string, string>>({});
  const debouncedColFilters = useDebounced(colFilters, SEARCH_DEBOUNCE_MS);
  const [sortBy, setSortBy] = useState<EnhancerSortColumn>("TF");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState<PageSize>(DEFAULT_PAGE_SIZE);
  const { filter } = useLibraryFilter();

  const colFiltersKey = JSON.stringify(debouncedColFilters);
  // Reset to first page whenever the search, sort, panel filter, OR page size changes.
  useEffect(() => {
    setPage(0);
  }, [debouncedSearch, colFiltersKey, sortBy, sortDir, filter.kind, filter.value, pageSize]);

  const offset = page * pageSize;
  const { data, isPending, error, isFetching } = useQuery({
    queryKey: ["enhancers", debouncedSearch, colFiltersKey, sortBy, sortDir, offset, pageSize, filter.kind, filter.value],
    queryFn: () =>
      api.listEnhancers({
        q: debouncedSearch || undefined,
        tf_contains: debouncedColFilters["TF"] || undefined,
        dbd_contains: debouncedColFilters["DBD_family"] || undefined,
        tfbs_contains: debouncedColFilters["TFBS_sequence"] || undefined,
        vr_contains: debouncedColFilters["variable_region"] || undefined,
        ppm_contains: debouncedColFilters["by_ppm_name"] || undefined,
        dbd_family: filter.kind === "dbd_family" && filter.value ? filter.value : undefined,
        cacts_tumor: filter.kind === "cacts_tumor" && filter.value ? filter.value : undefined,
        dalessio_system: filter.kind === "dalessio_system" && filter.value ? filter.value : undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
        limit: pageSize,
        offset,
      }),
    placeholderData: (prev) => prev,
  });

  function handleSort(colId: ColumnDef["id"]) {
    if (!SORTABLE_COLUMN_IDS.has(colId)) return;
    const col = colId as EnhancerSortColumn;
    if (col === sortBy) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(col);
      setSortDir(col === "n_barcodes" || col === "rank" || col === "variable_region" ? "desc" : "asc");
    }
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 0;

  return (
    <div className="card">
      <div className="flex flex-wrap items-end gap-4 mb-6">
        <div className="mr-auto">
          <h3 className="text-card-title font-semibold">Enhancer table</h3>
          <p className="text-xs text-muted mt-1">
            One row per designed enhancer. Click any column header to sort. Search
            matches transcription factor, TFBS sequence, PPM name, or variable region.
          </p>
        </div>
        <div className="flex flex-col">
          <label htmlFor="enh-search" className="text-muted text-xs mb-1">
            Search
          </label>
          <div className="relative">
            <input
              id="enh-search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="e.g. SOX2, AAGCT, jaspar"
              className="w-72 bg-cream border border-cream-border rounded-standard pl-3 pr-9 py-1.5 text-sm focus:outline-none focus:border-charcoal-40"
            />
            {searchInput && (
              <button
                type="button"
                onClick={() => setSearchInput("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-charcoal text-sm"
                aria-label="Clear search"
              >
                ✕
              </button>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="text-sm text-charcoal-82 border border-charcoal-40 rounded-comfortable p-4">
          {String(error)}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead className="border-b border-cream-border text-xs tracking-wide text-muted">
            <tr>
              {COLUMNS.map((c) => {
                const sortable = SORTABLE_COLUMN_IDS.has(c.id);
                const isActive = sortable && c.id === sortBy;
                return (
                  <th
                    key={c.id}
                    className="py-3 pr-4 font-medium select-none align-middle text-center"
                  >
                    {sortable ? (
                      <button
                        type="button"
                        onClick={() => handleSort(c.id)}
                        className={cn(
                          "inline-flex items-center gap-1.5 transition-colors",
                          isActive ? "text-charcoal" : "text-muted hover:text-charcoal-82",
                        )}
                      >
                        <span>{c.header}</span>
                        <SortIndicator active={isActive} dir={sortDir} />
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
                const filterKey = COLUMN_FILTER_KEYS[c.id];
                if (!filterKey) {
                  return <th key={`${c.id}-filter`} className="pb-2 pr-4 align-middle" />;
                }
                return (
                  <th key={`${c.id}-filter`} className="pb-2 pr-4 font-normal align-middle text-center">
                    <input
                      type="text"
                      value={colFilters[c.id] ?? ""}
                      onChange={(e) =>
                        setColFilters((prev) => ({ ...prev, [c.id]: e.target.value }))
                      }
                      placeholder="Search…"
                      aria-label={`Search ${c.header}`}
                      className="w-full bg-cream border border-cream-border rounded-standard px-2 py-1 text-xs text-charcoal-82 placeholder:text-charcoal-40 focus:outline-none focus:border-charcoal-40 text-center"
                    />
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {isPending && (
              <tr>
                <td colSpan={COLUMNS.length} className="py-6 text-center text-muted">
                  Loading…
                </td>
              </tr>
            )}
            {!isPending &&
              (data?.rows ?? []).map((row: EnhancerRow, i) => {
                return (
                  <tr
                    key={`${row.TF}_${row.TFBS_sequence}_${row.by_ppm_name}_${row.rank}_${i}`}
                    className="border-b border-cream-border transition-colors hover:bg-charcoal-3"
                  >
                    <td className="py-2.5 pr-4 align-top">
                      <code className="font-mono text-xs">{row.TF}</code>
                    </td>
                    <td className="py-2.5 pr-4 align-top">
                      {row.Lambert_DBD_family ? (
                        <span className="text-xs text-charcoal-82">{row.Lambert_DBD_family}</span>
                      ) : (
                        <span className="text-xs text-muted">—</span>
                      )}
                    </td>
                    <td className="py-2.5 pr-4 align-top">
                      <code className="font-mono text-xs">{row.TFBS_sequence}</code>
                    </td>
                    <td className="py-2.5 pr-4 align-top">
                      <VariableRegionCell sequence={row.variable_region} />
                    </td>
                    <td className="py-2.5 pr-4 align-top">
                      <span className="text-xs">{row.by_ppm_name}</span>
                    </td>
                    <td className="py-2.5 pr-4 align-top text-right">
                      <span className="text-xs tabular-nums">{row.rank}</span>
                    </td>
                    <td className="py-2.5 pr-4 align-top text-right">
                      <span className="text-xs tabular-nums font-semibold">
                        {row.n_barcodes.toLocaleString()}
                      </span>
                    </td>
                  </tr>
                );
              })}
            {!isPending && (data?.rows.length ?? 0) === 0 && (
              <tr>
                <td colSpan={COLUMNS.length} className="py-6 text-center text-muted">
                  No enhancers match this search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {data && (
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 text-sm">
          <span className="text-muted tabular-nums">
            {data.total > 0 ? (
              <>
                Showing {offset + 1}–{Math.min(offset + pageSize, data.total)} of{" "}
                {data.total.toLocaleString()} enhancers
                {isFetching && <span className="ml-2 text-charcoal-40">updating…</span>}
              </>
            ) : (
              "0 enhancers"
            )}
          </span>
          <div className="flex flex-wrap items-center gap-3">
            <label className="inline-flex items-center gap-2 text-xs text-muted">
              Rows per page
              <select
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value) as PageSize)}
                className="bg-cream border border-cream-border rounded-standard px-2 py-1 text-xs text-charcoal focus:outline-none focus:border-charcoal-40"
              >
                {PAGE_SIZE_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="btn-ghost text-sm"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              ← Prev
            </button>
            <span className="self-center tabular-nums text-muted">
              Page {page + 1} / {totalPages.toLocaleString()}
            </span>
            <button
              type="button"
              className="btn-ghost text-sm"
              disabled={page + 1 >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
