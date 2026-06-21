"""Round-3 figure fixes per user:
  fig1b  readable log scales (plain numbers + grid); PWM-name titles;
         parenthetical relabeled 'best OV8/IOSE = N x' (absolute specificity)
  fig1c  median-annotation box moved to the empty UPPER-LEFT of each panel
  fig3b  2x3 grid incl. an 'all PWMs' panel; legend moved OUT of the panels;
         consensus/best value labels separated (tumor above, normal below)
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import textwrap

OUT=Path(r"C:\Dev\TREND_bioinformatics_pipeline\revision_analysis"); FIGS=OUT/"figs"
OV8,IOSE="mean_OV8_RD_ratio","mean_IOSE_RD_ratio"; pc,floor=0.0,0.1  # no pseudocount: no zeros exist, raw OV8/IOSE matches dashboard
df=pd.read_csv(OUT/"per_variant_ovca.csv").dropna(subset=["rel_affinity",OV8,IOSE])

def short_pwm(k):                      # unique, full PWM label (no truncation)
    k=" ".join(k.split())              # collapse tabs/whitespace (some names are tab-separated)
    return k.replace("_Hsapiens-"," · ").replace("Hsapiens-"," · ").replace("-"," ")

summ=[]
for k,g in df.groupby("pwm_key"):
    cons=g.loc[g["rel_affinity"].idxmax()]; elig=g[g[OV8]>=floor]
    if elig.empty: continue
    best=elig.loc[elig["log2ratio"].idxmax()]
    summ.append(dict(pwm=k, nvar=len(g),
        cons_OV8=cons[OV8],cons_IOSE=cons[IOSE],best_OV8=best[OV8],best_IOSE=best[IOSE],
        dT=np.log2((best[OV8]+pc)/(cons[OV8]+pc)), dN=np.log2((best[IOSE]+pc)/(cons[IOSE]+pc)),
        best_spec=best["log2ratio"], cons_prom=cons["promoter_name"], best_prom=best["promoter_name"]))
S=pd.DataFrame(summ).sort_values("best_spec",ascending=False).reset_index(drop=True)

# ---------- fig1b: readable axes + PWM-name titles -------------------------
top=S[S.nvar>=8].head(12)
fig,axs=plt.subplots(3,4,figsize=(15,11)); axs=axs.ravel()
for i,(ax,(_,row)) in enumerate(zip(axs, top.iterrows())):
    gp=df[df.pwm_key==row.pwm]
    ax.scatter(gp[OV8]+pc, gp[IOSE]+pc, c=gp["rel_affinity"], cmap="viridis",
               s=60, edgecolors="k", linewidths=.4, vmin=0, vmax=1, zorder=3)
    cons=gp[gp.promoter_name==row.cons_prom]; best=gp[gp.promoter_name==row.best_prom]
    ax.scatter(cons[OV8]+pc,cons[IOSE]+pc,marker="s",s=180,facecolors="none",edgecolors="black",linewidths=1.8,zorder=4)
    ax.scatter(best[OV8]+pc,best[IOSE]+pc,marker="*",s=340,facecolors="none",edgecolors="crimson",linewidths=1.8,zorder=5)
    hi=max(gp[OV8].max(),gp[IOSE].max())
    ax.plot([0,hi],[0,hi],"--",color="gray",lw=1)          # linear diagonal from origin
    ax.set_xlim(0,hi*1.08); ax.set_ylim(0,hi*1.08)
    ax.grid(True, alpha=.2)
    name="\n".join(textwrap.wrap(short_pwm(row.pwm), 30))
    ax.set_title(f"{name}\nbest OV8/IOSE = {2**row.best_spec:.1f}×", fontsize=8)
    if i % 4 == 0: ax.set_ylabel("IOSE activity (normal)\nRD ratio",fontsize=8)
    if i // 4 == 2: ax.set_xlabel("OV8 activity (tumor)  RD ratio",fontsize=8)
leg=[Line2D([0],[0],marker="s",ls="none",mfc="none",mec="black",ms=12,label="consensus (highest affinity)"),
     Line2D([0],[0],marker="*",ls="none",mfc="none",mec="crimson",ms=16,label="most-specific variant"),
     Line2D([0],[0],ls="--",color="gray",label="diagonal = equal in both (no specificity)")]
fig.legend(handles=leg,loc="upper center",ncol=3,fontsize=10,frameon=False,bbox_to_anchor=(.5,.995))
fig.suptitle("Per-PWM variant clouds — top tumor-specific performers  (point color = motif affinity; below diagonal = tumor-specific)",
             fontsize=12,y=1.025)
fig.tight_layout(rect=[0,0,1,.955]); fig.savefig(FIGS/"fig1b_per_pwm_panels.png",dpi=120,bbox_inches="tight")

# ---------- fig1c: med box to UPPER-LEFT -----------------------------------
TIERS6=[(0.1,"top 0.1%"),(1,"top 1%"),(10,"top 10%"),(20,"top 20%"),(40,"top 40%"),(100,"all PWMs")]
fig,axs=plt.subplots(2,3,figsize=(13,8.4)); axs=axs.ravel(); L=3.2
for ax,(p,lab) in zip(axs,TIERS6):
    s=S.head(max(3,int(len(S)*p/100)))
    ax.scatter(s.dT.clip(-L,L), s.dN.clip(-L,L), s=14, alpha=.45, c="#1f6feb", edgecolors="none")
    ax.plot([-L,L],[-L,L],"--",color="k",lw=1); ax.axhline(0,color="gray",lw=.6); ax.axvline(0,color="gray",lw=.6)
    ax.set_xlim(-L,L); ax.set_ylim(-L,L); ax.set_aspect("equal")
    ax.set_title(f"{lab}  (n={len(s)})",fontsize=10)
    ax.set_xlabel("Δ tumor (log2, best−consensus)",fontsize=8); ax.set_ylabel("Δ normal (log2, best−consensus)",fontsize=8)
    ax.text(.04,.96,f"med Δtumor {s.dT.median():+.2f}\nmed Δnormal {s.dN.median():+.2f}",
            transform=ax.transAxes,fontsize=8,va="top",ha="left",
            bbox=dict(boxstyle="round",fc="white",ec="gray",alpha=.85))
fig.suptitle("Best variant vs its consensus, by performance tier  (bottom-right = tumor↑ & normal↓; below diagonal = specificity gained)",fontsize=11)
fig.tight_layout(rect=[0,0,1,.95]); fig.savefig(FIGS/"fig1c_decomposition_by_tier.png",dpi=120,bbox_inches="tight")

# ---------- fig3b: 2x3 incl 'all PWMs', legend outside, labels separated ----
TIERS3=[(0.1,"top 0.1%"),(1,"top 1%"),(10,"top 10%"),(20,"top 20%"),(40,"top 40%"),(100,"all PWMs")]
fig,axs=plt.subplots(2,3,figsize=(12,7)); axs=axs.ravel()
for ax,(p,lab) in zip(axs,TIERS3):
    s=S.head(max(3,int(len(S)*p/100)))
    tum=(s.cons_OV8.median(), s.best_OV8.median()); nor=(s.cons_IOSE.median(), s.best_IOSE.median())
    ax.plot([0,1],list(tum),"-o",color="#cf222e",lw=2.4)
    ax.plot([0,1],list(nor),"-o",color="#1f6feb",lw=2.4)
    ymax=max(*tum,*nor)
    for col,x in ((0,0.0),(1,1.0)):     # higher value labels above, lower below -> never collide
        tv,nv=tum[col],nor[col]
        ax.annotate(f"{tv:.2f}",(x,tv),textcoords="offset points",xytext=(0, 9 if tv>=nv else -13),ha="center",fontsize=7,color="#cf222e")
        ax.annotate(f"{nv:.2f}",(x,nv),textcoords="offset points",xytext=(0, 9 if nv>tv else -13),ha="center",fontsize=7,color="#1f6feb")
    ax.set_xticks([0,1]); ax.set_xticklabels(["consensus","best"],fontsize=8)
    ax.set_title(f"{lab}  (n={len(s)})",fontsize=10); ax.set_xlim(-.5,1.5); ax.set_ylim(-.1*ymax,1.3*ymax)
axs[0].set_ylabel("median activity (RD ratio)"); axs[3].set_ylabel("median activity (RD ratio)")
fig.legend(handles=[Line2D([0],[0],marker="o",color="#cf222e",label="tumor (OV8)"),
                    Line2D([0],[0],marker="o",color="#1f6feb",label="normal (IOSE)")],
           loc="upper center",ncol=2,fontsize=10,frameon=False,bbox_to_anchor=(.5,.985))
fig.suptitle("Activity shift consensus → most-specific variant, by performance tier",fontsize=12,y=1.04)
fig.tight_layout(rect=[0,0,1,.93]); fig.savefig(FIGS/"fig3b_tiered_slopegraph.png",dpi=130,bbox_inches="tight")
print("wrote fig1b, fig1c, fig3b")
