"""Rebuilt figures per user feedback:
  fig1b  per-PWM small multiples (variant cloud: tumor vs normal), top performers
  fig3b  tiered slopegraph (consensus->best) sharpening as we focus on the best
  fig5b  Goldilocks histogram with gap-free bins, colored by affinity tier
  fig6b  specificity-vs-affinity density with a clear colorbar + median trend line
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT=Path(r"C:\Dev\TREND_bioinformatics_pipeline\revision_analysis"); FIGS=OUT/"figs"
OV8,IOSE="mean_OV8_RD_ratio","mean_IOSE_RD_ratio"; pc,floor=0.01,0.1; CENTER=-0.19
df=pd.read_csv(OUT/"per_variant_ovca.csv").dropna(subset=["rel_affinity",OV8,IOSE])

# per-PWM consensus (max affinity) and best-specific (max ratio, OV8>=floor)
summ=[]
for k,g in df.groupby("pwm_key"):
    cons=g.loc[g["rel_affinity"].idxmax()]; elig=g[g[OV8]>=floor]
    if elig.empty: continue
    best=elig.loc[elig["log2ratio"].idxmax()]
    summ.append(dict(pwm=k, tf=str(cons["TF_name_human_curated"]), nvar=len(g),
        cons_OV8=cons[OV8],cons_IOSE=cons[IOSE],best_OV8=best[OV8],best_IOSE=best[IOSE],
        best_spec=best["log2ratio"], cons_prom=cons["promoter_name"], best_prom=best["promoter_name"]))
S=pd.DataFrame(summ).sort_values("best_spec",ascending=False).reset_index(drop=True)

# ---------- fig1b: small multiples of top PWMs -----------------------------
top=S[S.nvar>=8].head(12)
fig,axs=plt.subplots(3,4,figsize=(13,9.5)); axs=axs.ravel()
for ax,(_,row) in zip(axs, top.iterrows()):
    gp=df[df.pwm_key==row.pwm]
    sc=ax.scatter(gp[OV8]+pc, gp[IOSE]+pc, c=gp["rel_affinity"], cmap="viridis",
                  s=55, edgecolors="k", linewidths=.4, vmin=0, vmax=1, zorder=3)
    cons=gp[gp.promoter_name==row.cons_prom]; best=gp[gp.promoter_name==row.best_prom]
    ax.scatter(cons[OV8]+pc,cons[IOSE]+pc,marker="s",s=170,facecolors="none",edgecolors="black",linewidths=1.8,zorder=4,label="consensus")
    ax.scatter(best[OV8]+pc,best[IOSE]+pc,marker="*",s=330,facecolors="none",edgecolors="crimson",linewidths=1.8,zorder=5,label="most specific")
    lo=min(gp[OV8].min(),gp[IOSE].min())+pc; hi=max(gp[OV8].max(),gp[IOSE].max())+pc
    ax.plot([lo,hi],[lo,hi],"--",color="gray",lw=1)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_title(f"{row.tf}  ({2**row.best_spec:.1f}x)",fontsize=10)
    ax.set_xlabel("OV8 (tumor)",fontsize=8); ax.set_ylabel("IOSE (normal)",fontsize=8)
axs[0].legend(fontsize=8,loc="upper left")
fig.suptitle("Per-PWM variant clouds — top tumor-specific performers\n"
             "(color = motif affinity; below the diagonal = tumor-specific)",fontsize=13)
fig.tight_layout(rect=[0,0,1,.95]); fig.savefig(FIGS/"fig1b_per_pwm_panels.png",dpi=120,bbox_inches="tight")

# ---------- fig3b: tiered slopegraph ---------------------------------------
tiers=[(0.1,"top 0.1%"),(1,"top 1%"),(5,"top 5%"),(10,"top 10%"),(100,"all PWMs")]
fig,axs=plt.subplots(1,len(tiers),figsize=(14,3.6),sharey=True)
for ax,(p,lab) in zip(axs,tiers):
    s=S.head(max(2,int(len(S)*p/100)))
    for cT,bT,color,name in [(s.cons_OV8.median(),s.best_OV8.median(),"#cf222e","tumor (OV8)"),
                             (s.cons_IOSE.median(),s.best_IOSE.median(),"#1f6feb","normal (IOSE)")]:
        ax.plot([0,1],[cT,bT],"-o",color=color,lw=2.4,label=name)
        ax.annotate(f"{cT:.2f}",(0,cT),textcoords="offset points",xytext=(-4,4),ha="right",fontsize=7,color=color)
        ax.annotate(f"{bT:.2f}",(1,bT),textcoords="offset points",xytext=(4,4),ha="left",fontsize=7,color=color)
    ax.set_xticks([0,1]); ax.set_xticklabels(["consensus","best"],fontsize=8)
    ax.set_title(f"{lab}\n(n={len(s)})",fontsize=9); ax.set_xlim(-.4,1.4)
axs[0].set_ylabel("median activity (RD ratio)"); axs[0].legend(fontsize=8,loc="center left")
fig.suptitle("Activity shift consensus → most-specific variant, sharpening toward the best enhancers",fontsize=12)
fig.tight_layout(rect=[0,0,1,.93]); fig.savefig(FIGS/"fig3b_tiered_slopegraph.png",dpi=130,bbox_inches="tight")

# ---------- fig5b: gap-free Goldilocks, colored by affinity tier -----------
pcts=[]
for k,g in df.groupby("pwm_key"):
    g=g[g[OV8]>=floor]
    if len(g)<4: continue
    b=g.loc[g["log2ratio"].idxmax()]
    pcts.append(100*(g["rel_affinity"]<b["rel_affinity"]).mean())
pcts=np.array(pcts)
edges=np.arange(0,101,10); centers=(edges[:-1]+edges[1:])/2
counts,_=np.histogram(pcts,bins=edges)
colors=["#cf222e" if c<20 else ("#2da44e" if c>=80 else "#8b949e") for c in centers]
fig,ax=plt.subplots(figsize=(7,3.4))
ax.bar(centers,counts,width=9,color=colors)
ax.set_xlabel("affinity rank of the MOST-specific variant within its PWM\n(0 = weakest motif match · 100 = consensus)")
ax.set_ylabel("PWMs")
ax.set_title("Where the best variant sits in affinity — no universal optimum")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color="#cf222e",label=f"weakest 20%  ({(pcts<20).mean()*100:.0f}%)"),
                   Patch(color="#8b949e",label=f"middle  ({((pcts>=20)&(pcts<80)).mean()*100:.0f}%)"),
                   Patch(color="#2da44e",label=f"near-consensus 20%  ({(pcts>=80).mean()*100:.0f}%)")],fontsize=8)
fig.savefig(FIGS/"fig5b_goldilocks.png",dpi=130,bbox_inches="tight")

# ---------- fig6b: clearer density + median trend --------------------------
fig,ax=plt.subplots(figsize=(6.6,4.2))
hb=ax.hexbin(df["rel_affinity"],df["log2ratio"],gridsize=40,bins="log",cmap="magma")
# median specificity per affinity bin (the "is there a trend?" line)
b=np.linspace(0,1,21); idx=np.clip(np.digitize(df["rel_affinity"],b)-1,0,19)
med=[np.median(df["log2ratio"][idx==i]) if (idx==i).any() else np.nan for i in range(20)]
ax.plot((b[:-1]+b[1:])/2, med, color="cyan", lw=2, label="median specificity (flat = no trend)")
ax.axhline(CENTER,color="white",ls=":",lw=1)
ax.set_xlabel("relative affinity (1 = consensus motif)"); ax.set_ylabel("specificity  log2(OV8/IOSE)")
ax.set_title("Specificity vs affinity — flat median = affinity does not predict specificity")
ax.legend(fontsize=8,loc="upper right")
cb=fig.colorbar(hb); cb.set_label("number of variants in each hexagon (log scale)")
fig.savefig(FIGS/"fig6b_specificity_vs_affinity.png",dpi=130,bbox_inches="tight")
print("wrote fig1b, fig3b, fig5b, fig6b")
print(f"top performers shown: {list(top.tf)}")
EOF=1
