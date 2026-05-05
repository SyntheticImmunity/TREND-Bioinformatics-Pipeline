/**
 * Manuscript-reproduction tab. Intended for the review period only.
 *
 * To remove this tab post-acceptance:
 *   1. Delete this file (`pages/Reproduce.tsx`).
 *   2. In `App.tsx`: drop the `Reproduce` import, the `/reproduce` route,
 *      and the "Reproduce manuscript" nav entry.
 *   3. (optional) In `dashboard/backend/main.py`: drop the three
 *      `/run/reproduce/...` endpoints and the imports they pull from
 *      `oracle/run_example.py` (`reproduce_streaming`, `get_latest_reproduce_dir`).
 *   4. (optional) In `dashboard/backend/oracle/run_example.py`: drop
 *      `reproduce_streaming`, `_REPRODUCE_PROJECTS`, `_REPRODUCE_COUNT_TABLES`,
 *      `_LATEST_REPRODUCE_DIRS`, `get_latest_reproduce_dir`, `REPRODUCE_RELEASE_TAG`,
 *      `REPRODUCE_RELEASE_URL`.
 *   5. (optional) On the GitHub release `library-data-2026-05-04`, the four
 *      `*__alignment_result_*.csv` assets become unused; safe to delete.
 *   6. (optional) In `lib/api.ts`: drop `runReproduceStream` and
 *      `reproduceDownloadUrl`.
 *   7. In `REVIEWERS.md`: drop the "Reproducing the manuscript's results"
 *      section if no longer relevant.
 */

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
  approxDownloadMB: number;
}

const PROJECTS: ProjectCardSpec[] = [
  {
    key: "ovarian_cancer",
    title: "Ovarian cancer",
    blurb:
      "Reproduces the OV8 / IOSE / ID8 enhancer activity tables from the deposited post-alignment count tables.",
    approxDownloadMB: 1300,
  },
  {
    key: "T_cell_activation",
    title: "T-cell activation",
    blurb:
      "Reproduces the per-donor activation-responsive enhancer tables from the deposited post-alignment count tables.",
    approxDownloadMB: 1080,
  },
];

function formatMB(bytes?: number): string {
  if (!bytes) return "—";
  return `${(bytes / (1024 * 1024)).toFixed(0)} MB`;
}

function ReproduceCard({ spec }: { spec: ProjectCardSpec }) {
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
    <article className="card">
      <h2 className="text-card-title font-semibold">{spec.title}</h2>
      <p className="mt-3 text-sm text-charcoal-82">{spec.blurb}</p>

      <div className="mt-6 border-t border-cream-border pt-5">
        {state.status === "idle" && (
          <button
            type="button"
            onClick={() => setState({ status: "confirming" })}
            className="btn-ghost no-underline w-full"
          >
            Reproduce this analysis
          </button>
        )}

        {state.status === "confirming" && (
          <div>
            <p className="text-sm text-charcoal-82">
              First run downloads the post-alignment count tables
              (~{spec.approxDownloadMB} MB) from GitHub, then runs the
              manuscript's Step 9 R script (~3–5 min). The result will be a
              CSV you can compare manually against the deposited copy.
            </p>
            <div className="mt-4 flex gap-3">
              <button
                type="button"
                onClick={handleRun}
                className="btn-primary"
              >
                Download and run
              </button>
              <button
                type="button"
                onClick={reset}
                className="btn-ghost no-underline"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {state.status === "running" && (
          <div className="text-sm">
            <p className="text-charcoal-82">{state.stage}</p>
            {state.currentFile && (
              <p className="mt-1 text-xs text-muted font-mono break-all">
                {state.currentFile}
              </p>
            )}
            {state.downloadedBytes !== undefined && (
              <p className="mt-1 text-xs text-muted tabular-nums">
                {formatMB(state.downloadedBytes)}
                {state.totalBytes ? ` / ${formatMB(state.totalBytes)}` : ""}
              </p>
            )}
          </div>
        )}

        {state.status === "done" && (
          <div className="text-sm">
            <p className="text-charcoal-82">
              <span className="font-semibold">Run complete</span>
              {state.runtimeSeconds !== undefined && (
                <span className="text-muted">
                  {" "}— Step 9 finished in {state.runtimeSeconds.toFixed(0)} s.
                </span>
              )}
            </p>
            <p className="mt-2 text-xs text-muted">
              Download both files and compare with your tool of choice
              (<code>diff</code>, pandas, R). The dashboard does not assert
              a match — you decide.
            </p>
            <ul className="mt-4 space-y-3">
              {(state.producedFiles ?? []).map((filename) => (
                <li
                  key={filename}
                  className="rounded-card border border-cream-border bg-cream p-3"
                >
                  <div className="font-mono text-xs text-charcoal-82 break-all">
                    {filename}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-3 text-xs">
                    <a
                      href={reproduceDownloadUrl(spec.key, "produced", filename)}
                      download={`produced__${filename}`}
                      className="underline"
                    >
                      Produced just now ↓
                    </a>
                    {state.depositedFiles?.includes(filename) && (
                      <a
                        href={reproduceDownloadUrl(spec.key, "deposited", filename)}
                        download={`deposited__${filename}`}
                        className="underline"
                      >
                        Deposited (in repository) ↓
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={reset}
              className="mt-4 text-xs text-muted underline"
            >
              Reset
            </button>
          </div>
        )}

        {state.status === "error" && (
          <div className="text-sm">
            <p className="text-charcoal-82">
              <span className="font-semibold">Run failed.</span>{" "}
              <span className="text-muted">{state.error}</span>
            </p>
            <button
              type="button"
              onClick={reset}
              className="mt-3 btn-ghost no-underline"
            >
              Reset
            </button>
          </div>
        )}
      </div>
    </article>
  );
}

export default function Reproduce() {
  return (
    <div className="mx-auto max-w-[1200px] px-6 py-16">
      <h1 className="text-display-section font-semibold tracking-tight">
        Reproduce manuscript
      </h1>
      <p className="mt-4 max-w-2xl text-muted">
        Row-for-row verification of the deposited activity tables. On first
        click for a project, the dashboard fetches the post-alignment count
        tables from this repository's GitHub release, runs the manuscript's
        unmodified Step 9 R script against them, and exposes both the
        newly-produced CSV and the deposited reference CSV for download.
        You compare them yourself — the dashboard does not assert a match.
      </p>

      <section className="mt-12 grid gap-6 md:grid-cols-2">
        {PROJECTS.map((spec) => (
          <ReproduceCard key={spec.key} spec={spec} />
        ))}
      </section>

      <p className="mt-8 text-xs text-muted">
        Command-line equivalent (without the dashboard):{" "}
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
    </div>
  );
}
