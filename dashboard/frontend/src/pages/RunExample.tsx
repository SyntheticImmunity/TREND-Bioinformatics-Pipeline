import { useState } from "react";
import { Link } from "react-router-dom";

import {
  runExampleStream,
  type ExampleTier,
  type OracleFileResult,
  type OracleReport,
} from "@/lib/api";
import { cn } from "@/lib/cn";

const INSTALL_CHECK_TIER: ExampleTier = "install_check";

function ResultCard({ r }: { r: OracleFileResult }) {
  return (
    <div
      className={cn(
        "card",
        r.equivalent ? "border-cream-border" : "border-charcoal-40",
      )}
    >
      <div className="flex items-baseline justify-between gap-4">
        <h3 className="text-card-title font-semibold font-mono break-all">{r.filename}</h3>
        <span
          className={cn(
            "rounded-full px-3 py-1 text-xs uppercase tracking-wide whitespace-nowrap",
            r.equivalent ? "bg-charcoal-82 text-cream-light" : "border border-charcoal-40",
          )}
        >
          {r.equivalent ? "match" : "differs"}
        </span>
      </div>
      <p className="mt-2 text-sm text-charcoal-82">{r.summary}</p>
      {r.numeric_mismatches && r.numeric_mismatches.length > 0 && (
        <details className="mt-3">
          <summary className="cursor-pointer text-xs text-muted">
            Numeric diffs (first {r.numeric_mismatches.length})
          </summary>
          <table className="mt-2 w-full text-xs">
            <thead>
              <tr className="text-left text-muted">
                <th className="py-1 pr-2">column</th>
                <th className="py-1 pr-2">row</th>
                <th className="py-1 pr-2 text-right">actual</th>
                <th className="py-1 text-right">expected</th>
              </tr>
            </thead>
            <tbody>
              {r.numeric_mismatches.map((m, i) => (
                <tr key={i} className="border-t border-cream-border">
                  <td className="py-1 pr-2 font-mono">{m.column}</td>
                  <td className="py-1 pr-2 tabular-nums">{m.row}</td>
                  <td className="py-1 pr-2 text-right tabular-nums">{String(m.actual)}</td>
                  <td className="py-1 text-right tabular-nums">{String(m.expected)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </div>
  );
}

export default function RunExample() {
  const [report, setReport] = useState<OracleReport | null>(null);
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  async function handleRun() {
    setRunning(true);
    setReport(null);
    setError(null);
    setStage("Starting…");

    try {
      await runExampleStream("ovarian_cancer", INSTALL_CHECK_TIER, (event) => {
        switch (event.event) {
          case "run_started":
            setStage("Phase 1 — running pipeline against simulated FASTQs (~3 min)");
            break;
          case "step_started": {
            const sid = String(event.step_id);
            if (sid === "step_9_enhancer_activity") {
              setStage("Phase 2 — running Step 9 R analysis (~30 s)");
            }
            break;
          }
          case "step_finished": {
            const sid = String(event.step_id);
            if (sid === "step_8_count_barcodes") {
              setStage("Phase 1 complete; preparing Step 9…");
            } else if (sid === "step_9_enhancer_activity") {
              setStage("Comparing outputs…");
            }
            break;
          }
          case "report":
            setReport(event.payload as OracleReport);
            break;
        }
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
      setStage("");
    }
  }

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-16">
      <h1 className="text-display-section font-semibold tracking-tight">Install check</h1>
      <p className="mt-4 max-w-2xl text-muted">
        Confirms your install can run TREND end-to-end across all nine pipeline
        steps and reproduces the published outputs. Run this once after
        installation; no further check is needed before bringing your own data.
      </p>

      <section className="mt-12 card">
        <div className="flex items-baseline justify-between gap-4 flex-wrap">
          <h2 className="text-card-title font-semibold">End-to-end install check</h2>
          <span className="text-xs text-muted">~3–4 minutes total</span>
        </div>
        <p className="mt-3 text-sm text-charcoal-82">
          Runs both phases of the pipeline back-to-back and reports a
          single result.
        </p>
        <ul className="mt-4 space-y-2 text-sm text-charcoal-82 list-disc pl-5">
          <li>
            <strong>Phase 1 — Steps 2–8 (alignment + count tables).</strong>{" "}
            Snakemake on a small simulated FASTQ fixture; produces the
            post-alignment count matrix and verifies it matches the
            analytically-computed expected values. Validates bowtie2,
            cutadapt, samtools, fastx-toolkit, and the count-table R script.
          </li>
          <li>
            <strong>Phase 2 — Step 9 (enhancer-activity quantification).</strong>{" "}
            R + tidyverse on a 1,000-promoter slice of real OvCa alignment
            data; verifies the activity table matches the published values
            row-for-row. Validates the per-project Step 9 R script.
          </li>
        </ul>
        <p className="mt-3 text-xs text-muted">
          For the full-data manuscript reproduction (the deposited 57k-promoter
          tables), use the <em>Reproduce this analysis</em> buttons on the{" "}
          <Link to="/project" className="underline">Projects</Link> page.
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-4">
          <button
            onClick={handleRun}
            disabled={running}
            className="btn-primary"
          >
            {running ? "Running…" : "Run install check"}
          </button>
          <Link to="/results" className="btn-ghost no-underline">
            Browse published results →
          </Link>
        </div>

        {running && stage && (
          <p className="mt-4 text-sm text-charcoal-82">{stage}</p>
        )}
      </section>

      {error && (
        <div className="mt-6 card border-charcoal-40">
          <p className="text-sm text-charcoal-82">{error}</p>
        </div>
      )}

      {report && (
        <section className="mt-12">
          <div
            className={cn(
              "card flex items-baseline gap-4",
              report.overall_pass ? "border-cream-border" : "border-charcoal-40",
            )}
          >
            <span
              className={cn(
                "rounded-full px-4 py-1.5 text-sm uppercase tracking-wide",
                report.overall_pass
                  ? "bg-charcoal text-cream-light"
                  : "border border-charcoal-40 text-charcoal",
              )}
            >
              {report.overall_pass ? "all match" : "differences found"}
            </span>
            <div>
              <h2 className="text-card-title font-semibold">Install check result</h2>
              <p className="text-sm text-muted mt-1">
                {report.mode === "real"
                  ? `Live re-run · completed in ${report.runtime_seconds.toFixed(2)} s`
                  : `Reference comparison · completed in ${report.runtime_seconds.toFixed(2)} s`}
              </p>
            </div>
          </div>

          {report.notes.length > 0 && (
            <div className="mt-4 card bg-cream border-cream-border">
              <h3 className="text-sm font-semibold text-charcoal">About this result</h3>
              <ul className="mt-2 space-y-1 text-sm text-charcoal-82">
                {report.notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-6 grid gap-4">
            {report.file_results.map((r) => (
              <ResultCard key={r.filename} r={r} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
