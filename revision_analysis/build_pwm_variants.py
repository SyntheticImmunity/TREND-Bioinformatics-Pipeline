#!/usr/bin/env python
"""Build the per-PWM variant table that powers the dashboard decomposition panel.

One row per quantified variant, per project, with the activity pair + relative
affinity needed to draw a motif's variant cloud and identify its consensus
(highest-affinity) and best (most target-selective) variant. PWM names are
normalized to the dashboard's key (first alias, trailing _vN stripped).

Output: dashboard/backend/library/pwm_variants.csv
"""
import re
import pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SUF = re.compile(r"_v\d+$")
def norm(x): return SUF.sub("", str(x).split()[0])

SRC = [
    ("ovarian_cancer", HERE / "standalone" / "trend_ovca_variants.csv", "ov8", "iose"),
    ("T_cell_activation", HERE / "standalone_tcell" / "trend_tcell_variants.csv", "stim", "rest"),
]

frames = []
for project, path, exp, ctrl in SRC:
    if not path.exists():
        print(f"skip {project}: {path} missing"); continue
    d = pd.read_csv(path)
    frames.append(pd.DataFrame({
        "project": project,
        "pwm": d.pwm.map(norm),
        "tf": d.tf,
        "promoter": d.promoter,
        "exp": d[exp].round(4),
        "ctrl": d[ctrl].round(4),
        "affinity": d.rel_affinity.round(4),
        "log2r": d.log2r.round(4),
    }))

out = pd.concat(frames, ignore_index=True)
dest = ROOT / "dashboard" / "backend" / "library" / "pwm_variants.csv"
out.to_csv(dest, index=False)
print(f"wrote {dest}  ({len(out)} rows, {out.pwm.nunique()} PWMs, projects={list(out.project.unique())})")
