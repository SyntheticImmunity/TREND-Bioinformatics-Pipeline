import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api, startRun } from "@/lib/api";
import { StateMachine, type StepState } from "@/components/StateMachine";

export default function Run() {
  const qc = useQueryClient();
  const { data: stepsData } = useQuery({
    queryKey: ["pipeline-steps"],
    queryFn: api.pipelineSteps,
  });
  const { data: history } = useQuery({
    queryKey: ["run-history"],
    queryFn: () => api.runHistory(10),
    refetchInterval: 5000,
  });

  const [stepState, setStepState] = useState<Record<string, StepState>>({});
  const [running, setRunning] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleDryRun() {
    if (!stepsData) return;
    setRunning(true);
    setError(null);
    setActiveRunId(null);
    setStepState(
      Object.fromEntries(
        stepsData.steps.map((s) => [s.id, { status: "pending" } as StepState]),
      ),
    );

    try {
      await startRun(
        { project: "ovarian_cancer", mode: "dry_run" },
        (event) => {
          if (event.event === "run_started") {
            setActiveRunId(String(event.run_id));
          } else if (event.event === "step_started") {
            const id = String(event.step_id);
            setStepState((prev) => ({
              ...prev,
              [id]: { ...prev[id], status: "running" },
            }));
          } else if (event.event === "step_finished") {
            const id = String(event.step_id);
            setStepState((prev) => ({
              ...prev,
              [id]: {
                status: event.status as StepState["status"],
                runtime: event.runtime_seconds as number,
                exit_code: event.exit_code as number,
              },
            }));
          }
        },
      );
      qc.invalidateQueries({ queryKey: ["run-history"] });
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-16">
      <h1 className="text-display-section font-semibold tracking-tight">Pipeline</h1>
      <p className="mt-4 max-w-2xl text-muted">
        The TREND pipeline takes raw sequencing reads through demultiplexing,
        barcode extraction, alignment to the Lib4 reference, and per-promoter
        enhancer-activity quantification. Run a simulation to preview the workflow,
        or verify the bundled example for a full reproducibility check.
      </p>

      <div className="mt-8 flex flex-wrap gap-4 items-center">
        <button
          onClick={handleDryRun}
          disabled={running || !stepsData}
          className="btn-primary"
        >
          {running ? "Simulating…" : "Simulate a run"}
        </button>
        <Link to="/run/example" className="btn-ghost">
          Verify the bundled example →
        </Link>
        {activeRunId && (
          <span className="text-xs text-muted font-mono">run id: {activeRunId}</span>
        )}
      </div>

      {error && (
        <div className="mt-6 card border-charcoal-40">
          <p className="text-sm text-charcoal-82">{error}</p>
        </div>
      )}

      {stepsData && (
        <section className="mt-12">
          <StateMachine steps={stepsData.steps} state={stepState} />
        </section>
      )}

      <section className="mt-16">
        <h2 className="text-card-title font-semibold">Recent runs</h2>
        {history?.runs.length === 0 && (
          <p className="mt-4 text-sm text-muted">No runs yet.</p>
        )}
        {(history?.runs.length ?? 0) > 0 && (
          <table className="mt-6 w-full text-sm">
            <thead className="border-b border-cream-border text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="text-left py-2 pr-4 font-medium">Run ID</th>
                <th className="text-left py-2 pr-4 font-medium">Project</th>
                <th className="text-left py-2 pr-4 font-medium">Mode</th>
                <th className="text-left py-2 pr-4 font-medium">Status</th>
                <th className="text-left py-2 pr-4 font-medium">Started</th>
                <th className="text-left py-2 font-medium">Finished</th>
              </tr>
            </thead>
            <tbody>
              {history?.runs.map((r) => (
                <tr key={r.run_id} className="border-b border-cream-border">
                  <td className="py-2 pr-4 font-mono text-xs">{r.run_id}</td>
                  <td className="py-2 pr-4">{r.project}</td>
                  <td className="py-2 pr-4 font-mono text-xs">{r.mode}</td>
                  <td className="py-2 pr-4">{r.status}</td>
                  <td className="py-2 pr-4 text-xs text-muted">{r.created_at}</td>
                  <td className="py-2 text-xs text-muted">{r.finished_at ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
