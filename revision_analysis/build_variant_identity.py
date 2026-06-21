#!/usr/bin/env python
"""Build the app's variant-identity lookup from the per-project identity scans.

The TF-identity *call* is context-independent (pure sequence vs motif), so it is
stored once. Functional corroboration is context-specific, so it is stored per
project. Confidence is the sequence-based tier (decoupled from corroboration,
which is now shown per project in the app).

Inputs : identity_scan_full.csv (ovca), identity_scan_tcell.csv (tcell)
Output : dashboard/backend/library/variant_identity.csv  (keyed by seq)
"""
import pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BONF = 0.05 / 6012

def seq_confidence(row):
    """Sequence-only confidence tier (no functional corroboration)."""
    pmin = min(row.p_ownfam, row.p_otherfam)
    if row.call == "retained":
        return "high" if row.p_ownfam < BONF else ("low" if row.len <= 6 else "med")
    if row.call in ("switched", "dual"):
        return "high" if pmin < BONF else "med"   # both p-values are already < 1e-4
    return "low" if row.len <= 6 else "med"        # lost / ambiguous

ov = pd.read_csv(HERE / "identity_scan_full.csv").drop_duplicates("seq")
tc = pd.read_csv(HERE / "identity_scan_tcell.csv").drop_duplicates("seq").set_index("seq")

# activity-quantified rows (ovarian cancer is the superset screen; T-cell a subset)
quant = pd.DataFrame({
    "seq": ov.seq,
    "assigned_tf": ov.tf,
    "call": ov.call,
    "dual_kind": ov.dual_kind,
    "other_tf": ov.other_tf,
    "p_ownfam": ov.p_ownfam,
    "p_otherfam": ov.p_otherfam,
    "margin": ov.margin,
    "confidence": ov.apply(seq_confidence, axis=1),
    "ovca_in": True,
    "ovca_corroborated": ov.functionally_corroborated.astype(bool),
    "tcell_in": ov.seq.isin(tc.index),
    "tcell_corroborated": ov.seq.map(
        lambda s: bool(tc.loc[s, "functionally_corroborated"]) if s in tc.index else False
    ),
})

# library coverage rows — sequences not in either activity screen (sequence call
# only; functional corroboration not available → marked not-scanned in both).
cov_path = HERE / "identity_scan_coverage.csv"
frames = [quant]
if cov_path.exists():
    cov = pd.read_csv(cov_path).drop_duplicates("seq")
    cov = cov[~cov.seq.isin(set(quant.seq))]
    coverage = pd.DataFrame({
        "seq": cov.seq,
        "assigned_tf": cov.tf,
        "call": cov.call,
        "dual_kind": cov.dual_kind,
        "other_tf": cov.other_tf,
        "p_ownfam": cov.p_ownfam,
        "p_otherfam": cov.p_otherfam,
        "margin": cov.margin,
        "confidence": cov.apply(seq_confidence, axis=1),
        "ovca_in": False, "ovca_corroborated": False,
        "tcell_in": False, "tcell_corroborated": False,
    })
    frames.append(coverage)

out = pd.concat(frames, ignore_index=True)
dest = ROOT / "dashboard" / "backend" / "library" / "variant_identity.csv"
out.to_csv(dest, index=False)
print(f"wrote {dest}  ({len(out)} rows: {len(quant)} activity-quantified + {len(out)-len(quant)} coverage)")
print("confidence:", out.confidence.value_counts().to_dict())
print("calls:", out.call.value_counts().to_dict())
print("ovca corroborated:", int(out.ovca_corroborated.sum()),
      " tcell scanned:", int(out.tcell_in.sum()),
      " tcell corroborated:", int(out.tcell_corroborated.sum()))
sw = out[out.call.isin(["switched", "dual"])]
disagree = sw[sw.tcell_in & (sw.ovca_corroborated != sw.tcell_corroborated)]
print(f"switch/dual scanned in both, corroboration DIFFERS by context: {len(disagree)}")
