import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, type SelectionRow, type SelectionAxis } from "@/lib/api";
import { cn } from "@/lib/cn";

const PROJECTS = [
  { id: "ovarian_cancer", label: "Ovarian cancer" },
  { id: "T_cell_activation", label: "T-cell activation" },
];
const AXIS_KEYS = ["target", "specificity", "basal"] as const;
type AxisKey = (typeof AXIS_KEYS)[number];
const DEFAULT_WEIGHTS: Record<AxisKey, number> = { target: 50, specificity: 70, basal: 40 };

/** Percentile of each value within the column (0..1); inverted for low-is-better
 *  axes so a higher percentile always means "more desirable". Robust to the
 *  heavy-tailed activity/ratio distributions (vs. raw min-max). */
function percentiles(vals: number[], lowerBetter: boolean): number[] {
  const order = vals.map((v, i) => [v, i] as const).sort((a, b) => a[0] - b[0]);
  const pct = new Array<number>(vals.length);
  order.forEach(([, i], rank) => {
    pct[i] = vals.length > 1 ? rank / (vals.length - 1) : 1;
  });
  return lowerBetter ? pct.map((p) => 1 - p) : pct;
}

// Sequence redundancy via 3-mer Jaccard; used to diversify the shortlist the way
// one would when picking variants to clone (avoid near-identical sequences).
function kmers(seq: string, k = 3): Set<string> {
  const s = new Set<string>();
  for (let i = 0; i + k <= seq.length; i++) s.add(seq.slice(i, i + k));
  return s;
}
function jaccard(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 || b.size === 0) return a.size === b.size ? 1 : 0;
  let inter = 0;
  for (const x of a) if (b.has(x)) inter++;
  return inter / (a.size + b.size - inter);
}
const SIMILAR = 0.7; // Jaccard >= this counts as "too similar to clone both"

type Scored = SelectionRow & { score: number; members?: number };

