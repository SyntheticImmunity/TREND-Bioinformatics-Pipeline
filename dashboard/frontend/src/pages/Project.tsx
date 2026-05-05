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
          Picking DNA thresholds is a human-in-the-loop step — you have to look at
          per-sample DNA-coverage distributions before you can choose them sensibly.
          The flow is iterative:
        </p>
        <ol className="mt-3 list-decimal pl-5 text-sm text-charcoal-82 space-y-1">
          <li>
            <code className="font-mono text-xs">trend init my-experiment --template ovarian_cancer</code>
            {" "}— scaffold a project; produces <code className="font-mono text-xs">samplesheet.yaml</code> pre-filled with the published OvCa example.
          </li>
          <li>
            Edit <code className="font-mono text-xs">samplesheet.yaml</code> with your cell lines, replicate counts, and DNA/RNA FASTQ filenames. Leave <code className="font-mono text-xs">dna_threshold</code> blank.
          </li>
          <li>
            Run <code className="font-mono text-xs">trend run --inputs ./fastqs --output ./runs/&lt;date&gt; --samplesheet ./my-experiment/samplesheet.yaml --profile snakemake</code>
            {" "}— produces the alignment result, a preliminary activity table, and a per-sample DNA-distribution PDF.
          </li>
          <li>
            Inspect <code className="font-mono text-xs">runs/&lt;date&gt;/DNA_threshold_for_samples.pdf</code> — pick the threshold per sample where each curve plateaus.
          </li>
          <li>
            Edit <code className="font-mono text-xs">runs/&lt;date&gt;/samplesheet.yaml</code> (the dropped copy in the run dir), fill in <code className="font-mono text-xs">dna_threshold</code>, then re-run only Step 9 with{" "}
            <code className="font-mono text-xs">trend run --resume ./runs/&lt;date&gt; --rerun-from step9</code>{" "}— takes ~minutes, not hours. Iterate until satisfied.
          </li>
        </ol>
        <p className="mt-4 text-sm text-charcoal-82">
          For the full walkthrough with copy-pasteable commands for both bash/zsh and PowerShell, including the Docker volume-mount form and the <em>For bioinformaticians: direct R control</em> path, see <strong>REVIEWERS.md</strong> § <em>Running TREND on your own data</em> or <strong>MANUAL.md</strong> § 7.
        </p>
      </section>
    </div>
  );
}
