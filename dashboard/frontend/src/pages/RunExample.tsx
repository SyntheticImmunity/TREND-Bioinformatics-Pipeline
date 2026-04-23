import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api, type ExampleTier, type OracleFileResult, type OracleReport } from "@/lib/api";
import { cn } from "@/lib/cn";

interface TierSpec {
  id: ExampleTier;
  title: string;
  blurb: string;
  expectedRuntime: string;
  requirements: string;
}

const TIERS: TierSpec[] = [
  {
    id: "smoke",
    title: "Quick check",
    blurb:
      "Compares the bundled published activity tables against themselves. Confirms the dashboard's comparison machinery is wired up. No external tools required.",
    expectedRuntime: "~1 second",
    requirements: "Python only.",
  },
  {
    id: "step9",
    title: "Activity reproduction",
    blurb:
      "Re-runs the unchanged Step-9 R script against a 1,000-promoter slice of the published ovarian cancer alignment data and verifies the output matches the published activity tables row-for-row.",
    expectedRuntime: "~30 seconds",
    requirements: "R + tidyverse + Rsamtools.",
  },
  {
    id: "pipeline",
    title: "Full pipeline reproduction",
    blurb:
      "Runs Steps 1-9 end-to-end on simulated FASTQs (50 promoters x 5 barcodes, 8 samples) and verifies the post-alignment count matrix matches the analytically-computed expected counts.",
    expectedRuntime: "~3 minutes",
    requirements: "Conda environment (bowtie2, samtools, cutadapt, fastx-toolkit, R).",
  },
];

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
  const [tier, setTier] = useState<ExampleTier>("smoke");
  const [report, setReport] = useState<OracleReport | null>(null);
  const mutation = useMutation({
    mutationFn: (chosenTier: ExampleTier) => api.runExample("ovarian_cancer", chosenTier),
    onSuccess: setReport,
  });

  const tierSpec = TIERS.find((t) => t.id === tier)!;

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-16">
      <h1 className="text-display-section font-semibold tracking-tight">
        Verify the example
      </h1>
      <p className="mt-4 max-w-2xl text-muted">
        Three tiers of reproducibility check, each comparing this environment&apos;s
        outputs against the bundled reference. Pick a tier based on which tools
        you have installed; results render below.
      </p>

      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {TIERS.map((t) => {
          const isActive = t.id === tier;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTier(t.id)}
              className={cn(
                "card text-left transition-shadow",
                isActive ? "shadow-focus border-charcoal" : "hover:shadow-focus",
              )}
            >
              <div className="flex items-baseline justify-between">
                <h3 className="text-card-title font-semibold">{t.title}</h3>
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wide",
                    isActive ? "bg-charcoal text-cream-light" : "bg-charcoal-3 text-muted",
                  )}
                >
                  Tier {TIERS.indexOf(t) + 1}
                </span>
              </div>
              <p className="mt-3 text-sm text-charcoal-82">{t.blurb}</p>
              <div className="mt-4 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-muted">
                <span>Runtime</span>
                <span className="text-charcoal-82">{t.expectedRuntime}</span>
                <span>Needs</span>
                <span className="text-charcoal-82">{t.requirements}</span>
              </div>
            </button>
          );
        })}
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-4">
        <button
          onClick={() => mutation.mutate(tier)}
          disabled={mutation.isPending}
          className="btn-primary"
        >
          {mutation.isPending ? "Running…" : `Run ${tierSpec.title.toLowerCase()}`}
        </button>
        <Link to="/results" className="btn-ghost">
          Browse published results →
        </Link>
      </div>

      {mutation.error && (
        <div className="mt-6 card border-charcoal-40">
          <p className="text-sm text-charcoal-82">{String(mutation.error)}</p>
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
              <h2 className="text-card-title font-semibold">
                {report.project === "ovarian_cancer" ? "Ovarian cancer" : "T-cell activation"}
                <span className="ml-2 text-sm font-normal text-muted">
                  · {TIERS.find((t) => t.id === report.tier)?.title}
                </span>
              </h2>
              <p className="text-sm text-muted mt-1">
                {report.mode === "real"
                  ? `Live re-run · completed in ${report.runtime_seconds.toFixed(2)}s`
                  : `Reference comparison · completed in ${report.runtime_seconds.toFixed(2)}s`}
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
