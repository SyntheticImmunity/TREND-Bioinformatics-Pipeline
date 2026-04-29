import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, type SelectivityPoint } from "@/lib/api";
import { SequenceLogo } from "@/components/SequenceLogo";
import { PpmRankChart, type RankMetric } from "@/components/PpmRankChart";
import { cn } from "@/lib/cn";

type SortCol =
  | "rank"
  | "tfbs_sequence"
  | "ov8_activity"
  | "iose_activity"
  | "selectivity_ratio";
type SortDir = "asc" | "desc";

function SortableTh({
  col,
  label,
  align,
  width,
  sort,
  onClick,
}: {
  col: SortCol;
  label: string;
  align?: "right";
  width?: string;
  sort: { col: SortCol; dir: SortDir };
  onClick: (col: SortCol) => void;
}) {
  const active = sort.col === col;
  const indicator = !active ? (
    <span className="text-charcoal-40">↕</span>
  ) : sort.dir === "asc" ? (
    <span className="text-charcoal">↑</span>
  ) : (
    <span className="text-charcoal">↓</span>
  );
  return (
    <th
      className={cn(
        "py-2.5 px-3 font-medium select-none",
        align === "right" && "text-right",
      )}
      style={width ? { width } : undefined}
    >
      <button
        type="button"
        onClick={() => onClick(col)}
        className={cn(
          "inline-flex items-center gap-1.5 transition-colors",
          active ? "text-charcoal" : "text-muted hover:text-charcoal-82",
        )}
      >
        <span>{label}</span>
        {indicator}
      </button>
    </th>
  );
}

