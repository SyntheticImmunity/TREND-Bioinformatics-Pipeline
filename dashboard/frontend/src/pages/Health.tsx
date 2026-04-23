import { useQuery } from "@tanstack/react-query";

import { api, type PreflightCheck } from "@/lib/api";
import { cn } from "@/lib/cn";

const CATEGORY_LABEL: Record<PreflightCheck["category"], string> = {
  binary: "External tool",
  python_package: "Python package",
  r_package: "R package",
};

const OVERALL_BADGE: Record<string, string> = {
  ok: "bg-charcoal text-cream-light",
  degraded: "border border-charcoal-40 text-charcoal",
  blocked: "border border-charcoal text-charcoal bg-charcoal-4",
};

function CheckRow({ c }: { c: PreflightCheck }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr_1fr] gap-3 py-3 border-b border-cream-border last:border-0">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "w-2 h-2 rounded-full shrink-0",
            c.found ? "bg-charcoal-82" : c.severity === "error" ? "bg-charcoal" : "bg-charcoal-40",
          )}
        />
        <span className="font-mono text-sm text-charcoal">{c.name}</span>
        <span className="text-xs text-muted">{CATEGORY_LABEL[c.category]}</span>
      </div>
      <div className="text-sm text-charcoal-82">
        <p>{c.purpose}</p>
        {!c.found && c.hint && (
          <p className="mt-2 text-xs">
            <span className="text-muted">Install:</span>{" "}
            <code className="font-mono text-charcoal-82">{c.hint}</code>
          </p>
        )}
      </div>
      <div className="text-xs text-muted text-right tabular-nums">
        {c.found ? c.version || "present" : "missing"}
      </div>
    </div>
  );
}

export default function Health() {
  const { data: pf, isPending: pfPending, error: pfError, refetch } = useQuery({
    queryKey: ["preflight"],
    queryFn: () => api.preflight(false),
    refetchInterval: 30000,
  });

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 5000,
  });

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-16">
      <h1 className="text-display-section font-semibold tracking-tight">System status</h1>
      <p className="mt-4 max-w-2xl text-muted">
        Backend status and the pipeline tools available on this machine. Updated
        every 30 seconds.
      </p>

      <div className="mt-8 flex flex-wrap items-center gap-4">
        <button
          className="btn-primary"
          onClick={() => api.preflight(true).then(() => refetch())}
        >
          Refresh now
        </button>
      </div>

      {health && (
        <section className="mt-12 grid gap-4 sm:grid-cols-3">
          <div className="card">
            <div className="text-sm text-muted">Backend</div>
            <div className="mt-2 text-card-title font-semibold">{health.status}</div>
            <div className="text-xs text-muted mt-1">v{health.version}</div>
          </div>
          <div className="card">
            <div className="text-sm text-muted">Library data</div>
            <div className="mt-2 text-card-title font-semibold">
              {health.library_ingested ? "loaded" : "not loaded"}
            </div>
            {!health.library_ingested && (
              <div className="text-xs text-muted mt-1">
                Run <code className="font-mono">trend ingest</code>
              </div>
            )}
          </div>
          <div className="card">
            <div className="text-sm text-muted">Runtime</div>
            <div className="mt-2 text-card-title font-semibold">
              {health.container_mode ? "Container" : "Host"}
            </div>
          </div>
        </section>
      )}

      {pfError && (
        <div className="mt-8 card border-charcoal-40">
          <p className="text-sm text-charcoal-82">{String(pfError)}</p>
        </div>
      )}

      {pf && (
        <section className="mt-12 card">
          <div className="flex items-center justify-between gap-4 mb-4">
            <h2 className="text-card-title font-semibold">Pipeline tools</h2>
            <span
              className={cn(
                "rounded-full px-3 py-1 text-xs uppercase tracking-wide",
                OVERALL_BADGE[pf.overall],
              )}
            >
              {pf.overall}
            </span>
          </div>
          <p className="text-sm text-charcoal-82">{pf.summary}</p>
          <p className="text-xs text-muted mt-1 font-mono">
            {pf.os_name} · {pf.os_version}
          </p>

          <div className="mt-6">
            {pf.checks.map((c) => (
              <CheckRow key={`${c.category}:${c.name}`} c={c} />
            ))}
          </div>
        </section>
      )}

      {pfPending && <p className="mt-12 text-muted">Checking environment…</p>}
    </div>
  );
}
