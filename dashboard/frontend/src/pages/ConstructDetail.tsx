import { useParams, useSearchParams, useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type VariantParalog } from "@/lib/api";

// ---- Most-likely binding TF: which individual TF this site most likely binds ----
// Sequence-only, project-agnostic. Replaces the older family-level identity card;
// activity is folded in only as optional support/contradiction of a predicted shift.
const PARALOG_STYLE: Record<string, { label: string; cls: string }> = {
  assigned_top: { label: "Sequence matches design", cls: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20" },
  degenerate_assigned_plausible: { label: "Closely tied", cls: "bg-amber-50 text-amber-700 ring-1 ring-amber-600/20" },
  within_family_shift: { label: "Related TF favoured", cls: "bg-orange-50 text-orange-700 ring-1 ring-orange-600/20" },
  cross_family_shift: { label: "Different TF favoured", cls: "bg-rose-50 text-rose-700 ring-1 ring-rose-600/20" },
  unresolved: { label: "Unresolved", cls: "bg-zinc-100 text-zinc-600 ring-1 ring-zinc-500/20" },
};

function paralogSummary(d: VariantParalog) {
  const assigned = d.assigned_tf ?? "the designed TF";
  const best = d.best_tf ?? "another factor";
  const delta = d.delta_best_assigned != null ? Math.abs(d.delta_best_assigned).toFixed(2) : "—";
  const rank = d.assigned_rank ?? 0;
  switch (d.call) {
    case "assigned_top":
      return <>The designed factor <b className="text-charcoal">{assigned}</b> remains the best sequence match for this site — no predicted shift to another factor.</>;
    case "degenerate_assigned_plausible":
      return <>The closest sequence match is <b className="text-charcoal">{best}</b>, but the designed <b className="text-charcoal">{assigned}</b> is within {delta} bits — sequence cannot separate them, so {assigned} remains plausible.</>;
    case "within_family_shift":
      return <>This variant's sequence most closely matches <b className="text-charcoal">{best}</b>{d.within_family ? ", a motif-related factor" : ""}; the designed <b className="text-charcoal">{assigned}</b> ranks #{rank}.</>;
    case "cross_family_shift":
      return <>This variant's sequence best matches <b className="text-charcoal">{best}</b>, a motif-unrelated factor; the designed <b className="text-charcoal">{assigned}</b> is displaced (rank #{rank}).</>;
    default:
      return <>This site is too short or low-information to assign a single factor.</>;
  }
}

function ParalogCard({ d }: { d: VariantParalog }) {
  if (!d.available || !d.call) return null;
  const style = PARALOG_STYLE[d.call] ?? PARALOG_STYLE.unresolved;
  const cands = d.candidates ?? [];
  const best = cands[0]?.score ?? 0;
  const assignedInList = cands.some((c) => c.tf === d.assigned_tf);
  const isShift = d.call === "within_family_shift" || d.call === "cross_family_shift";
  const showLimit = isShift || d.call === "degenerate_assigned_plausible";

  const Row = ({ tf, score, designed, top }: { tf: string | null; score: number; designed: boolean; top: boolean }) => (
    <div className="flex items-center gap-3 py-1 text-xs">
      <span className={`w-24 shrink-0 font-mono ${top ? "font-semibold text-charcoal" : "text-charcoal-82"}`}>
        {tf ?? "—"}
      </span>
      {designed && (
        <span className="rounded-full bg-sky-50 px-2 py-0.5 text-[10px] font-medium text-sky-700 ring-1 ring-sky-600/20">
          designed
        </span>
      )}
      <span className="ml-auto tabular-nums text-charcoal">{score.toFixed(2)} bits</span>
      <span className="w-16 text-right tabular-nums text-muted">
        {top ? "best" : `−${(best - score).toFixed(2)}`}
      </span>
    </div>
  );

  return (
    <section className="mt-8 card">
      <h2 className="text-card-title font-semibold">Most-likely binding TF</h2>
      <p className="mt-1 text-sm text-muted">
        Predicted from the binding-site sequence, scored against every transcription factor's motif.
      </p>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${style.cls}`}>{style.label}</span>
        {d.confidence && (
          <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-charcoal-82 ring-1 ring-cream-border">
            {d.confidence}-confidence match
          </span>
        )}
        {d.resolution === "degenerate" && d.call !== "unresolved" && (
          <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-[11px] font-medium text-zinc-600">
            top matches within 1 bit
          </span>
        )}
      </div>

      <p className="mt-4 text-sm text-charcoal-82">{paralogSummary(d)}</p>

      {cands.length > 0 && (
        <div className="mt-5 rounded-comfortable border border-cream-border bg-cream-light px-4 py-3">
          <p className="text-[11px] uppercase tracking-wide text-muted">Best-matching transcription factors</p>
          <div className="mt-2 divide-y divide-cream-border">
            {cands.map((c) => (
              <Row key={c.rank} tf={c.tf} score={c.score} designed={c.tf === d.assigned_tf} top={c.rank === 1} />
            ))}
            {!assignedInList && d.assigned_rank && d.assigned_rank > cands.length && d.assigned_score != null && (
              <div className="flex items-center gap-3 py-1 text-xs">
                <span className="w-24 shrink-0 font-mono text-charcoal-82">{d.assigned_tf}</span>
                <span className="rounded-full bg-sky-50 px-2 py-0.5 text-[10px] font-medium text-sky-700 ring-1 ring-sky-600/20">
                  designed
                </span>
                <span className="text-[10px] text-muted">rank {d.assigned_rank}</span>
                <span className="ml-auto tabular-nums text-muted">{d.assigned_score.toFixed(2)} bits</span>
                <span className="w-16 text-right tabular-nums text-muted">−{(best - d.assigned_score).toFixed(2)}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {d.rel_affinity != null && (
        <div className="mt-4 flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-xs">
          <span className="text-muted">Relative affinity</span>
          <span className="tabular-nums font-medium text-charcoal">{d.rel_affinity.toFixed(2)}</span>
          <span className="text-[11px] text-muted">
            (1.00 = consensus, the highest-affinity variant of this motif)
          </span>
        </div>
      )}

      {showLimit && (
        <p className="mt-4 text-[11px] leading-relaxed text-muted">
          Closely related transcription factors recognise nearly the same motif, so the sequence narrows
          the candidates but does not single out one factor with certainty.
        </p>
      )}
    </section>
  );
}

function MetadataRow({ k, label, v }: { k: string; label?: string; v: unknown }) {
  if (v === null || v === undefined || v === "") return null;
  return (
    <div className="grid grid-cols-1 md:grid-cols-[14rem_1fr] gap-1 py-2 border-b border-cream-border last:border-0">
      <dt
        className={
          label
            ? "text-xs uppercase tracking-wide text-muted"
            : "text-xs text-muted font-mono"
        }
      >
        {label ?? k}
      </dt>
      <dd className="text-sm text-charcoal-82 break-all">{String(v)}</dd>
    </div>
  );
}

// Low-signal columns we don't want surfaced in the condensed metadata view.
// Match case-insensitively; prefixes cover all Lambert/Reddy/DNase variants.
const ENHANCER_META_HIDDEN_PREFIXES = ["lambert_", "reddy_", "dnase_"];
const ENHANCER_META_HIDDEN_KEYS = new Set(["tf_name_by_ppm"]);

function isHiddenMetaKey(k: string): boolean {
  const lc = k.toLowerCase();
  if (ENHANCER_META_HIDDEN_KEYS.has(lc)) return true;
  return ENHANCER_META_HIDDEN_PREFIXES.some((p) => lc.startsWith(p));
}

export default function ConstructDetail() {
  const { id = "" } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const fromProject = searchParams.get("project");

  const { data, isPending } = useQuery({
    queryKey: ["construct", id],
    queryFn: () => api.getConstruct(id),
    enabled: !!id,
    retry: false,
  });

  const { data: perf } = useQuery({
    queryKey: ["construct-performance", id],
    queryFn: () => api.constructPerformance(id),
    enabled: !!id,
  });

  const { data: paralog } = useQuery({
    queryKey: ["construct-paralog", id],
    queryFn: () => api.constructParalog(id),
    enabled: !!id,
    retry: false,
  });

  // Always show a single project's performance card. Preference order:
  //   1. Project carried in the URL (?project=…) when the user drilled down
  //      from a Results page.
  //   2. Otherwise, the first project that has at least one non-null metric
  //      for this construct (skips projects where it wasn't measured).
  //   3. Fallback to the first project entry returned by the backend.
  const visibleProjects = (() => {
    const all = perf?.projects ?? [];
    if (all.length === 0) return [];
    if (fromProject) {
      const match = all.find((p) => p.project === fromProject);
      if (match) return [match];
    }
    const withData = all.find((p) =>
      Object.values(p.metrics).some((v) => v !== null && v !== undefined),
    );
    return [withData ?? all[0]];
  })();

  const backLabel = fromProject ? "← Back to results" : "← Back to library";

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-12">
      <div className="text-sm">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="text-charcoal-82 underline decoration-charcoal-40 underline-offset-2 hover:decoration-charcoal hover:text-charcoal"
        >
          {backLabel}
        </button>
      </div>

      <h1 className="mt-4 text-display-sub font-semibold tracking-tight font-mono break-all">
        {id}
      </h1>

      {isPending && <p className="mt-12 text-muted">Loading…</p>}

      {perf && visibleProjects.length > 0 && (
        <section className="mt-12 card">
          <h2 className="text-card-title font-semibold">Performance</h2>
          <p className="mt-1 text-sm text-muted">
            Activity readouts for this enhancer in{" "}
            <span className="font-mono text-charcoal-82">
              {visibleProjects[0]?.project}
            </span>
            .
          </p>
          <div className="mt-6">
            {visibleProjects.map((p) => (
              <div
                key={p.project}
                className="rounded-comfortable border border-cream-border bg-cream-light p-4"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <h3 className="text-sm font-semibold text-charcoal">{p.project}</h3>
                  <span className="text-[11px] text-muted font-mono">{p.title}</span>
                </div>
                <div className="mt-3 grid grid-cols-1 gap-1 text-xs">
                  {Object.entries(p.metrics).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between gap-3 border-b border-cream-border last:border-0 py-1">
                      <span className="text-muted">{k}</span>
                      <span className="tabular-nums text-charcoal">
                        {v === null ? "—" : v.toFixed(3)}
                      </span>
                    </div>
                  ))}
                </div>
                {p.by_ppm_name && (
                  <div className="mt-3 text-[11px] text-muted">
                    PPM:{" "}
                    <Link
                      to={`/results/pwm/${encodeURIComponent(p.by_ppm_name)}?project=${encodeURIComponent(p.project)}${p.rank != null ? `&rank=${p.rank}` : ""}`}
                      className="font-mono text-charcoal-82 underline decoration-charcoal-40 underline-offset-2 hover:decoration-charcoal"
                    >
                      {p.by_ppm_name}
                    </Link>
                    {p.rank !== null && <> · PPM rank {p.rank}</>}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {paralog && <ParalogCard d={paralog} />}

      {data && (
        <section className="mt-8 card">
          <h2 className="text-card-title font-semibold">Enhancer metadata</h2>
          <dl className="mt-4">
            <MetadataRow
              k="enhancer_name"
              v={data.construct.promoter_name}
            />
            {data.metadata
              ? Object.entries(data.metadata)
                  .filter(([k]) => !isHiddenMetaKey(k))
                  .map(([k, v]) => <MetadataRow key={k} k={k} v={v} />)
              : null}
          </dl>
          {!data.metadata && (
            <p className="mt-4 text-sm text-muted">
              No matching row in <code className="font-mono">all_enhancer_metadata_111525.csv</code>{" "}
              for this construct&apos;s <code className="font-mono">by_ppm_name</code> +{" "}
              <code className="font-mono">rank</code>.
            </p>
          )}
        </section>
      )}
    </div>
  );
}
