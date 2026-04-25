import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { SummaryCard } from "@/components/SummaryCard";
import { EnhancerTable } from "@/components/EnhancerTable";
import { HorizontalFamilyBar } from "@/components/HorizontalFamilyBar";
import { StackedCoverageBar } from "@/components/StackedCoverageBar";
import {
  ActiveFilterPill,
  LibraryFilterProvider,
} from "@/components/LibraryFilters";

function fmt(n: number): string {
  return n.toLocaleString("en-US");
}

function LibraryContent() {
  const { data, isPending, error } = useQuery({
    queryKey: ["library", "summary"],
    queryFn: api.librarySummary,
  });

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-16">
      <div className="flex flex-wrap items-baseline gap-4">
        <h1 className="text-display-section font-semibold tracking-tight">
          Library composition
        </h1>
        <ActiveFilterPill />
      </div>
      <p className="mt-4 max-w-2xl text-muted">
        Coverage of the designed enhancer library by transcription factor,
        promoter, and barcoded construct.
      </p>

      {isPending && <p className="mt-12 text-muted">Loading library summary…</p>}

      {error && (
        <div className="mt-12 card border-charcoal-40">
          <h2 className="text-card-title font-semibold">Library data not loaded</h2>
          <p className="mt-2 text-sm text-muted">
            The library metadata has not been imported yet. Run{" "}
            <code className="font-mono">trend ingest</code> (or{" "}
            <code className="font-mono">make ingest</code> from the{" "}
            <code className="font-mono">dashboard/</code> directory) and refresh.
          </p>
          <pre className="mt-4 text-xs text-charcoal-82 overflow-auto">
            {String(error)}
          </pre>
        </div>
      )}

      {data && (
        <>
          <section className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <SummaryCard label="Total constructs" value={fmt(data.total_constructs)} />
            <SummaryCard label="Unique promoters" value={fmt(data.total_promoters)} />
            <SummaryCard
              label="Median barcodes / promoter"
              value={data.median_barcodes_per_promoter.toFixed(1)}
            />
            <SummaryCard label="DNA-binding proteins" value={fmt(data.total_tfs_curated)} />
            <SummaryCard label="Variable regions" value={fmt(data.total_variable_regions)} />
          </section>

          {/* Panel B */}
          <section className="mt-16 card">
            <h3 className="text-card-title font-semibold">DNA-binding domain family composition</h3>
            <p className="text-sm text-muted mt-1">
              {data.classifications?.totals?.n_classified_tfs ?? 729} TFs classified across{" "}
              {data.classifications?.totals?.n_dbd_families_total ?? 49} DBD families
              (Lambert et al. 2018 taxonomy). Click any bar to filter the enhancer table below.
            </p>
            <div className="mt-6">
              <HorizontalFamilyBar variant="tfs" />
            </div>
          </section>

          {/* Panel C */}
          <section className="mt-16 card">
            <h3 className="text-card-title font-semibold">Sensor representation by TF family</h3>
            <p className="text-sm text-muted mt-1">
              Total enhancer-reporter constructs (sensors) per DBD family. Each TF is
              represented by multiple sensors designed from distinct PPMs or PWMs. Same
              colors as the chart above.
            </p>
            <div className="mt-6">
              <HorizontalFamilyBar variant="sensors" />
            </div>
          </section>

          {/* Panel D */}
          <section className="mt-16 card">
            <h3 className="text-card-title font-semibold">
              Coverage of cancer master transcription factors
            </h3>
            <p className="text-sm text-muted mt-1">
              {data.classifications?.totals?.cacts?.n_in ?? 0}/
              {data.classifications?.totals?.cacts?.n_total ?? 0} (
              {data.classifications?.totals?.cacts?.pct ?? 0}%) candidate MTFs from the
              CaCTS algorithm (Reddy et al. 2021) across 34 TCGA tumor types.
            </p>
            <div className="mt-6">
              <StackedCoverageBar variant="cacts" />
            </div>
          </section>

          {/* Panel E */}
          <section className="mt-16 card">
            <h3 className="text-card-title font-semibold">
              Coverage of cell identity transcription factors
            </h3>
            <p className="text-sm text-muted mt-1">
              {data.classifications?.totals?.dalessio?.n_in ?? 0}/
              {data.classifications?.totals?.dalessio?.n_total ?? 0} (
              {data.classifications?.totals?.dalessio?.pct ?? 0}%) core identity TFs
              (D'Alessio et al. 2015) — top 10 specificity-ranked per tissue, grouped
              into 15 anatomical systems.
            </p>
            <div className="mt-6">
              <StackedCoverageBar variant="dalessio" />
            </div>
          </section>

          <section className="mt-16">
            <EnhancerTable />
          </section>
        </>
      )}
    </div>
  );
}

export default function Library() {
  return (
    <LibraryFilterProvider>
      <LibraryContent />
    </LibraryFilterProvider>
  );
}
