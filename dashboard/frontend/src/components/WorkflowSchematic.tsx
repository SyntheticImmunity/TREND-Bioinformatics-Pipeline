/**
 * Panel A of Figure 1: TREND workflow schematic.
 *
 * Three numbered steps from the manuscript:
 *   1. Library design — PPMs/PWMs → consensus + 9 variants (10 sequences total) → arrayed library
 *   2. Cellular delivery — pooled lentivirus into target cells
 *   3. Activity quantification — barcode-linked RNA / DNA via targeted NGS
 *
 * Rendered as a 3-card horizontal flow on desktop, stacked on mobile.
 */
import { Link } from "react-router-dom";

interface Step {
  index: number;
  title: string;
  body: string;
  highlight: string;
}

const STEPS: Step[] = [
  {
    index: 1,
    title: "Library design",
    body:
      "PPMs and PWMs from 1,068 proteins with annotated DNA-binding motifs across 14 databases generate consensus sequences plus nine high-probability variants per matrix. Each sequence is arrayed in tandem upstream of an adenoviral minimal promoter, linked to a unique DNA barcode, and packaged into a pooled lentiviral library.",
    highlight: "1,068 TFs · 14 databases · 10 sequences / matrix",
  },
  {
    index: 2,
    title: "Cellular delivery",
    body:
      "The pooled library is delivered into target cells. Each cell integrates one barcoded enhancer-reporter; barcode abundance in genomic DNA reports library representation, while barcode abundance in RNA reports enhancer activity in that cell context.",
    highlight: "Pooled lentivirus · multiple cell contexts",
  },
  {
    index: 3,
    title: "Activity quantification",
    body:
      "Targeted NGS reads barcode-linked RNA and DNA in parallel. Per-construct activity is the RNA / DNA ratio; cross-condition specificity comes from comparing those ratios across cell types or treatments.",
    highlight: "RNA / DNA ratios · per-construct activity & specificity",
  },
];

export function WorkflowSchematic() {
  return (
    <div className="grid gap-6 md:grid-cols-3 relative">
      {STEPS.map((s, i) => (
        <article
          key={s.index}
          className="card flex flex-col"
        >
          <div className="flex items-baseline gap-3">
            <span className="text-display-sub font-semibold text-charcoal-40 tabular-nums">
              {String(s.index).padStart(2, "0")}
            </span>
            <h3 className="text-card-title font-semibold">{s.title}</h3>
          </div>
          <p className="mt-3 text-sm text-charcoal-82 flex-1">{s.body}</p>
          <p className="mt-4 text-xs text-muted">{s.highlight}</p>
          {i < STEPS.length - 1 && (
            <span
              aria-hidden
              className="hidden md:block absolute top-1/2 -translate-x-1/2 -translate-y-1/2 text-charcoal-40 text-xl font-light pointer-events-none"
              style={{
                // Center of the gap between cards i and i+1 in a gap-6 (1.5rem)
                // grid: (i+1) card-widths + (i + 0.5) gap-widths from the left,
                // where card_width = (100% - (N-1)*1.5rem) / N. translate-x-1/2
                // then centers the rendered span on that point.
                left: `calc(${i + 1} * (100% - ${(STEPS.length - 1) * 1.5}rem) / ${STEPS.length} + ${(i + 0.5) * 1.5}rem)`,
              }}
            >
              →
            </span>
          )}
        </article>
      ))}
      <div className="md:col-span-3 mt-2 text-sm text-muted">
        See the <Link to="/run" className="text-charcoal">pipeline page</Link> for the
        full nine-step computational workflow that runs after sequencing.
      </div>
    </div>
  );
}
