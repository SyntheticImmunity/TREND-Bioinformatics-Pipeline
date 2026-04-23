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
            Per-donor activity contrast between resting and stimulated CD4 T cells.
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
        <h2 className="text-card-title font-semibold">Adding your own project</h2>
        <p className="mt-3 text-sm text-charcoal-82">
          Use the <code className="font-mono">trend init</code> command to scaffold a
          new project from one of the templates above:
        </p>
        <pre className="mt-4 overflow-x-auto rounded-comfortable border border-cream-border bg-cream p-4 text-xs">
{`trend init my-experiment --template ovarian_cancer
$EDITOR my-experiment/samplesheet.yaml
trend run --inputs ./fastqs/ --output ./runs/$(date +%F)/`}
        </pre>
      </section>
    </div>
  );
}
