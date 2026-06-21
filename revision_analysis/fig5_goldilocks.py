"""Dedicated regen of fig5b (Goldilocks) only — legend moved OUT of the plot,
labels disambiguated. The '20%' band width and the share-of-PWMs were colliding
in the old label; now the legend states only the share of PWMs, and faint
dividers at the 20/80 affinity boundaries show the band edges on the x-axis."""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

OUT=Path(r"C:\Dev\TREND_bioinformatics_pipeline\revision_analysis"); FIGS=OUT/"figs"
OV8="mean_OV8_RD_ratio"; floor=0.1
df=pd.read_csv(OUT/"per_variant_ovca.csv").dropna(subset=["rel_affinity",OV8,"mean_IOSE_RD_ratio"])

pcts=[]
for k,g in df.groupby("pwm_key"):
    g=g[g[OV8]>=floor]
    if len(g)<4: continue
    pcts.append(100*(g["rel_affinity"] < g.loc[g["log2ratio"].idxmax(),"rel_affinity"]).mean())
pcts=np.array(pcts)
edges=np.arange(0,101,10); centers=(edges[:-1]+edges[1:])/2
counts,_=np.histogram(pcts,bins=edges)
colors=["#cf222e" if c<20 else ("#2da44e" if c>=80 else "#8b949e") for c in centers]
low=(pcts<20).mean()*100; mid=((pcts>=20)&(pcts<80)).mean()*100; high=(pcts>=80).mean()*100

fig,ax=plt.subplots(figsize=(8.4,3.8))
ax.bar(centers,counts,width=9,color=colors,zorder=3)
ax.axvline(20,color="gray",ls=":",lw=1,zorder=2); ax.axvline(80,color="gray",ls=":",lw=1,zorder=2)
ax.set_xlim(0,100); ax.set_xticks(np.arange(0,101,20))
ax.set_xlabel("affinity rank of the most-specific variant within its PWM\n"
              "(0 = weakest motif match   →   100 = consensus)")
ax.set_ylabel("number of PWMs")
ax.set_title("Where the best variant sits in affinity — no universal optimum")
# legend OUTSIDE on the right; each entry states only the share of PWMs
ax.legend(handles=[Patch(color="#cf222e",label=f"low affinity (bottom fifth) — {low:.0f}% of PWMs"),
                   Patch(color="#8b949e",label=f"intermediate — {mid:.0f}% of PWMs"),
                   Patch(color="#2da44e",label=f"near-consensus (top fifth) — {high:.0f}% of PWMs")],
          loc="upper left", bbox_to_anchor=(1.02,1.0), frameon=False, fontsize=9,
          title="best variant's affinity")
fig.savefig(FIGS/"fig5b_goldilocks.png", dpi=130, bbox_inches="tight")
print(f"wrote fig5b_goldilocks.png  | low={low:.0f}% mid={mid:.0f}% high={high:.0f}%")
