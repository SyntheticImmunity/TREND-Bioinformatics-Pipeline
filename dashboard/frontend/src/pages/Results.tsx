import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { SelectivityScatter } from "@/components/SelectivityScatter";

export default function Results() {
  const { data: projects } = useQuery({
    queryKey: ["results-projects"],
    queryFn: api.resultsProjects,
  });

  const [project, setProject] = useState<string | null>(null);

  useEffect(() => {
    if (!project && projects?.projects.length) {
      setProject(projects.projects[0].name);
    }
  }, [projects, project]);

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-16">
      <h1 className="text-display-section font-semibold tracking-tight">Published results</h1>
      <p className="mt-4 max-w-2xl text-muted">
        Differential enhancer activity for each project. Click any selective
        enhancer to drill into its motif and per-construct activity.
      </p>

      <section className="mt-8 flex flex-wrap gap-4">
        <label className="flex flex-col text-sm">
          <span className="text-muted text-xs mb-1">Project</span>
          <select
            value={project ?? ""}
            onChange={(e) => setProject(e.target.value)}
            className="bg-cream border border-cream-border rounded-standard px-3 py-1.5 text-sm focus:outline-none focus:border-charcoal-40"
          >
            {projects?.projects.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
      </section>

      {project && (
        <section className="mt-12 card">
          <h2 className="text-card-title font-semibold">Selectivity</h2>
          <p className="text-sm text-muted mt-1">
            Differential enhancer activity (experimental vs. control). Selective
            enhancers cluster at the top of the strip plot.
          </p>
          <div className="mt-6">
            <SelectivityScatter project={project} />
          </div>
        </section>
      )}
    </div>
  );
}
