"""Round-2 figure fixes:
  fig1b  per-PWM panels with CLEAN log ticks + single shared legend
  fig1c  the Dtumor-vs-Dnormal decomposition scatter, FACETED by 6 top tiers
  fig3b  tiered slopegraph with 6 tiers and labels kept inside the axes
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter, LogLocator
from matplotlib.lines import Line2D

OUT=Path(r"C:\Dev\TREND_bioinformatics_pipeline\revision_analysis"); FIGS=OUT/"figs"
OV8,IOSE="mean_OV8_RD_ratio","mean_IOSE_RD_ratio"; pc,floor=0.01,0.1
df=pd.read_csv(OUT/"per_variant_ovca.csv").dropna(subset=["rel_affinity",OV8,IOSE])

summ=[]
for k,g in df.groupby("pwm_key"):
    cons=g.loc[g["rel_affinity"].idxmax()]; elig=g[g[OV8]>=floor]
    if elig.empty: continue
    best=elig.loc[elig["log2ratio"].idxmax()]
    summ.append(dict(pwm=k, tf=str(cons["TF_name_human_curated"]), nvar=len(g),
        cons_OV8=cons[OV8],cons_IOSE=cons[IOSE],best_OV8=best[OV8],best_IOSE=best[IOSE],
        dT=np.log2((best[OV8]+pc)/(cons[OV8]+pc)), dN=np.log2((best[IOSE]+pc)/(cons[IOSE]+pc)),
        best_spec=best["log2ratio"], cons_prom=cons["promoter_name"], best_prom=best["promoter_name"]))
S=pd.DataFrame(summ).sort_values("best_spec",ascending=False).reset_index(drop=True)
TIERS=[(0.1,"top 0.1%"),(1,"top 1%"),(5,"top 5%"),(10,"top 10%"),(20,"top 20%"),(40,"top 40%")]

# ---------- fig1b: per-PWM panels, clean ticks + shared legend -------------
top=S[S.nvar>=8].head(12)
fig,axs=plt.subplots(3,4,figsize=(14,10)); axs=axs.ravel()
for i,(ax,(_,row)) in enumerate(zip(axs, top.iterrows())):
    gp=df[df.pwm_key==row.pwm]
    ax.scatter(gp[OV8]+pc, gp[IOSE]+pc, c=gp["rel_affinity"], cmap="viridis",
               s=60, edgecolors="k", linewidths=.4, vmin=0, vmax=1, zorder=3)
    cons=gp[gp.promoter_name==row.cons_prom]; best=gp[gp.promoter_name==row.best_prom]
    ax.scatter(cons[OV8]+pc,cons[IOSE]+pc,marker="s",s=180,facecolors="none",edgecolors="black",linewidths=1.8,zorder=4)
    ax.scatter(best[OV8]+pc,best[IOSE]+pc,marker="*",s=340,facecolors="none",edgecolors="crimson",linewidths=1.8,zorder=5)
    lo=min(gp[OV8].min(),gp[IOSE].min())+pc; hi=max(gp[OV8].max(),gp[IOSE].max())+pc
    ax.plot([lo,hi],[lo,hi],"--",color="gray",lw=1)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.xaxis.set_minor_formatter(NullFormatter()); ax.yaxis.set_minor_formatter(NullFormatter())
    ax.xaxis.set_major_locator(LogLocator(base=10,numticks=4)); ax.yaxis.set_major_locator(LogLocator(base=10,numticks=4))
    ax.set_title(f"{row.tf}  ({2**row.best_spec:.1f}x)",fontsize=11)
    if i % 4 == 0: ax.set_ylabel("IOSE (normal)",fontsize=9)
    if i // 4 == 2: ax.set_xlabel("OV8 (tumor)",fontsize=9)
leg=[Line2D([0],[0],marker="s",color="none",markeredgecolor="black",markersize=12,label="consensus (highest affinity)"),
     Line2D([0],[0],marker="*",color="none",markeredgecolor="crimson",markersize=16,label="most-specific variant"),
     Line2D([0],[0],ls="--",color="gray",label="diagonal = equal in both (no specificity)")]
fig.legend(handles=leg,loc="upper center",ncol=3,fontsize=10,frameon=False,bbox_to_anchor=(.5,.99))
fig.suptitle("Per-PWM variant clouds — top tumor-specific performers   "
             "(point color = motif affinity; below diagonal = tumor-specific)",fontsize=12,y=1.015)
fig.tight_layout(rect=[0,0,1,.96]); fig.savefig(FIGS/"fig1b_per_pwm_panels.png",dpi=120,bbox_inches="tight")

# ---------- fig1c: decomposition scatter faceted by tier -------------------
fig,axs=plt.subplots(2,3,figsize=(13,8.2)); axs=axs.ravel()
L=3.2
for ax,(p,lab) in zip(axs,TIERS):
    s=S.head(max(3,int(len(S)*p/100)))
    ax.scatter(s.dT.clip(-L,L), s.dN.clip(-L,L), s=14, alpha=.45, c="#1f6feb", edgecolors="none")
    ax.plot([-L,L],[-L,L],"--",color="k",lw=1)
    ax.axhline(0,color="gray",lw=.6); ax.axvline(0,color="gray",lw=.6)
    ax.set_xlim(-L,L); ax.set_ylim(-L,L); ax.set_aspect("equal")
    ax.set_title(f"{lab}  (n={len(s)})",fontsize=10)
    ax.set_xlabel("Δ tumor (log2, best−consensus)",fontsize=8)
    ax.set_ylabel("Δ normal (log2, best−consensus)",fontsize=8)
    ax.text(.04,.06,f"med Δtumor {s.dT.median():+.2f}\nmed Δnormal {s.dN.median():+.2f}",
            transform=ax.transAxes,fontsize=8,va="bottom",
            bbox=dict(boxstyle="round",fc="white",ec="gray",alpha=.8))
fig.suptitle("Where the best variant lands vs its consensus, by performance tier\n"
             "(bottom-right = tumor up & normal down; below diagonal = specificity gained)",fontsize=12)
fig.tight_layout(rect=[0,0,1,.93]); fig.savefig(FIGS/"fig1c_decomposition_by_tier.png",dpi=120,bbox_inches="tight")

# ---------- fig3b: 6-tier slopegraph, labels inside ------------------------
fig,axs=plt.subplots(1,6,figsize=(16,3.8))
for ax,(p,lab) in zip(axs,TIERS):
    s=S.head(max(3,int(len(S)*p/100)))
    series=[(s.cons_OV8.median(),s.best_OV8.median(),"#cf222e","tumor (OV8)"),
            (s.cons_IOSE.median(),s.best_IOSE.median(),"#1f6feb","normal (IOSE)")]
    ymax=max(v for a,b,_,_ in series for v in (a,b))
    for cT,bT,color,name in series:
        ax.plot([0,1],[cT,bT],"-o",color=color,lw=2.4,label=name)
        ax.annotate(f"{cT:.2f}",(0,cT),textcoords="offset points",xytext=(0,7),ha="center",fontsize=7,color=color)
        ax.annotate(f"{bT:.2f}",(1,bT),textcoords="offset points",xytext=(0,7),ha="center",fontsize=7,color=color)
    ax.set_xticks([0,1]); ax.set_xticklabels(["consensus","best"],fontsize=8)
    ax.set_title(f"{lab}\n(n={len(s)})",fontsize=9); ax.set_xlim(-.5,1.5); ax.set_ylim(-.05*ymax,1.25*ymax)
axs[0].set_ylabel("median activity (RD ratio)"); axs[0].legend(fontsize=8,loc="center left")
fig.suptitle("Activity shift consensus → most-specific variant, by performance tier",fontsize=12)
fig.tight_layout(rect=[0,0,1,.9]); fig.savefig(FIGS/"fig3b_tiered_slopegraph.png",dpi=130,bbox_inches="tight")
print("wrote fig1b, fig1c, fig3b ; top performers:", list(top.tf))
