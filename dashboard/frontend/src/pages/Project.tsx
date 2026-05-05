import { useState } from "react";

import { runReproduceStream, reproduceDownloadUrl } from "@/lib/api";

type ProjectKey = "ovarian_cancer" | "T_cell_activation";

interface ReproduceState {
  status: "idle" | "confirming" | "running" | "done" | "error";
  stage?: string;
  downloadedBytes?: number;
  totalBytes?: number;
  currentFile?: string;
  runtimeSeconds?: number;
  producedFiles?: string[];
  depositedFiles?: string[];
  error?: string;
}

interface ProjectCardSpec {
  key: ProjectKey;
  title: string;
  blurb: string;
  metadata: Array<[string, string]>;
  approxDownloadMB: number;
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
    approxDownloadMB: 1300,
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
    approxDownloadMB: 1080,
  },
];

function formatMB(bytes?: number): string {
  if (!bytes) return "—";
  return `${(bytes / (1024 * 1024)).toFixed(0)} MB`;
}

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

function ReproduceMini({ spec }: { spec: ProjectCardSpec }) {
  const [state, setState] = useState<ReproduceState>({ status: "idle" });

  async function handleRun() {
    setState({ status: "running", stage: "Starting…" });
    try {
      await runReproduceStream(spec.key, (event) => {
        setState((prev) => {
          switch (event.event) {
            case "run_started":
              return {
                ...prev,
                status: "running",
                stage: event.download_needed
                  ? `Will download ~${event.approx_download_mb} MB before running R`
                  : "Count tables already cached — starting analysis…",
              };
            case "download_started":
              return { ...prev, stage: "Downloading count tables…" };
            case "download_progress":
              return {
                ...prev,
                stage: "Downloading count tables…",
                currentFile: event.filename as string | undefined,
                downloadedBytes: event.downloaded_bytes as number | undefined,
                totalBytes: event.total_bytes as number | undefined,
              };
            case "download_finished":
              return { ...prev, stage: "Download complete; starting R…" };
            case "analysis_started":
              return {
                ...prev,
                stage: `Running Step 9 R script (~${event.estimated_minutes ?? 5} minutes)…`,
                downloadedBytes: undefined,
                totalBytes: undefined,
                currentFile: undefined,
              };
            case "analysis_finished":
              return {
                ...prev,
                stage: "R completed; finalizing…",
                runtimeSeconds: event.runtime_seconds as number | undefined,
              };
            case "report": {
              const payload = event.payload as {
                error: string | null;
                produced_files: string[];
                deposited_files: string[];
                runtime_seconds: number;
              };
              if (payload.error) {
                return { ...prev, status: "error", error: payload.error };
              }
              return {
                ...prev,
                status: "done",
                runtimeSeconds: payload.runtime_seconds,
                producedFiles: payload.produced_files,
                depositedFiles: payload.deposited_files,
              };
            }
            default:
              return prev;
          }
        });
      });
    } catch (e) {
      setState({ status: "error", error: String(e) });
    }
  }

  const reset = () => setState({ status: "idle" });

  return (
    <div className="rounded-card border border-cream-border bg-cream p-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h4 className="font-semibold text-charcoal text-sm">{spec.title}</h4>
        {state.status === "idle" && (
          <button
            type="button"
            onClick={() => setState({ status: "confirming" })}
            className="text-xs underline text-charcoal-82"
          >
            Reproduce →
          </button>
        )}
      </div>

      {state.status === "confirming" && (
        <div className="mt-3 text-xs">
          <p className="text-charcoal-82">
            First run downloads ~{spec.approxDownloadMB} MB from GitHub, then
            runs the manuscript's Step 9 R script (~3–5 min).
          </p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={handleRun}
              className="btn-primary text-xs px-3 py-1"
            >
              Download and run
            </button>
            <button
              type="button"
              onClick={reset}
              className="text-xs underline text-charcoal-82"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {state.status === "running" && (
        <div className="mt-3 text-xs">
          <p className="text-charcoal-82">{state.stage}</p>
          {state.currentFile && (
            <p className="mt-1 text-muted font-mono break-all">{state.currentFile}</p>
          )}
          {state.downloadedBytes !== undefined && (
            <p className="mt-1 text-muted tabular-nums">
              {formatMB(state.downloadedBytes)}
              {state.totalBytes ? ` / ${formatMB(state.totalBytes)}` : ""}
            </p>
          )}
        </div>
      )}

      {state.status === "done" && (
        <div className="mt-3 text-xs">
          <p className="text-charcoal-82">
            <span className="font-semibold">Run complete</span>
            {state.runtimeSeconds !== undefined && (
              <span className="text-muted">
                {" "}— {state.runtimeSeconds.toFixed(0)} s.
              </span>
            )}
          </p>
          <ul className="mt-3 space-y-2">
            {(state.producedFiles ?? []).map((filename) => (
              <li key={filename}>
                <div className="font-mono text-muted break-all">{filename}</div>
                <div className="mt-1 flex flex-wrap gap-3">
                  <a
                    href={reproduceDownloadUrl(spec.key, "produced", filename)}
                    download={`produced__${filename}`}
                    className="underline"
                  >
                    Produced ↓
                  </a>
                  {state.depositedFiles?.includes(filename) && (
                    <a
                      href={reproduceDownloadUrl(spec.key, "deposited", filename)}
                      download={`deposited__${filename}`}
                      className="underline"
                    >
                      Deposited ↓
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={reset}
            className="mt-3 underline text-muted"
          >
            Reset
          </button>
        </div>
      )}

      {state.status === "error" && (
        <div className="mt-3 text-xs">
          <p className="text-charcoal-82">
            <span className="font-semibold">Run failed.</span>{" "}
            <span className="text-muted">{state.error}</span>
          </p>
          <button
            type="button"
            onClick={reset}
            className="mt-2 underline text-muted"
          >
            Reset
          </button>
        </div>
      )}
    </div>
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

      <section className="mt-12">
        <h2 className="text-card-title font-semibold">
          Reproducing the manuscript's results
        </h2>
        <p className="mt-2 max-w-3xl text-sm text-charcoal-82">
          For row-for-row verification of the deposited activity tables, click
          <em> Reproduce</em> on either project below. The dashboard fetches
          the count tables from this repository's GitHub release on first use,
          runs the manuscript's unmodified Step 9 R script, and exposes both
          the produced and deposited CSVs for download. Compare them manually.
        </p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {PROJECTS.map((spec) => (
            <ReproduceMini key={spec.key} spec={spec} />
          ))}
        </div>
        <p className="mt-3 text-xs text-muted">
          Command-line equivalent:{" "}
          <a
            href="https://github.com/SyntheticImmunity/TREND-Bioinformatics-Pipeline/blob/main/REVIEWERS.md#reproducing-the-manuscripts-results"
            target="_blank"
            rel="noopener noreferrer"
            className="underline"
          >
            REVIEWERS.md § Reproducing the manuscript's results
          </a>
          .
        </p>
      </section>
    </div>
  );
}
