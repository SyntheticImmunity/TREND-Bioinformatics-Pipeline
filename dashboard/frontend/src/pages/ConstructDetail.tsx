import { useParams, useSearchParams, useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

function MetadataRow({ k, v }: { k: string; v: unknown }) {
  if (v === null || v === undefined || v === "") return null;
  return (
    <div className="grid grid-cols-1 md:grid-cols-[14rem_1fr] gap-1 py-2 border-b border-cream-border last:border-0">
      <dt className="text-xs text-muted font-mono">{k}</dt>
      <dd className="text-sm text-charcoal-82 break-all">{String(v)}</dd>
    </div>
  );
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

  // Project isolation: when the user drilled down from a specific project,
  // only show that project's performance card.
  const visibleProjects = fromProject
    ? perf?.projects.filter((p) => p.project === fromProject) ?? []
    : perf?.projects ?? [];

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
          <h2 className="text-card-title font-semibold">
            {fromProject ? "Performance" : "Performance across projects"}
          </h2>
          <p className="mt-1 text-sm text-muted">
            {fromProject
              ? `Activity readouts for this promoter in ${fromProject}.`
              : "Activity readouts for this promoter in every TREND screen where it was measured."}
          </p>
          <div className={fromProject ? "mt-6" : "mt-6 grid gap-6 lg:grid-cols-2"}>
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
                    PWM:{" "}
                    <Link
                      to={`/results/pwm/${encodeURIComponent(p.by_ppm_name)}?project=${encodeURIComponent(p.project)}`}
                      className="font-mono text-charcoal-82 underline decoration-charcoal-40 underline-offset-2 hover:decoration-charcoal"
                    >
                      {p.by_ppm_name}
                    </Link>
                    {p.rank !== null && <> · PWM rank {p.rank}</>}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {data && (
        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <section className="card">
            <h2 className="text-card-title font-semibold">Construct metadata</h2>
            <dl className="mt-4">
              {Object.entries(data.construct).map(([k, v]) => (
                <MetadataRow key={k} k={k} v={v} />
              ))}
            </dl>
          </section>

          <section className="card">
            <h2 className="text-card-title font-semibold">Enhancer metadata</h2>
            {data.metadata ? (
              <dl className="mt-4">
                {Object.entries(data.metadata).map(([k, v]) => (
                  <MetadataRow key={k} k={k} v={v} />
                ))}
              </dl>
            ) : (
              <p className="mt-4 text-sm text-muted">
                No matching row in <code className="font-mono">all_enhancer_metadata_111525.csv</code>{" "}
                for this construct&apos;s <code className="font-mono">by_ppm_name</code> +{" "}
                <code className="font-mono">rank</code>.
              </p>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
