export default function Project() {
  return (
    <div className="mx-auto max-w-[1200px] px-6 py-16">
      <h1 className="text-display-section font-semibold tracking-tight">Projects</h1>
      <p className="mt-4 max-w-2xl text-muted">
        Bundled analyses for ovarian cancer enhancer screening and T-cell activation
        responsiveness. Each project ships with a sample sheet documenting the cell
        lines, replicates, and threshold parameters used for the published analysis.
      </p>

      <section className="mt-12 grid gap-6 md:grid-cols-2">
        <article className="card">
          <h2 className="text-card-title font-semibold">Ovarian cancer</h2>
          <p className="mt-3 text-sm text-charcoal-82">
            Enhancer activity contrasted between OV8 (ovarian cancer), ID8 (mouse
            ovarian cancer), and IOSE (immortalized normal control) cell lines.
            Tumor selectivity ratios identify enhancers preferentially active in
            malignant cells.
          </p>
          <dl className="mt-6 grid grid-cols-2 gap-y-2 text-xs">
            <dt className="text-muted">Cell lines</dt>
            <dd className="font-mono text-charcoal-82">OV8, IOSE, ID8</dd>
            <dt className="text-muted">Replicates</dt>
            <dd className="font-mono text-charcoal-82">8 samples (3 + 3 + 2)</dd>
            <dt className="text-muted">Barcode threshold</dt>
            <dd className="font-mono text-charcoal-82">3 per promoter</dd>
          </dl>
        </article>

        <article className="card">
          <h2 className="text-card-title font-semibold">T-cell activation</h2>
          <p className="mt-3 text-sm text-charcoal-82">
            Per-donor activity contrast between resting and stimulated primary human T cells (total CD4+CD8).
            Activation-induced enhancers identified per donor; reproducibility
            across donors is the primary readout.
          </p>
          <dl className="mt-6 grid grid-cols-2 gap-y-2 text-xs">
            <dt className="text-muted">Conditions</dt>
            <dd className="font-mono text-charcoal-82">rest, stim</dd>
            <dt className="text-muted">Donors</dt>
            <dd className="font-mono text-charcoal-82">2</dd>
            <dt className="text-muted">Barcode threshold</dt>
            <dd className="font-mono text-charcoal-82">8 per promoter</dd>
          </dl>
        </article>
      </section>

      <section className="mt-12 card">
        <h2 className="text-card-title font-semibold">Running TREND on your own data</h2>
        <p className="mt-3 text-sm text-charcoal-82">
          Picking DNA thresholds is a human-in-the-loop step. You run the
          pipeline once with default thresholds, inspect the per-sample
          DNA-coverage PDF that comes out, fill in tuned thresholds, then
          re-run only Step 9 — minutes, not hours. Iterate until satisfied.
        </p>
        <p className="mt-3 text-sm text-charcoal-82">
          The full walkthrough has copy-pasteable bash and PowerShell commands
          for the Docker and bioinformatician-direct paths, plus the sample
          sheet template.
        </p>
        <div className="mt-5">
          <a
            href="https://github.com/SyntheticImmunity/TREND-Bioinformatics-Pipeline/blob/main/REVIEWERS.md#running-trend-on-your-own-data"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary inline-block"
          >
            Read the full walkthrough →
          </a>
        </div>
      </section>
    </div>
  );
}
