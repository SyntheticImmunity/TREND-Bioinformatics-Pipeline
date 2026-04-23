/**
 * Lightweight context for the four interactive panels (B/C/D/E) and the
 * enhancer table — all of them read this object to know what filter is
 * currently applied, and call setFilter() to change it.
 */
import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import { cn } from "@/lib/cn";

export type LibraryFilterKind = "dbd_family" | "cacts_tumor" | "dalessio_system" | null;

export interface LibraryFilter {
  kind: LibraryFilterKind;
  value: string | null;
  label?: string;
}

interface Ctx {
  filter: LibraryFilter;
  setFilter: (f: LibraryFilter) => void;
  clearFilter: () => void;
}

const LibraryFilterContext = createContext<Ctx | null>(null);

export function LibraryFilterProvider({ children }: { children: ReactNode }) {
  const [filter, setFilter] = useState<LibraryFilter>({ kind: null, value: null });
  const value = useMemo<Ctx>(
    () => ({
      filter,
      setFilter,
      clearFilter: () => setFilter({ kind: null, value: null }),
    }),
    [filter],
  );
  return (
    <LibraryFilterContext.Provider value={value}>{children}</LibraryFilterContext.Provider>
  );
}

export function useLibraryFilter(): Ctx {
  const ctx = useContext(LibraryFilterContext);
  if (!ctx) throw new Error("useLibraryFilter outside provider");
  return ctx;
}

const KIND_LABEL: Record<NonNullable<LibraryFilterKind>, string> = {
  dbd_family: "DBD family",
  cacts_tumor: "Cancer MTF (CaCTS)",
  dalessio_system: "Identity TF system",
};

export function ActiveFilterPill() {
  const { filter, clearFilter } = useLibraryFilter();
  if (!filter.kind || !filter.value) return null;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full bg-charcoal text-cream-light",
        "px-3 py-1 text-xs uppercase tracking-wide",
      )}
    >
      <span className="opacity-70">{KIND_LABEL[filter.kind]}:</span>
      <span className="font-mono normal-case">{filter.label ?? filter.value}</span>
      <button
        type="button"
        onClick={clearFilter}
        className="ml-1 opacity-70 hover:opacity-100"
        aria-label="Clear filter"
      >
        ✕
      </button>
    </span>
  );
}
