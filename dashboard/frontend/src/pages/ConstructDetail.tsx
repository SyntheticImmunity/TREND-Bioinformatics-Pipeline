import { useParams, useSearchParams, useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type VariantIdentity } from "@/lib/api";

const CALL_STYLE: Record<string, { label: string; cls: string }> = {
  retained: { label: "Retained", cls: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20" },
  switched: { label: "Switched", cls: "bg-amber-50 text-amber-700 ring-1 ring-amber-600/20" },
  dual: { label: "Dual", cls: "bg-indigo-50 text-indigo-700 ring-1 ring-indigo-600/20" },
  lost: { label: "Lost", cls: "bg-rose-50 text-rose-700 ring-1 ring-rose-600/20" },
  ambiguous: { label: "Ambiguous", cls: "bg-zinc-100 text-zinc-600 ring-1 ring-zinc-500/20" },
};
const CONF_STYLE: Record<string, string> = {
  high: "bg-emerald-50 text-emerald-700",
  med: "bg-amber-50 text-amber-700",
  low: "bg-zinc-100 text-zinc-600",
};

function pfmt(p?: number | null): string {
  if (p == null) return "—";
  if (p >= 1) return "n.s.";
  return `p = ${p.toExponential(0)}`;
}

function identitySummary(d: VariantIdentity): string {
  const own = d.assigned_tf ?? "its assigned TF";
  const other = d.other_tf ?? "a different TF";
  switch (d.call) {
    case "retained":
      return `This binding site still matches ${own}.`;
    case "switched":
      return `The sequence now matches ${other} rather than ${own} — a few-nucleotide change moved a different TF in.`;
    case "dual":
      return d.dual_kind === "distinct"
        ? `Matches both ${own} and ${other}, at two distinct sites in this variant.`
        : `The same site matches both ${own} and ${other} — which factor binds is ambiguous.`;
    case "lost":
      return `No transcription-factor motif is recognised in this site (likely a non-binder).`;
    case "ambiguous":
      return `This site is too short or low-information to assign a TF with confidence.`;
    default:
      return "";
  }
}

function IdentityCard({ d }: { d: VariantIdentity }) {
  if (!d.available || !d.call) return null;
  const style = CALL_STYLE[d.call] ?? CALL_STYLE.ambiguous;
  const callLabel =
    d.call === "dual" && d.dual_kind
      ? `${style.label} · ${d.dual_kind === "distinct" ? "two sites" : "shared site"}`
      : style.label;
  const isSwitchDual = d.call === "switched" || d.call === "dual";
  return (
    <section className="mt-8 card">
      <h2 className="text-card-title font-semibold">Inferred TF identity</h2>
      <p className="mt-1 text-sm text-muted">
        Which transcription factor this binding site matches, predicted from a calibrated scan of all
        6,012 motifs.
      </p>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${style.cls}`}>{callLabel}</span>
        {d.confidence && (
          <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${CONF_STYLE[d.confidence]}`}>
            {d.confidence} confidence
          </span>
        )}
        {isSwitchDual &&
          (d.functionally_corroborated ? (
            <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-700">
              functionally corroborated
            </span>
          ) : (
            <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-[11px] font-medium text-zinc-600">
              not corroborated
            </span>
          ))}
      </div>

      <p className="mt-4 text-sm text-charcoal-82">{identitySummary(d)}</p>

      <dl className="mt-5 grid grid-cols-1 gap-x-4 gap-y-2 text-xs sm:grid-cols-[12rem_1fr]">
        <dt className="text-muted">Assigned TF match</dt>
        <dd className="font-mono tabular-nums text-charcoal">
          {d.assigned_tf ?? "—"} · {pfmt(d.p_ownfam)}
        </dd>
        {isSwitchDual && (
          <>
            <dt className="text-muted">Alternative TF match</dt>
            <dd className="font-mono tabular-nums text-charcoal">
              {d.other_tf ?? "—"} · {pfmt(d.p_otherfam)}
            </dd>
          </>
        )}
        {isSwitchDual && d.functionally_corroborated && (
          <>
            <dt className="text-muted">Functional support for {d.other_tf}</dt>
            <dd className="text-charcoal">
              its own sensors are tumour-active and this variant&apos;s activity matches them
            </dd>
          </>
        )}
      </dl>

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

  const { data: identity } = useQuery({
    queryKey: ["construct-identity", id],
    queryFn: () => api.constructIdentity(id),
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

      {identity && <IdentityCard d={identity} />}

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
