import { useParams, useSearchParams, useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

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
