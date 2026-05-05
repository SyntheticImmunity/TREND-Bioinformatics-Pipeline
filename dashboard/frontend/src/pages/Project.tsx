interface ProjectCardSpec {
  key: string;
  title: string;
  blurb: string;
  metadata: Array<[string, string]>;
}

const PROJECTS: ProjectCardSpec[] = [
  {
    key: "ovarian_cancer",
    title: "Ovarian cancer",
    blurb:
      "Enhancer activity contrasted between OV8 (ovarian cancer), ID8 (mouse ovarian cancer), and IOSE (immortalized normal control) cell lines. Tumor selectivity ratios identify enhancers preferentially active in malignant cells.",
    metadata: [
      ["Cell lines", "OV8, IOSE, ID8"],
      ["Replicates", "8 samples (3 + 3 + 2)"],
      ["Barcode threshold", "3 per promoter"],
    ],
  },
  {
    key: "T_cell_activation",
    title: "T-cell activation",
    blurb:
      "Per-donor activity contrast between resting and stimulated primary human T cells (total CD4+CD8). Activation-induced enhancers identified per donor; reproducibility across donors is the primary readout.",
    metadata: [
      ["Conditions", "rest, stim"],
      ["Donors", "2"],
      ["Barcode threshold", "8 per promoter"],
    ],
  },
];

function ProjectInfoCard({ spec }: { spec: ProjectCardSpec }) {
  return (
    <article className="card">
      <h2 className="text-card-title font-semibold">{spec.title}</h2>
      <p className="mt-3 text-sm text-charcoal-82">{spec.blurb}</p>
      <dl className="mt-6 grid grid-cols-2 gap-y-2 text-xs">
        {spec.metadata.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-muted">{label}</dt>
            <dd className="font-mono text-charcoal-82">{value}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

export default function Project() {
  return (
    <div className="mx-auto max-w-[1200px] px-6 py-16">
      <h1 className="text-display-section font-semibold tracking-tight">Projects</h1>
      <p className="mt-4 max-w-2xl text-muted">
        Bundled analyses for ovarian cancer enhancer screening and T-cell
        activation responsiveness. Each project ships with a sample sheet
        documenting the cell lines, replicates, and threshold parameters
        used for the published analysis.
      </p>

      <section className="mt-12 grid gap-6 md:grid-cols-2">
        {PROJECTS.map((spec) => (
          <ProjectInfoCard key={spec.key} spec={spec} />
        ))}
      </section>

      <section className="mt-16 card">
        <h2 className="text-card-title font-semibold">Running TREND on your own data</h2>
        <p className="mt-3 text-sm text-charcoal-82">
          The bundled analyses are starting templates — TREND extends to your
          own cell lines, donor cohorts, or experimental contrasts. The
          typical flow: scaffold a project with your sample design, run the
          pipeline once, inspect the diagnostics it produces, tune parameters
          in the sample sheet, and re-run just the affected analysis step.
          Minutes per iteration.
        </p>
        <div className="mt-5">
          <a
            href="https://github.com/SyntheticImmunity/TREND-Bioinformatics-Pipeline/blob/main/REVIEWERS.md#running-trend-on-your-own-data"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-ghost no-underline"
          >
            Read the full walkthrough →
          </a>
        </div>
      </section>
    </div>
  );
}
