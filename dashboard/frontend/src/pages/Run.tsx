import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/lib/api";
import { StateMachine } from "@/components/StateMachine";

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
        and contract is documented below.
      </p>

      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Link to="/run/example" className="btn-ghost no-underline">
          Run install check →
        </Link>
        <span className="text-sm text-muted">
          Verify your install reproduces our published outputs.
        </span>
      </div>

      {stepsData && (
        <section className="mt-12">
          <StateMachine steps={stepsData.steps} state={{}} />
        </section>
      )}
    </div>
  );
}
