#!/usr/bin/env python
"""Coverage scan — give EVERY library construct a TF-identity call.

The activity-quantified standalone tables cover 37,832 of the library's 54,193
distinct binding sites; the rest were filtered out before activity analysis and
so have no identity card in the app. This script runs the *same* sequence-based
classifier (imported from identity_scan_full) on those remaining sequences,
pulling their assigned TF / PWM straight from the construct library DB.

These sequences are not in either activity screen, so functional corroboration
is not available for them — they get the sequence call only (the app marks
corroboration "not measured"). Output: identity_scan_coverage.csv.
"""
import sqlite3, time, sys
import pandas as pd
from pathlib import Path

import identity_scan_full as M   # reuses the exact scorer; no full scan on import

ROOT = Path(r"C:\Dev\TREND_bioinformatics_pipeline")
OUT = ROOT / "revision_analysis"
DB = ROOT / "dashboard" / "backend" / "state" / "library.sqlite"
COVERED = OUT.parent / "dashboard" / "backend" / "library" / "variant_identity.csv"

# sequences already covered by the activity scans
done = set(pd.read_csv(COVERED)["seq"].astype(str))

# distinct (TFBS, TF, by_ppm_name) from the construct library, minus the covered ones
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
rows = con.execute(
    "SELECT TFBS, TF, by_ppm_name FROM constructs GROUP BY TFBS"
).fetchall()
todo = [r for r in rows if str(r["TFBS"]) not in done]
print(f"library distinct TFBS: {len(rows)}   already covered: {len(rows)-len(todo)}   to scan: {len(todo)}")

recs = []; t0 = time.time()
for n, r in enumerate(todo):
    seq = str(r["TFBS"])
    c = M.classify_sequence(seq, r["by_ppm_name"], r["TF"])
    recs.append(dict(tf=r["TF"], assigned=c["aname"], seq=seq, len=c["length"],
                     call=c["call"], dual_kind=c["dual_kind"], other_tf=c["other_tf"],
                     p_ownfam=c["p_ownfam"], p_otherfam=c["p_otherfam"],
                     margin=round(c["margin"], 2)))
    if (n + 1) % 2000 == 0:
        dt = time.time() - t0
        print(f"  {n+1}/{len(todo)}  ({dt:.0f}s, {1000*dt/(n+1):.1f} ms/seq)")

res = pd.DataFrame(recs)
res.to_csv(OUT / "identity_scan_coverage.csv", index=False)
print(f"\nscanned {len(res)} sequences in {time.time()-t0:.0f}s -> identity_scan_coverage.csv")
print("\n=== call distribution (coverage set) ===")
print(res.call.value_counts().to_string())
