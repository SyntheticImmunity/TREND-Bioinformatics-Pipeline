interface SummaryCardProps {
  label: string;
  value: string;
  hint?: string;
}

export function SummaryCard({ label, value, hint }: SummaryCardProps) {
  return (
    <div className="card">
      <div className="text-sm text-muted">{label}</div>
      <div className="mt-3 text-display-sub font-semibold text-charcoal tabular-nums">
        {value}
      </div>
      {hint && <div className="mt-2 text-xs text-muted">{hint}</div>}
    </div>
  );
}
