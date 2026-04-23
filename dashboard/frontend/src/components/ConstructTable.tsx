import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { Link } from "react-router-dom";

import { api, type ConstructRow } from "@/lib/api";
import { cn } from "@/lib/cn";

const PAGE_SIZE = 100;

export function ConstructTable() {
  const [tf, setTf] = useState("");
  const [promoterPrefix, setPromoterPrefix] = useState("");
  const [appliedTf, setAppliedTf] = useState<string | undefined>(undefined);
  const [appliedPrefix, setAppliedPrefix] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(0);

  const offset = page * PAGE_SIZE;
  const { data, isPending, error } = useQuery({
    queryKey: ["constructs", appliedTf ?? "", appliedPrefix ?? "", offset],
    queryFn: () =>
      api.listConstructs({
        tf: appliedTf,
        promoter_prefix: appliedPrefix,
        limit: PAGE_SIZE,
        offset,
      }),
  });

  const columns = useMemo<ColumnDef<ConstructRow>[]>(
    () => [
      {
        id: "promoter_name_bc",
        header: "Construct ID",
        accessorKey: "promoter_name_bc",
        cell: ({ getValue }) => (
          <Link
            to={`/library/${encodeURIComponent(String(getValue()))}`}
            className="font-mono text-xs no-underline text-charcoal hover:underline"
          >
            {String(getValue())}
          </Link>
        ),
      },
      { header: "Promoter", accessorKey: "promoter_name", cell: (c) => <code className="font-mono text-xs">{String(c.getValue())}</code> },
      { header: "TF", accessorKey: "TF", cell: (c) => <code className="font-mono text-xs">{String(c.getValue())}</code> },
      { header: "TFBS", accessorKey: "TFBS", cell: (c) => <code className="font-mono text-xs">{String(c.getValue())}</code> },
      { header: "PPM Name", accessorKey: "by_ppm_name", cell: (c) => <span className="text-xs">{String(c.getValue())}</span> },
      { header: "Rank", accessorKey: "rank", cell: (c) => <span className="text-xs tabular-nums">{String(c.getValue())}</span> },
    ],
    [],
  );

  const table = useReactTable({
    data: data?.rows ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  function applyFilters(e: React.FormEvent) {
    e.preventDefault();
    setAppliedTf(tf.trim() || undefined);
    setAppliedPrefix(promoterPrefix.trim() || undefined);
    setPage(0);
  }

  function clearFilters() {
    setTf("");
    setPromoterPrefix("");
    setAppliedTf(undefined);
    setAppliedPrefix(undefined);
    setPage(0);
  }

  return (
    <div className="card">
      <div className="flex flex-wrap items-end gap-4 mb-6">
        <h3 className="text-card-title font-semibold mr-auto">Construct table</h3>
        <form className="flex flex-wrap items-end gap-3" onSubmit={applyFilters}>
          <label className="flex flex-col text-sm">
            <span className="text-muted text-xs mb-1">TF (exact)</span>
            <input
              value={tf}
              onChange={(e) => setTf(e.target.value)}
              placeholder="e.g. SOX2"
              className="bg-cream border border-cream-border rounded-standard px-3 py-1.5 text-sm focus:outline-none focus:border-charcoal-40"
            />
          </label>
          <label className="flex flex-col text-sm">
            <span className="text-muted text-xs mb-1">Promoter prefix</span>
            <input
              value={promoterPrefix}
              onChange={(e) => setPromoterPrefix(e.target.value)}
              placeholder="e.g. TTTGTA"
              className="bg-cream border border-cream-border rounded-standard px-3 py-1.5 text-sm focus:outline-none focus:border-charcoal-40"
            />
          </label>
          <button type="submit" className="btn-primary text-sm">Apply</button>
          <button type="button" onClick={clearFilters} className="btn-ghost text-sm">
            Clear
          </button>
        </form>
      </div>

      {error && (
        <div className="text-sm text-charcoal-82 border border-charcoal-40 rounded-comfortable p-4">
          {String(error)}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead className="border-b border-cream-border text-xs uppercase tracking-wide text-muted">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th key={h.id} className="py-3 pr-4 font-medium">
                    {flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {isPending && (
              <tr>
                <td colSpan={columns.length} className="py-6 text-center text-muted">
                  Loading…
                </td>
              </tr>
            )}
            {!isPending &&
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className={cn(
                    "border-b border-cream-border transition-colors",
                    "hover:bg-charcoal-3",
                  )}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="py-2.5 pr-4 align-top">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {data && (
        <div className="mt-6 flex items-center justify-between text-sm">
          <span className="text-muted tabular-nums">
            Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)} of{" "}
            {data.total.toLocaleString()}
          </span>
          <div className="flex gap-2">
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
