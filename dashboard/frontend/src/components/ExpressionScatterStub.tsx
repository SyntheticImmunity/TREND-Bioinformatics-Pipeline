/**
 * Panel G of Figure 1: scatter of differential TF mRNA expression vs differential
 * enhancer activity. Requires per-condition RNA-seq quantification (TPM or similar)
 * for the cell lines under study, which is not bundled with the pipeline.
 *
 * This stub explains what the panel will show and how to populate it.
 */
export function ExpressionScatterStub({ project }: { project: string }) {
  return (
    <div className="card border-cream-border">
      <h2 className="text-card-title font-semibold">TF expression vs enhancer activity</h2>
      <p className="mt-2 text-sm text-charcoal-82">
        For each transcription factor, this panel will plot the differential TF mRNA
        expression (tumor vs normal) against the corresponding differential synthetic
        enhancer activity measured by TREND, revealing how well TF protein abundance
        predicts enhancer activation in each cell context.
      </p>
      <div className="mt-4 rounded-comfortable border border-dashed border-cream-border bg-cream p-6 text-sm text-muted">
        <div className="font-semibold text-charcoal mb-2">Expression data required</div>
        <p>
          To populate this panel for the <code className="font-mono">{project}</code>{" "}
          project, provide a TF expression matrix as a CSV with columns:
        </p>
        <pre className="mt-3 text-xs font-mono text-charcoal-82 overflow-x-auto">
{`TF,log2FC_tumor_vs_normal,padj
MYC,2.43,1.2e-08
E2F7,1.89,4.5e-06
...`}
        </pre>
        <p className="mt-3">
          Drop the file into{" "}
          <code className="font-mono">project_data/expression/{project}.csv</code>{" "}
          and refresh — the panel will render automatically.
        </p>
      </div>
    </div>
  );
}