export default function ResourceSelector() {
  const [project, setProject] = useState("ovarian_cancer");
  const [weights, setWeights] = useState<Record<AxisKey, number>>(DEFAULT_WEIGHTS);
  const [paretoOnly, setParetoOnly] = useState(false);
  const [diversify, setDiversify] = useState(false);

  const { data, isPending, error } = useQuery({
    queryKey: ["selection", project],
    queryFn: () => api.selection(project),
  });

  const axisByKey = useMemo(() => {
    const m: Record<string, SelectionAxis> = {};
    (data?.axes ?? []).forEach((a) => (m[a.key] = a));
    return m;
  }, [data]);

  // percentile per axis — recomputed only when the pool changes, not per slider
  const pct = useMemo(() => {
    const rows = data?.rows ?? [];
    const out: Record<AxisKey, number[]> = { target: [], specificity: [], basal: [] };
    for (const k of AXIS_KEYS) {
      const low = axisByKey[k]?.direction === "low";
      out[k] = percentiles(rows.map((r) => r[k]), low);
    }
    return out;
  }, [data, axisByKey]);

  const ranked = useMemo<Scored[]>(() => {
    const rows = data?.rows ?? [];
    const wsum = AXIS_KEYS.reduce((s, k) => s + weights[k], 0) || 1;
    const scored = rows.map((r, i) => ({
      ...r,
      score: AXIS_KEYS.reduce((s, k) => s + weights[k] * pct[k][i], 0) / wsum,
    }));
    scored.sort((a, b) => b.score - a.score);
    return scored;
  }, [data, pct, weights]);

  const shown = useMemo<Scored[]>(() => {
    let list = paretoOnly ? ranked.filter((r) => r.pareto) : ranked;
    if (diversify) {
      // greedy over the ranked list so each cluster's representative is its
      // best-scoring member under the current weights
      const reps: { km: Set<string>; row: Scored; members: number }[] = [];
      const pool = list.slice(0, 600);
      for (const row of pool) {
        const km = kmers(row.seq);
        const hit = reps.find((r) => jaccard(r.km, km) >= SIMILAR);
        if (hit) hit.members += 1;
        else reps.push({ km, row, members: 0 });
      }
      list = reps.map((r) => ({ ...r.row, members: r.members }));
    }
    return list.slice(0, 200);
  }, [ranked, paretoOnly, diversify]);

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-12">
      <h1 className="text-display-section font-semibold tracking-tight">Resource selector</h1>
      <p className="mt-2 max-w-3xl text-sm text-muted">
        Rank candidate enhancers by the priorities <em>you</em> set. Selection is a trade-off
        between target activity, selectivity, and basal leakage — there is no single best
        construct, so this tool surfaces the Pareto-optimal set and a sequence-diversified
        shortlist as a starting point for expert selection, not a replacement for it.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        {PROJECTS.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => setProject(p.id)}
            className={cn(
              "rounded-standard px-3 py-1.5 text-sm transition-colors",
              project === p.id ? "bg-charcoal-4 text-charcoal" : "text-charcoal-82 hover:bg-charcoal-3",
            )}
          >
            {p.label}
          </button>
        ))}
      </div>

      {isPending && <p className="mt-10 text-muted">Loading candidates…</p>}
      {error && <p className="mt-10 text-sm text-charcoal-82">{String(error)}</p>}

      {data && (
        <>
          <section className="mt-8 card">
            <h2 className="text-card-title font-semibold">Priorities</h2>
            <p className="mt-1 text-sm text-muted">
              Weight each axis (0 = ignore). Scores use within-pool percentiles, so weights are
              comparable across axes despite different scales.
            </p>
            <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-3">
              {AXIS_KEYS.map((k) => (
                <label key={k} className="block">
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm text-charcoal">{axisByKey[k]?.label ?? k}</span>
                    <span className="tabular-nums text-xs text-muted">{weights[k]}</span>
                  </div>
                  <input
                    type="range" min={0} max={100} value={weights[k]}
                    onChange={(e) => setWeights((w) => ({ ...w, [k]: Number(e.target.value) }))}
                    className="mt-2 w-full accent-charcoal"
                  />
                  <span className="text-[11px] text-muted">
                    {axisByKey[k]?.direction === "low" ? "lower is better" : "higher is better"}
                  </span>
                </label>
              ))}
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-4 text-sm">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={paretoOnly} onChange={(e) => setParetoOnly(e.target.checked)} className="accent-charcoal" />
                <span className="text-charcoal-82">Pareto-optimal only <span className="text-muted">({data.n_pareto})</span></span>
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={diversify} onChange={(e) => setDiversify(e.target.checked)} className="accent-charcoal" />
                <span className="text-charcoal-82">Diversify sequences <span className="text-muted">(collapse near-identical)</span></span>
              </label>
              <span className="text-muted text-xs ml-auto">
                {data.n.toLocaleString()} candidate enhancers (target ≥ 0.1, selectivity ≥ 1×)
              </span>
            </div>
          </section>

          <section className="mt-8 card">
            <h2 className="text-card-title font-semibold">
              Ranked candidates
              <span className="ml-2 text-sm font-normal text-muted">
                showing {shown.length}{diversify ? " representatives" : ""}
              </span>
            </h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead className="border-b border-cream-border text-xs tracking-wide text-muted bg-cream-light">
                  <tr>
                    <th className="py-2.5 px-3 font-medium text-right w-12">#</th>
                    <th className="py-2.5 px-3 font-medium">TF</th>
                    <th className="py-2.5 px-3 font-medium">Enhancer</th>
                    <th className="py-2.5 px-3 font-medium text-right">{axisByKey.target?.label.split(" (")[0]}</th>
                    <th className="py-2.5 px-3 font-medium text-right">{axisByKey.specificity?.label.split(" (")[0]}</th>
                    <th className="py-2.5 px-3 font-medium text-right">{axisByKey.basal?.label.split(" (")[0]}</th>
                    <th className="py-2.5 px-3 font-medium text-right">Score</th>
                    <th className="py-2.5 px-3 font-medium">Flags</th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((r, i) => (
                    <tr key={r.promoter} className="border-b border-cream-border hover:bg-charcoal-3">
                      <td className="py-2 px-3 text-right tabular-nums text-xs text-muted">{i + 1}</td>
                      <td className="py-2 px-3">
                        <Link
                          to={`/results/pwm/${encodeURIComponent(r.pwm)}?project=${encodeURIComponent(project)}`}
                          className="font-mono text-xs text-charcoal underline decoration-charcoal-40 underline-offset-2 hover:decoration-charcoal"
                        >
                          {r.tf}
                        </Link>
                      </td>
                      <td className="py-2 px-3">
                        <Link
                          to={`/library/${encodeURIComponent(r.promoter)}?project=${encodeURIComponent(project)}`}
                          className="font-mono text-xs text-charcoal-82 underline decoration-charcoal-40 underline-offset-2 hover:decoration-charcoal"
                        >
                          {r.promoter}
                        </Link>
                      </td>
                      <td className="py-2 px-3 text-right tabular-nums text-xs">{r.target.toFixed(2)}</td>
                      <td className="py-2 px-3 text-right tabular-nums text-xs font-semibold">{r.specificity.toFixed(1)}×</td>
                      <td className="py-2 px-3 text-right tabular-nums text-xs">{r.basal.toFixed(2)}</td>
                      <td className="py-2 px-3 text-right tabular-nums text-xs">{r.score.toFixed(3)}</td>
                      <td className="py-2 px-3">
                        <span className="flex flex-wrap gap-1">
                          {r.pareto && (
                            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700">Pareto</span>
                          )}
                          {diversify && r.members ? (
                            <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] text-zinc-600">+{r.members} similar</span>
                          ) : null}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
