import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { PwmHistogram, type HistogramMetric } from "@/components/PwmHistogram";
import { SequenceLogo } from "@/components/SequenceLogo";

export default function PwmDetail() {
  const { pwmName: encoded = "" } = useParams();
  const [searchParams] = useSearchParams();
  const project = searchParams.get("project") ?? "ovarian_cancer";
  const pwmName = decodeURIComponent(encoded);

  const [metric, setMetric] = useState<HistogramMetric>("selectivity_ratio");

  const { data: scatter, isPending: scatterPending, error: scatterError } = useQuery({
    queryKey: ["selectivity-scatter", project],
    queryFn: () => api.selectivityScatter(project),
  });

  const { data: pwmData, isPending: pwmsPending } = useQuery({
    queryKey: ["pwms"],
    queryFn: api.pwms,
    staleTime: Infinity,
  });

  const ppm = pwmData?.pwms?.[pwmName];
  const matchingRows = (scatter?.rows ?? []).filter(
    (r) => r.selective && r.by_ppm_name === pwmName,
  );
  const allRowsForPwm = (scatter?.rows ?? []).filter((r) => r.by_ppm_name === pwmName);

  return (
    <div className="mx-auto max-w-[1100px] px-6 py-12">
      <div className="text-sm">
        <Link
          to={`/results?project=${encodeURIComponent(project)}`}
          className="text-charcoal-82 underline decoration-charcoal-40 underline-offset-2 hover:decoration-charcoal hover:text-charcoal"
        >
          ← Back to results
        </Link>
      </div>

      <div className="mt-6 flex flex-wrap items-baseline gap-3">
        <h1 className="text-display-section font-semibold tracking-tight font-mono break-all">
          {pwmName}
        </h1>
        <span className="text-sm text-muted">PWM activity profile · {project}</span>
      </div>

      <section className="mt-10 card">
        <h2 className="text-card-title font-semibold">Sequence logo</h2>
        <p className="mt-1 text-sm text-muted">
          Position probability matrix from the ENCODE/MotifDb collection. Letter
          heights show information content in bits (max 2 per position).
        </p>
        <div className="mt-6">
          {pwmsPending ? (
            <p className="text-muted text-sm">Loading PPM…</p>
          ) : ppm ? (
            <SequenceLogo ppm={ppm} width={Math.min(640, ppm[0].length * 48)} height={120} showAxis />
          ) : (
            <p className="text-sm text-charcoal-82">
              No PPM found for <code className="font-mono">{pwmName}</code> in the reference set.
            </p>
          )}
        </div>
      </section>

      <section className="mt-8 card">
        {scatterPending && <p className="text-muted text-sm">Loading activity data…</p>}
        {scatterError && (
          <p className="text-sm text-charcoal-82">{String(scatterError)}</p>
        )}
        {scatter && matchingRows.length === 0 && (
          <div>
            <h2 className="text-card-title font-semibold">Activity distribution</h2>
            <p className="mt-2 text-sm text-charcoal-82">
              No selective enhancers in <code className="font-mono">{project}</code>{" "}
              use this PWM (
              {allRowsForPwm.length.toLocaleString()} total promoters with this PWM,
              none above the selectivity threshold).
            </p>
          </div>
        )}
        {scatter && matchingRows.length > 0 && (
          <PwmHistogram
            rows={matchingRows}
            metric={metric}
            onMetricChange={setMetric}
            pwmName={pwmName}
          />
        )}
      </section>
    </div>
  );
}
