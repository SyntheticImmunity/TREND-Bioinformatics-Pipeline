"""Zoom into the TOP tumor-specific enhancers: does 'consensus is not enough'
get MORE important at the top, what mechanism dominates there, and is there a
'Goldilocks' affinity (no universal optimum -> justifies a diverse library)?"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(r"C:\Dev\TREND_bioinformatics_pipeline\revision_analysis"); FIGS = OUT/"figs"
ACT_PC, ACT_FLOOR = 0.01, 0.1
OV8, IOSE = "mean_OV8_RD_ratio", "mean_IOSE_RD_ratio"
CENTER = -0.19  # empirical neutral center (log2), from pass 1

df = pd.read_csv(OUT/"per_variant_ovca.csv")
df = df.dropna(subset=["rel_affinity", OV8, IOSE]).copy()

# consensus = highest-affinity surviving variant per PWM
cons_idx = df.groupby("pwm_key")["rel_affinity"].idxmax()
cons = df.loc[cons_idx].set_index("pwm_key")
df["cons_OV8"]  = df["pwm_key"].map(cons[OV8]);  df["cons_IOSE"] = df["pwm_key"].map(cons[IOSE])
df["cons_prom"] = df["pwm_key"].map(cons["promoter_name"])
df["is_consensus"] = df["promoter_name"] == df["cons_prom"]
df["dT"] = np.log2((df[OV8]+ACT_PC)/(df["cons_OV8"]+ACT_PC))
df["dN"] = np.log2((df[IOSE]+ACT_PC)/(df["cons_IOSE"]+ACT_PC))

# ---- (Q1/Q2) zoom into top tumor-specific ENHANCERS by specificity percentile
df = df.sort_values("log2ratio", ascending=False)
N = len(df)
print(f"expressed enhancers: {N}   (empirical center log2={CENTER})")
for pct, lab in [(100,"all"),(10,"top 10%"),(5,"top 5%"),(1,"top 1%")]:
    top = df.head(int(N*pct/100))
    nonc = (~top["is_consensus"]).mean()
    # mechanism among these top enhancers (vs their own PWM consensus)
    g = top[top["log2ratio"] > CENTER]  # tumor-side only
    def buck(r):
        if r["dT"]>=0.5 and r["dN"]<=-0.5: return "divergent(both)"
        if r["dT"]>=0.5: return "tumor-gain"
        if r["dN"]<=-0.5: return "normal-suppress"
        return "small"
    bm = g.apply(buck, axis=1).value_counts(normalize=True).mul(100).round(0).to_dict()
    print(f"\n{lab:8s} (n={len(top)}): non-consensus = {100*nonc:.0f}%   "
          f"median dT={top['dT'].median():+.2f} ({2**top['dT'].median():.2f}x)  "
          f"median dN={top['dN'].median():+.2f} ({2**top['dN'].median():.2f}x)")
    print(f"          mechanism mix: {bm}")

# ---- (Q3) Goldilocks: where does each PWM's MOST-specific variant sit in affinity?
rows=[]
for k,gp in df.groupby("pwm_key"):
    gp = gp[gp[OV8] >= ACT_FLOOR]
    if len(gp) < 4: continue
    best = gp.loc[gp["log2ratio"].idxmax()]
    # affinity percentile of the best-specific variant WITHIN this PWM (0=lowest,100=highest aff)
    pctile = 100*(gp["rel_affinity"] < best["rel_affinity"]).mean()
    rows.append(pctile)
g = pd.Series(rows)
print(f"\n=== Goldilocks (n={len(g)} PWMs >=4 variants) ===")
print(f"affinity-percentile of the MOST tumor-specific variant within its PWM:")
print(f"  lowest-affinity is best:  {(g<=20).mean()*100:.0f}% of PWMs")
print(f"  intermediate (20-80):     {((g>20)&(g<80)).mean()*100:.0f}% of PWMs")
print(f"  highest-affinity is best: {(g>=80).mean()*100:.0f}% of PWMs")
print(f"  => most-specific variant is NOT the lowest-affinity one in {(g>20).mean()*100:.0f}% of PWMs")

# ---- figures
# Fig5: Goldilocks histogram
fig,a = plt.subplots(figsize=(6,3.2))
a.hist(g, bins=20, color="#8250df")
a.set_xlabel("affinity rank of the MOST-specific variant within its PWM\n(0 = weakest motif match, 100 = consensus)")
a.set_ylabel("PWMs"); a.set_title("No universal 'best' affinity -> a diverse library is required")
fig.savefig(FIGS/"fig5_goldilocks.png", dpi=130, bbox_inches="tight")

# Fig6: specificity vs affinity density (all variants) — show no monotonic ridge
fig,a = plt.subplots(figsize=(6,4))
hb = a.hexbin(df["rel_affinity"], df["log2ratio"], gridsize=45, bins="log", cmap="viridis")
a.axhline(CENTER, color="white", ls=":", lw=1)
a.set_xlabel("relative affinity (1 = consensus motif)"); a.set_ylabel("specificity  log2(OV8/IOSE)")
a.set_title("Specificity vs affinity — no clear ridge (Goldilocks varies by PWM)")
fig.colorbar(hb, label="variants (log)")
fig.savefig(FIGS/"fig6_specificity_vs_affinity.png", dpi=130, bbox_inches="tight")
print(f"\nwrote fig5, fig6 to {FIGS}")
