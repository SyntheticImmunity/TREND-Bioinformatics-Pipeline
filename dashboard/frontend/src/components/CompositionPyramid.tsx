/**
 * Hierarchical decomposition of the 1,068 library TFs.
 *
 * Renders three nested levels as horizontal stacked bars:
 *   Level 0: total (1,068)
 *   Level 1: 729 confirmed TF + 91 Lambert non-TF + 248 not in Lambert
 *   Level 2: sub-categories of each (direct/alias, unlikely/ssDNA, etc.)
 *
 * Pure SVG, no chart library — the proportional segment widths are easy to
 * compute and the brand-coherent color palette comes from the backend.
 */
import type { CompositionBreakdown, CompositionBranch, CompositionLeaf } from "@/lib/api";

interface SegmentProps {
  count: number;
  total: number;
  color: string;
  label: string;
  detailLabel?: string;
}

function fmt(n: number): string {
  return n.toLocaleString("en-US");
}

function Segment({ count, total, color, label, detailLabel }: SegmentProps) {
  const pct = (count / total) * 100;
  const showInline = pct > 18;
  return (
    <div
      className="relative flex items-center px-3 py-3 text-cream-light overflow-hidden"
      style={{ width: `${pct}%`, backgroundColor: color, minWidth: "2.5rem" }}
      title={`${label}: ${fmt(count)} (${pct.toFixed(1)}%)`}
    >
      {showInline ? (
        <div className="text-xs leading-snug">
          <div className="font-semibold">{label}</div>
          {detailLabel && <div className="opacity-80">{detailLabel}</div>}
          <div className="font-mono mt-0.5">
            {fmt(count)} <span className="opacity-70">({pct.toFixed(1)}%)</span>
          </div>
        </div>
      ) : (
        <div className="text-[10px] font-mono">{fmt(count)}</div>
      )}
    </div>
  );
}

interface Props {
  breakdown: CompositionBreakdown;
}

export function CompositionPyramid({ breakdown }: Props) {
  const { total, branches } = breakdown;

  // Flatten level-2 (children) for the second row, keeping the order from level-1.
  const leaves: (CompositionLeaf & { parentLabel: string })[] = [];
  for (const b of branches) {
    if (b.children && b.children.length) {
      for (const ch of b.children) {
        leaves.push({ ...ch, parentLabel: b.label });
      }
    } else {
      leaves.push({ ...b, parentLabel: b.label });
    }
  }

  return (
    <div className="space-y-3">
      {/* Level 0: total */}
      <div className="flex items-center gap-3 text-xs text-muted">
        <span className="w-32 text-right uppercase tracking-wide">Total library</span>
        <div className="flex-1 flex rounded-comfortable overflow-hidden border border-cream-border">
          <Segment count={total} total={total} color="#1c1c1c" label="All library targets" />
        </div>
        <span className="w-16 text-left font-semibold tabular-nums text-charcoal">
          {fmt(total)}
        </span>
      </div>

      {/* Level 1: three branches */}
      <div className="flex items-center gap-3 text-xs text-muted">
        <span className="w-32 text-right uppercase tracking-wide">Source</span>
        <div className="flex-1 flex rounded-comfortable overflow-hidden border border-cream-border">
          {branches.map((b: CompositionBranch) => (
            <Segment
              key={b.label}
              count={b.count}
              total={total}
              color={b.color}
              label={b.label}
            />
          ))}
        </div>
        <span className="w-16" />
      </div>

      {/* Level 2: nested sub-categories */}
      <div className="flex items-center gap-3 text-xs text-muted">
        <span className="w-32 text-right uppercase tracking-wide">Detail</span>
        <div className="flex-1 flex rounded-comfortable overflow-hidden border border-cream-border">
          {leaves.map((l, i) => (
            <Segment
              key={`${l.parentLabel}-${l.label}-${i}`}
              count={l.count}
              total={total}
              color={l.color}
              label={l.label}
            />
          ))}
        </div>
        <span className="w-16" />
      </div>

      {/* Legend with the arithmetic breakdown */}
      <div className="mt-4 grid gap-3 sm:grid-cols-3 text-xs">
        {branches.map((b) => (
          <div key={b.label} className="flex items-start gap-2">
            <span
              className="inline-block w-3 h-3 rounded-sm mt-0.5 shrink-0"
              style={{ backgroundColor: b.color }}
            />
            <div>
              <div className="font-semibold text-charcoal">
                {b.label}{" "}
                <span className="font-mono text-muted">({fmt(b.count)})</span>
              </div>
              {b.children && b.children.length > 1 && (
                <ul className="mt-1 space-y-0.5 text-muted">
                  {b.children.map((c) => (
                    <li key={c.label}>
                      <span className="font-mono text-charcoal-82">{fmt(c.count)}</span> · {c.label}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