export default function PwmDetail() {
  const { pwmName: encoded = "" } = useParams();
  const [searchParams] = useSearchParams();
  const project = searchParams.get("project") ?? "ovarian_cancer";
  const pwmName = decodeURIComponent(encoded);
  const rankParam = searchParams.get("rank");
  const urlRank = rankParam !== null && /^\d+$/.test(rankParam) ? Number(rankParam) : null;

  const [metric, setMetric] = useState<RankMetric>("selectivity_ratio");
  const [sort, setSort] = useState<{ col: SortCol; dir: SortDir }>({
    col: "rank",
    dir: "asc",
  });

  function handleSortClick(col: SortCol) {
    setSort((prev) => {
      if (prev.col === col) {
        return { col, dir: prev.dir === "asc" ? "desc" : "asc" };
      }
      // First click on a new column: rank goes asc (natural), others go desc.
      return { col, dir: col === "rank" ? "asc" : "desc" };
    });
  }

  const { data: scatter, isPending: scatterPending, error: scatterError } = useQuery({
    queryKey: ["selectivity-scatter", project],
    queryFn: () => api.selectivityScatter(project),
  });

  const { data: pwmData, isPending: pwmsPending } = useQuery({
    queryKey: ["pwms"],
    queryFn: api.pwms,
    staleTime: Infinity,
  });

  const ppm = pwmData?.pwms?.[pwmName];

  // All rows for this specific PPM (PPM names normalized server-side, so the
  // 10 `_v1`..`_v10` design variants collapse into one `by_ppm_name`).
  // Always passed to the rank chart in design-rank ascending order regardless
  // of the user's chosen table sort.
  const pwmRows = useMemo(() => {
    if (!scatter) return [] as SelectivityPoint[];
    return scatter.rows
      .filter((r) => r.by_ppm_name === pwmName)
      .slice()
      .sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999));
  }, [scatter, pwmName]);

  const tf = pwmRows[0]?.tf ?? null;

  // Table-only ordering — independent of the chart's fixed rank-1..10 layout.
  const sortedRows = useMemo(() => {
    if (pwmRows.length === 0) return pwmRows;
    const dirMul = sort.dir === "asc" ? 1 : -1;
    const accessor = (r: SelectivityPoint): number | string | null => {
      switch (sort.col) {
        case "rank":
          return r.rank;
        case "tfbs_sequence":
          return r.tfbs_sequence;
        case "ov8_activity":
          return r.ov8_activity;
        case "iose_activity":
          return r.iose_activity;
        case "selectivity_ratio":
          return r.selectivity_ratio;
      }
    };
    const cmp = (a: SelectivityPoint, b: SelectivityPoint): number => {
      const va = accessor(a);
      const vb = accessor(b);
      // null/undefined sort to the bottom regardless of direction.
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "number" && typeof vb === "number") {
        return (va - vb) * dirMul;
      }
      return String(va).localeCompare(String(vb)) * dirMul;
    };
    return pwmRows.slice().sort(cmp);
  }, [pwmRows, sort]);

  return (
    <div className="mx-auto max-w-[1100px] px-6 py-12">
      <div className="text-sm">
        <Link
          to={`/results?project=${encodeURIComponent(project)}`}
          className="text-charcoal-82 underline decoration-charcoal-40 underline-offset-2 hover:decoration-charcoal hover:text-charcoal"
        >
          ← Back to results
        </Link>
      </div>

      <div className="mt-6 flex flex-wrap items-baseline gap-3">
        <h1 className="text-display-section font-semibold tracking-tight font-mono break-all">
          {pwmName}
        </h1>
        <span className="text-sm text-muted">
          PPM details · {project}
          {tf && (
            <>
              {" "}· TF: <span className="font-mono">{tf}</span>
            </>
          )}
        </span>
      </div>

      <section className="mt-10 card">
        <h2 className="text-card-title font-semibold">Sequence Logo</h2>
        <p className="mt-1 text-sm text-muted">
          Position probability matrix from the ENCODE/MotifDb collection. Letter
          heights show information content in bits (max 2 per position).
        </p>
        <div className="mt-6">
          {pwmsPending ? (
            <p className="text-muted text-sm">Loading PPM…</p>
          ) : ppm ? (
            <SequenceLogo ppm={ppm} width={Math.min(640, ppm[0].length * 48)} height={120} showAxis />
          ) : (
            <p className="text-sm text-charcoal-82">
              No PPM found for <code className="font-mono">{pwmName}</code> in the reference set.
            </p>
          )}
        </div>
      </section>

      <section className="mt-8 card">
        {scatterPending && <p className="text-muted text-sm">Loading activity data…</p>}
        {scatterError && (
          <p className="text-sm text-charcoal-82">{String(scatterError)}</p>
        )}
        {scatter && pwmRows.length === 0 && (
          <div>
            <h2 className="text-card-title font-semibold">Activity per TFBS variant rank</h2>
            <p className="mt-2 text-sm text-charcoal-82">
              No enhancers in <code className="font-mono">{project}</code> use
              this PPM, so the variant-rank chart has no data to show.
            </p>
          </div>
        )}
        {scatter && pwmRows.length > 0 && (
          <PpmRankChart
            pwmRows={pwmRows}
            metric={metric}
            onMetricChange={setMetric}
            pwmName={pwmName}
            project={project}
            currentRank={urlRank}
          />
        )}
      </section>

      <section className="mt-8 card">
        <h2 className="text-card-title font-semibold">
          TFBS variants in this PPM
        </h2>
        <p className="mt-1 text-sm text-muted">
          Each row is one designed TFBS sequence variant for this PPM, in
          library design order. Click an enhancer to view its construct details
          and per-condition activity.
        </p>

        {scatter && pwmRows.length === 0 && (
          <p className="mt-4 text-sm text-charcoal-82">
            No enhancers in <code className="font-mono">{project}</code> use
            this PPM.
          </p>
        )}

        {scatter && pwmRows.length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="border-b border-cream-border text-xs tracking-wide text-muted bg-cream-light">
                <tr>
                  <SortableTh
                    col="rank"
                    label="Rank"
                    align="right"
                    width="64px"
                    sort={sort}
                    onClick={handleSortClick}
                  />
                  <SortableTh
                    col="tfbs_sequence"
                    label="TFBS Sequence"
                    sort={sort}
                    onClick={handleSortClick}
                  />
                  <th className="py-2.5 px-3 font-medium">Enhancer</th>
                  <SortableTh
                    col="ov8_activity"
                    label="OV8 Activity"
                    align="right"
                    sort={sort}
                    onClick={handleSortClick}
                  />
                  <SortableTh
                    col="iose_activity"
                    label="IOSE Activity"
                    align="right"
                    sort={sort}
                    onClick={handleSortClick}
                  />
                  <SortableTh
                    col="selectivity_ratio"
                    label="OV8/IOSE"
                    align="right"
                    sort={sort}
                    onClick={handleSortClick}
                  />
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((r, i) => {
                  const highlighted = urlRank !== null && r.rank === urlRank;
                  return (
                    <tr
                      key={`${r.promoter_name}_${i}`}
                      className={cn(
                        "border-b border-cream-border transition-colors",
                        highlighted ? "bg-charcoal-3" : "hover:bg-charcoal-3",
                      )}
                    >
                      <td className="py-2 px-3 align-middle text-right tabular-nums text-xs text-muted">
                        {r.rank ?? "—"}
                      </td>
                      <td className="py-2 px-3 align-middle font-mono text-xs">
                        {r.tfbs_sequence ?? <span className="text-muted">—</span>}
                      </td>
                      <td className="py-2 px-3 align-middle">
                        <Link
                          to={`/library/${encodeURIComponent(r.promoter_name)}?project=${encodeURIComponent(project)}`}
                          className="font-mono text-xs text-charcoal underline decoration-charcoal-40 underline-offset-2 hover:decoration-charcoal"
                        >
                          {r.promoter_name}
                        </Link>
                      </td>
                      <td className="py-2 px-3 align-middle text-right tabular-nums text-xs">
                        {r.ov8_activity.toFixed(2)}
                      </td>
                      <td className="py-2 px-3 align-middle text-right tabular-nums text-xs">
                        {r.iose_activity != null ? r.iose_activity.toFixed(2) : "—"}
                      </td>
                      <td className="py-2 px-3 align-middle text-right tabular-nums text-xs font-semibold">
                        {r.selectivity_ratio.toFixed(1)}×
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
