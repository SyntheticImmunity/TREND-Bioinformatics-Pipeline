import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  ReferenceLine,
  Tooltip,
} from "recharts";

import { api, type DecompVariant } from "@/lib/api";

const MUTED = "#9a9a98";
const CONSENSUS = "#1f2937";
const BEST = "#d1495b";

function fmtDelta(d: number | null | undefined): string {
  if (d == null) return "—";
  const x = Math.pow(2, d);
  return `${d >= 0 ? "+" : ""}${d.toFixed(2)} log2 (${x.toFixed(2)}×)`;
}

/** Plain-language mechanism, the per-motif version of R1's "variants tune
 *  activity in the target cell, not specificity" question. */
function mechanism(dExp: number, dCtrl: number, expL: string, ctrlL: string): string {
  const up = dExp >= 0.5, downCtrl = dCtrl <= -0.5, expFlat = Math.abs(dExp) < 0.5;
  if (downCtrl && expFlat)
    return `selectivity is gained by suppressing ${ctrlL} activity — ${expL} activity barely changes.`;
  if (up && Math.abs(dCtrl) < 0.5)
    return `selectivity is gained by raising ${expL} activity, with ${ctrlL} roughly unchanged.`;
  if (up && downCtrl)
    return `selectivity is gained on both axes — ${expL} up and ${ctrlL} down.`;
  return `the consensus→best shift is modest on both axes.`;
}

export function VariantDecomposition({ pwm, project }: { pwm: string; project: string }) {
  const { data, isPending } = useQuery({
    queryKey: ["pwm-decomposition", pwm, project],
    queryFn: () => api.pwmDecomposition(pwm, project),
    retry: false,
  });

  const domainMax = useMemo(() => {
    if (!data?.available || !data.variants?.length) return 1;
    const m = Math.max(...data.variants.flatMap((v) => [v.exp, v.ctrl]));
    return Math.ceil(m * 1.05 * 10) / 10;
  }, [data]);

  // Self-contained section: renders nothing until its own (fast) endpoint
  // resolves, so it never waits on the page's slower scatter fetch.
  if (isPending || !data?.available) return null;

  const expL = data.exp_label ?? "Target";
  const ctrlL = data.ctrl_label ?? "Control";
  const consensus = data.consensus ? [data.consensus] : [];
  const best = data.best ? [data.best] : [];
  // de-emphasise consensus/best in the muted cloud so the markers read clearly
  const others = (data.variants ?? []).filter(
    (v) => v.promoter !== data.consensus?.promoter && v.promoter !== data.best?.promoter,
  );

  const tip = (v: DecompVariant, role: string) => (
    <div className="rounded-comfortable border border-cream-border bg-cream-light px-3 py-2 text-xs text-charcoal-82">
      {role && <div className="font-semibold text-charcoal mb-0.5">{role}</div>}
      <div className="font-mono text-[11px] text-muted mb-1">{v.promoter}</div>
      <div>{expL}: <span className="text-charcoal">{v.exp.toFixed(2)}</span></div>
      <div>{ctrlL}: <span className="text-charcoal">{v.ctrl.toFixed(2)}</span></div>
      <div>selectivity: <span className="text-charcoal">{Math.pow(2, v.log2r).toFixed(1)}×</span></div>
      <div>motif affinity: <span className="text-charcoal">{v.affinity.toFixed(2)}</span></div>
    </div>
  );

  return (
    <section className="mt-8 card">
      <h2 className="text-card-title font-semibold">Variant decomposition</h2>
      <p className="mt-1 mb-6 text-sm text-muted">
        Every variant of this motif in target-vs-control activity space. The shift from
        the consensus (highest-affinity) to the most selective variant shows <em>where</em>{" "}
        the selectivity gain comes from — raising target activity, suppressing control
        activity, or both.
      </p>
      <div className="h-[380px] w-full max-w-[460px]">
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 8, right: 16, bottom: 36, left: 8 }}>
            <XAxis
              type="number" dataKey="exp" domain={[0, domainMax]}
              tick={{ fill: "#5f5f5d", fontSize: 11 }}
              label={{ value: `${expL} activity (RD ratio)`, position: "insideBottom", offset: -20, fill: "#5f5f5d", fontSize: 12 }}
            />
            <YAxis
              type="number" dataKey="ctrl" domain={[0, domainMax]}
              tick={{ fill: "#5f5f5d", fontSize: 11 }}
              label={{ value: `${ctrlL} activity`, angle: -90, position: "insideLeft", offset: 16, fill: "#5f5f5d", fontSize: 12 }}
            />
            <ZAxis range={[36, 36]} />
            {/* y = x : equal activity = no selectivity; points below are target-selective */}
            <ReferenceLine
              segment={[{ x: 0, y: 0 }, { x: domainMax, y: domainMax }]}
              stroke="#b9b9b6" strokeDasharray="4 4" ifOverflow="hidden"
            />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const p = payload[0].payload as DecompVariant & { _role?: string };
                return tip(p, p._role ?? "");
              }}
            />
            <Scatter data={others} fill={MUTED} fillOpacity={0.55} isAnimationActive={false} />
            <Scatter
              data={consensus.map((v) => ({ ...v, _role: "Consensus (highest affinity)" }))}
              fill="none" stroke={CONSENSUS} strokeWidth={2} shape="circle" isAnimationActive={false}
            />
            <Scatter
              data={best.map((v) => ({ ...v, _role: "Best (most selective)" }))}
              fill={BEST} shape="star" isAnimationActive={false}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-muted">
        <span><span className="inline-block w-2.5 h-2.5 rounded-full align-middle mr-1" style={{ background: MUTED }} /> variant</span>
        <span><span className="inline-block w-2.5 h-2.5 rounded-full align-middle mr-1 border-2" style={{ borderColor: CONSENSUS }} /> consensus</span>
        <span><span className="align-middle mr-1" style={{ color: BEST }}>★</span> most selective</span>
        <span>dashed = equal activity (below it = {expL}-selective)</span>
      </div>

      {data.best && data.d_exp != null && data.d_ctrl != null && (
        <div className="mt-4 rounded-comfortable border border-cream-border bg-cream-light p-4 text-xs">
          <div className="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-[14rem_1fr]">
            <span className="text-muted">Selectivity gain (consensus→best)</span>
            <span className="tabular-nums text-charcoal font-semibold">{data.gain}×</span>
            <span className="text-muted">Δ {expL} activity</span>
            <span className="tabular-nums text-charcoal">{fmtDelta(data.d_exp)}</span>
            <span className="text-muted">Δ {ctrlL} activity</span>
            <span className="tabular-nums text-charcoal">{fmtDelta(data.d_ctrl)}</span>
          </div>
          <p className="mt-3 text-charcoal-82">
            For this motif, {mechanism(data.d_exp, data.d_ctrl, expL, ctrlL)}
          </p>
        </div>
      )}
    </section>
  );
}
