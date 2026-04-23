/** PRD §14.3 seed glossary, rendered as a static page. */
const TERMS: { term: string; def: string }[] = [
  { term: "TREND", def: "Transcription-Factor-Responsive Enhancer Discovery — the platform." },
  { term: "Lib4", def: "The current designed enhancer library." },
  {
    term: "Construct",
    def: "One designed library member (TF binding site + variable region + barcode + flanks).",
  },
  { term: "Barcode", def: "20-bp identifier sequence used to count construct abundance." },
  { term: "UMI", def: "Unique Molecular Identifier; collapsed to remove PCR duplicates." },
  { term: "RPM", def: "Reads Per Million; normalization for sequencing depth." },
  {
    term: "RD ratio",
    def: "RNA-to-DNA reads, normalized; the per-construct activity readout.",
  },
  {
    term: "Sample role",
    def: "Whether a sample is the DNA (input) or RNA (output) measurement.",
  },
  {
    term: "DNA threshold",
    def: "Minimum DNA abundance below which a construct is excluded.",
  },
  {
    term: "Promoter-level score",
    def: "Median RD ratio across the barcodes that share a promoter.",
  },
];

export default function Glossary() {
  return (
    <div className="mx-auto max-w-[1200px] px-6 py-16">
      <h1 className="text-display-section font-semibold tracking-tight">Glossary</h1>
      <p className="mt-4 max-w-2xl text-muted">
        Definitions for terms used throughout the interface. The same definitions
        appear as tooltips on column headers.
      </p>

      <dl className="mt-12 divide-y divide-cream-border">
        {TERMS.map((t) => (
          <div key={t.term} className="py-5 grid grid-cols-1 md:grid-cols-[12rem_1fr] gap-2">
            <dt className="font-semibold text-charcoal">{t.term}</dt>
            <dd className="text-charcoal-82">{t.def}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
