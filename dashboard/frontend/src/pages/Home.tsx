import { Link } from "react-router-dom";

import { WorkflowSchematic } from "@/components/WorkflowSchematic";

const ON_RAMPS = [
  {
    to: "/library",
    title: "Browse the library",
    body: "The designed enhancer library, organized by transcription factor, promoter, and barcoded construct.",
  },
  {
    to: "/run/example",
    title: "Validate your install",
    body: "Confirm your Docker install reproduces our published outputs end-to-end. One-time check before running on your own data.",
  },
  {
    to: "/results",
    title: "Published results",
    body: "Promoter-level enhancer activity tables from both projects, with annotated columns.",
  },
];

export default function Home() {
  return (
    <div className="mx-auto max-w-[1200px] px-6 py-22">
      <h1 className="text-display-hero font-semibold tracking-tight">TREND</h1>
      <p className="mt-6 max-w-2xl text-body-lg text-muted">
        Interactive interface for the TREND enhancer-screening platform. Browse the
        designed library, run analyses on your own samples, and explore published
        activity results.
      </p>

      <div className="mt-16 grid gap-6 md:grid-cols-3">
        {ON_RAMPS.map((r) => (
          <Link
            key={r.to}
            to={r.to}
            className="card no-underline transition-shadow hover:shadow-focus"
          >
            <h2 className="text-card-title font-semibold">{r.title}</h2>
            <p className="mt-3 text-sm text-muted">{r.body}</p>
            <span className="mt-6 inline-block text-sm text-charcoal underline underline-offset-2">
              Open
            </span>
          </Link>
        ))}
      </div>

      <section className="mt-30">
        <h2 className="text-display-sub font-semibold tracking-tight">How TREND works</h2>
        <p className="mt-3 max-w-2xl text-muted">
          A high-throughput screen for synthetic enhancer discovery: pooled lentiviral
          delivery of barcoded designs, followed by RNA / DNA quantification of activity
          across cell contexts.
        </p>
        <div className="mt-10">
          <WorkflowSchematic />
        </div>
      </section>
    </div>
  );
}
