import { useParams, Link } from "react-router-dom";
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
  const { data, isPending, error } = useQuery({
    queryKey: ["construct", id],
    queryFn: () => api.getConstruct(id),
    enabled: !!id,
  });

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-16">
      <div className="text-sm text-muted">
        <Link to="/library" className="text-charcoal">
          ← Back to library
        </Link>
      </div>

      <h1 className="mt-4 text-display-sub font-semibold tracking-tight font-mono break-all">
        {id}
      </h1>

      {isPending && <p className="mt-12 text-muted">Loading…</p>}
      {error && (
        <div className="mt-12 card border-charcoal-40">
          <p className="text-sm text-charcoal-82">{String(error)}</p>
        </div>
      )}

      {data && (
        <div className="mt-12 grid gap-6 lg:grid-cols-2">
          <section className="card">
            <h2 className="text-card-title font-semibold">Construct (Lib4_info)</h2>
            <dl className="mt-4">
              {Object.entries(data.construct).map(([k, v]) => (
                <MetadataRow key={k} k={k} v={v} />
              ))}
            </dl>
          </section>

          <section className="card">
            <h2 className="text-card-title font-semibold">Enhancer metadata join</h2>
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
