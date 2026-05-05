import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export default function Run() {
  const { data: stepsData } = useQuery({
    queryKey: ["pipeline-steps"],
    queryFn: api.pipelineSteps,
  });

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-16">
      <h1 className="text-display-section font-semibold tracking-tight">Pipeline</h1>
      <p className="mt-4 max-w-2xl text-muted">
        TREND processes raw sequencing reads through nine ordered steps:
        demultiplexing, barcode extraction, alignment to the Lib4 reference,
        and per-promoter enhancer-activity quantification. Each step's tool
        and short purpose is documented below. To verify your install can
        run all of these, see the Install check tab.
      </p>

      {stepsData && (
        <ol className="mt-12 space-y-3">
          {stepsData.steps.map((step, idx) => (
            <li
              key={step.id}
              className="flex items-start gap-4 rounded-card border border-cream-border bg-cream p-4"
            >
              <span className="font-mono text-xs text-muted tabular-nums pt-1">
                {String(idx + 1).padStart(2, "0")}
              </span>
              <div className="flex-1">
                <div className="flex items-baseline gap-2">
                  <h4 className="font-semibold text-charcoal">{step.name}</h4>
                  {step.optional && (
                    <span className="text-xs text-muted">(optional)</span>
                  )}
                </div>
                <p className="mt-1 text-sm text-charcoal-82">{step.short_purpose}</p>
                <p className="mt-2 text-xs text-muted font-mono">{step.tool}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
