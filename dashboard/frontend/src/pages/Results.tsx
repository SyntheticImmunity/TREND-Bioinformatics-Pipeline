import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/lib/api";
import { GlossaryTooltip } from "@/components/GlossaryTooltip";
import { SelectivityScatter } from "@/components/SelectivityScatter";
import { ExpressionScatterStub } from "@/components/ExpressionScatterStub";

const PAGE_SIZE = 100;

function isLikelyConstructLink(col: string): boolean {
  return col === "promoter_name_bc" || col === "promoter_name";
}

export default function Results() {
  const { data: projects } = useQuery({
    queryKey: ["results-projects"],
    queryFn: api.resultsProjects,
  });

  const [project, setProject] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  // Pick the first project + first file by default once loaded.
  useEffect(() => {
    if (!project && projects?.projects.length) {
      const p = projects.projects[0];
      setProject(p.name);
      if (p.files.length) setFilename(p.files[0]);
    }
  }, [projects, project]);

  const { data, isPending, error } = useQuery({
    queryKey: ["results-file", project, filename, page],
    queryFn: () => api.resultsFile(project!, filename!, PAGE_SIZE, page * PAGE_SIZE),
    enabled: !!project && !!filename,
  });

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-16">
      <h1 className="text-display-section font-semibold tracking-tight">Published results</h1>
      <p className="mt-4 max-w-2xl text-muted">
        Promoter-level enhancer activity for each project. Hover any underlined
        column header for a definition; click a promoter identifier to view it
        in the library.
      </p>

      <section className="mt-8 flex flex-wrap gap-4">
        <label className="flex flex-col text-sm">
          <span className="text-muted text-xs mb-1">Project</span>
          <select
            value={project ?? ""}
            onChange={(e) => {
              setProject(e.target.value);
              const p = projects?.projects.find((x) => x.name === e.target.value);
              setFilename(p?.files[0] ?? null);
              setPage(0);
            }}
            className="bg-cream border border-cream-border rounded-standard px-3 py-1.5 text-sm focus:outline-none focus:border-charcoal-40"
          >
            {projects?.projects.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-sm">
          <span className="text-muted text-xs mb-1">File</span>
          <select
            value={filename ?? ""}
            onChange={(e) => {
              setFilename(e.target.value);
              setPage(0);
            }}
            className="bg-cream border border-cream-border rounded-standard px-3 py-1.5 text-sm font-mono focus:outline-none focus:border-charcoal-40"
          >
            {projects?.projects
              .find((p) => p.name === project)
              ?.files.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
          </select>
        </label>
      </section>

      {project === "ovarian_cancer" && (
        <>
          <section className="mt-12 card">
            <h2 className="text-card-title font-semibold">Cancer selectivity</h2>
            <p className="text-sm text-muted mt-1">
              Differential enhancer activity in OV8 (ovarian cancer) vs IOSE
              (normal ovarian epithelial control). Cancer-selective enhancers
              cluster on the right at high activity.
            </p>
            <div className="mt-6">
              <SelectivityScatter project="ovarian_cancer" />
            </div>
          </section>

          <section className="mt-8">
            <ExpressionScatterStub project="ovarian_cancer" />
          </section>
        </>
      )}

      {error && (
        <div className="mt-8 card border-charcoal-40">
          <p className="text-sm text-charcoal-82">{String(error)}</p>
        </div>
      )}

      {isPending && project && filename && (
        <p className="mt-12 text-muted">Loading {filename}…</p>
      )}

      {data && (
        <>
          {data.schema_description && (
            <p className="mt-8 text-sm text-charcoal-82 italic max-w-3xl">
              {data.schema_description}
            </p>
          )}

          <div className="mt-6 card overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead className="border-b border-cream-border text-xs uppercase tracking-wide text-muted">
                <tr>
                  {data.columns.map((c) => (
                    <th key={c.name} className="py-2.5 pr-4 text-left font-medium whitespace-nowrap">
                      <GlossaryTooltip text={c.name} description={c.description}>
                        <span className="font-mono">{c.name}</span>
                      </GlossaryTooltip>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row, i) => (
                  <tr key={i} className="border-b border-cream-border hover:bg-charcoal-3">
                    {data.columns.map((c) => {
                      const v = row[c.name];
                      const display =
                        v === null || v === undefined
                          ? <span className="text-muted">—</span>
                          : c.type === "float"
                          ? <span className="tabular-nums">{Number(v).toFixed(4)}</span>
                          : c.type === "integer"
                          ? <span className="tabular-nums">{String(v)}</span>
                          : <span className="font-mono text-xs">{String(v)}</span>;

                      if (isLikelyConstructLink(c.name) && typeof v === "string" && v) {
                        return (
                          <td key={c.name} className="py-1.5 pr-4">
                            <Link
                              to={`/library/${encodeURIComponent(String(v))}`}
                              className="font-mono text-xs no-underline text-charcoal hover:underline"
                            >
                              {String(v)}
                            </Link>
                          </td>
                        );
                      }
                      return (
                        <td key={c.name} className="py-1.5 pr-4 align-top">
                          {display}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-6 flex items-center justify-between text-sm">
            <span className="text-muted tabular-nums">
              Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, data.total)} of{" "}
              {data.total.toLocaleString()}
            </span>
            <div className="flex gap-2">
              <button
                className="btn-ghost text-sm"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                ← Prev
              </button>
              <button
                className="btn-ghost text-sm"
                disabled={(page + 1) * PAGE_SIZE >= data.total}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
