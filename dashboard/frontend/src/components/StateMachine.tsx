import { cn } from "@/lib/cn";
import type { PipelineStep } from "@/lib/api";

export type StepStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export interface StepState {
  status: StepStatus;
  runtime?: number;
  exit_code?: number | null;
}

interface StateMachineProps {
  steps: PipelineStep[];
  state: Record<string, StepState>;
}

const STATUS_BADGE: Record<StepStatus, string> = {
  pending: "bg-charcoal-3 text-muted",
  running: "bg-charcoal text-cream-light animate-pulse",
  completed: "bg-charcoal-82 text-cream-light",
  failed: "border border-charcoal-40 text-charcoal",
  skipped: "border border-cream-border text-muted",
};

const STATUS_LABEL: Record<StepStatus, string> = {
  pending: "pending",
  running: "running…",
  completed: "done",
  failed: "failed",
  skipped: "skipped",
};

export function StateMachine({ steps, state }: StateMachineProps) {
  return (
    <ol className="space-y-4">
      {steps.map((step, idx) => {
        const s = state[step.id]?.status ?? "pending";
        const runtime = state[step.id]?.runtime;
        return (
          <li
            key={step.id}
            className={cn(
              "flex items-start gap-4 rounded-card border border-cream-border bg-cream p-4",
              s === "running" && "shadow-focus",
              s === "failed" && "border-charcoal-40",
            )}
          >
            <div className="flex flex-col items-center pt-1">
              <span className="font-mono text-xs text-muted tabular-nums">
                {String(idx + 1).padStart(2, "0")}
              </span>
            </div>
            <div className="flex-1">
              <div className="flex items-baseline gap-2">
                <h4 className="font-semibold text-charcoal">{step.name}</h4>
                {step.optional && (
                  <span className="text-xs text-muted">(optional)</span>
                )}
              </div>
              <p className="mt-1 text-sm text-charcoal-82">{step.short_purpose}</p>
              <div className="mt-2 flex items-center gap-3 text-xs text-muted">
                <span className="font-mono">{step.tool}</span>
                {runtime !== undefined && (
                  <span className="tabular-nums">{runtime.toFixed(2)}s</span>
                )}
              </div>
            </div>
            <span
              className={cn(
                "rounded-full px-3 py-1 text-xs uppercase tracking-wide whitespace-nowrap",
                STATUS_BADGE[s],
              )}
            >
              {STATUS_LABEL[s]}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
