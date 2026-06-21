"""Seaborn-themed versions of the key figures, saved as *_sns.png so the
matplotlib originals are kept for side-by-side comparison."""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, textwrap
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.lines import Line2D

sns.set_theme(style="whitegrid", context="notebook", font_scale=0.9)
OUT=Path(r"C:\Dev\TREND_bioinformatics_pipeline\revision_analysis"); FIGS=OUT/"figs"
OV8,IOSE="mean_OV8_RD_ratio","mean_IOSE_RD_ratio"; floor=0.1
df=pd.read_csv(OUT/"per_variant_ovca.csv").dropna(subset=["rel_affinity",OV8,IOSE])

def short_pwm(k): return " ".join(k.split()).replace("_Hsapiens-"," · ").replace("Hsapiens-"," · ").replace("-"," ")

summ=[]
for k,g in df.groupby("pwm_key"):
    cons=g.loc[g["rel_affinity"].idxmax()]; elig=g[g[OV8]>=floor]
    if elig.empty: continue
    best=elig.loc[elig["log2ratio"].idxmax()]
    summ.append(dict(pwm=k, nvar=len(g), cons_OV8=cons[OV8],cons_IOSE=cons[IOSE],
        best_OV8=best[OV8],best_IOSE=best[IOSE], best_spec=best["log2ratio"], cons_spec=cons["log2ratio"],
        cons_aff=cons["rel_affinity"], best_aff=best["rel_affinity"],
        cons_prom=cons["promoter_name"], best_prom=best["promoter_name"]))
S=pd.DataFrame(summ).sort_values("best_spec",ascending=False).reset_index(drop=True)

# ---- fig1b_sns: per-PWM clouds, linear, shared affinity colorbar ----------
top=S[S.nvar>=8].head(12)
print("consensus-proxy affinity per panel (1.0 = true consensus survived QC):")
for _,r in top.iterrows(): print(f"  {short_pwm(r.pwm)[:34]:34s} cons_aff={r.cons_aff:.2f}  gain={2**(r.best_spec-r.cons_spec):.1f}x")
gmax=max(max(df[df.pwm_key==r.pwm][OV8].max(), df[df.pwm_key==r.pwm][IOSE].max()) for _,r in top.iterrows())*1.05
fig,axs=plt.subplots(3,4,figsize=(15,12)); axs=axs.ravel(); sc=None
for i,(ax,(_,row)) in enumerate(zip(axs, top.iterrows())):
    gp=df[df.pwm_key==row.pwm]
    sc=ax.scatter(gp[OV8], gp[IOSE], c=gp["rel_affinity"], cmap="viridis",
                  s=70, edgecolors="k", linewidths=.4, vmin=0, vmax=1, zorder=3)
    cons=gp[gp.promoter_name==row.cons_prom]; best=gp[gp.promoter_name==row.best_prom]
    for m,s1,s2,ec in [("s",260,210,"black"),("*",470,380,"crimson")]:
        xy=cons if m=="s" else best
        ax.scatter(xy[OV8],xy[IOSE],marker=m,s=s1,facecolors="none",edgecolors="white",linewidths=3.2,zorder=4)
        ax.scatter(xy[OV8],xy[IOSE],marker=m,s=s2,facecolors="none",edgecolors=ec,linewidths=1.9,zorder=5)
    ax.plot([0,gmax],[0,gmax],"--",color="gray",lw=1); ax.set_xlim(0,gmax); ax.set_ylim(0,gmax)  # SHARED, consistent axes
    ax.text(.04,.96,f"cons {2**row.cons_spec:.1f}× → best {2**row.best_spec:.1f}×\nspecificity gain {2**(row.best_spec-row.cons_spec):.1f}×",
            transform=ax.transAxes,va="top",ha="left",fontsize=7.5,
            bbox=dict(boxstyle="round",fc="white",ec="gray",alpha=.85))
    ax.set_title("\n".join(textwrap.wrap(short_pwm(row.pwm),34)),fontsize=8)
    if i%4==0: ax.set_ylabel("IOSE (normal) RD ratio",fontsize=8)
    if i//4==2: ax.set_xlabel("OV8 (tumor) RD ratio",fontsize=8)
fig.subplots_adjust(right=0.9, hspace=0.5, wspace=0.2)
cax=fig.add_axes([0.92,0.25,0.015,0.5]); fig.colorbar(sc,cax=cax,label="motif affinity (1 = consensus)")
leg=[Line2D([0],[0],marker="s",ls="none",mfc="none",mec="black",ms=12,label="consensus"),
     Line2D([0],[0],marker="*",ls="none",mfc="none",mec="crimson",ms=15,label="most-specific"),
     Line2D([0],[0],ls="--",color="gray",label="no specificity (y=x)")]
fig.legend(handles=leg,loc="upper center",ncol=3,frameon=False,bbox_to_anchor=(.5,.99))
fig.suptitle("Per-PWM variant clouds — top tumor-specific performers (below diagonal = tumor-specific)",y=1.015,fontsize=12)
fig.savefig(FIGS/"fig1b_sns.png",dpi=120,bbox_inches="tight")

# ---- fig3b_sns: tiered slopegraph -----------------------------------------
TIERS=[(0.1,"top 0.1%"),(1,"top 1%"),(10,"top 10%"),(20,"top 20%"),(40,"top 40%"),(100,"all PWMs")]
fig,axs=plt.subplots(2,3,figsize=(12,7)); axs=axs.ravel()
pal={"tumor":"#d1495b","normal":"#3a7ca5"}
for ax,(p,lab) in zip(axs,TIERS):
    s=S.head(max(3,int(len(S)*p/100)))
    tum=(s.cons_OV8.median(),s.best_OV8.median()); nor=(s.cons_IOSE.median(),s.best_IOSE.median())
    ax.plot([0,1],tum,"-o",color=pal["tumor"],lw=2.6,ms=9)
    ax.plot([0,1],nor,"-o",color=pal["normal"],lw=2.6,ms=9)
    ymax=max(*tum,*nor)
    for col,x in ((0,0.),(1,1.)):
        tv,nv=tum[col],nor[col]
        ax.annotate(f"{tv:.2f}",(x,tv),textcoords="offset points",xytext=(0,9 if tv>=nv else -14),ha="center",fontsize=8,color=pal["tumor"])
        ax.annotate(f"{nv:.2f}",(x,nv),textcoords="offset points",xytext=(0,9 if nv>tv else -14),ha="center",fontsize=8,color=pal["normal"])
    ax.set_xticks([0,1]); ax.set_xticklabels(["consensus","best"]); ax.set_title(f"{lab}  (n={len(s)})")
    ax.set_xlim(-.5,1.5); ax.set_ylim(-.1*ymax,1.3*ymax)
for i in (0,3): axs[i].set_ylabel("median activity (RD ratio)")
fig.legend(handles=[Line2D([0],[0],marker="o",color=pal["tumor"],label="tumor (OV8)"),
                    Line2D([0],[0],marker="o",color=pal["normal"],label="normal (IOSE)")],
           loc="upper center",ncol=2,frameon=False,bbox_to_anchor=(.5,.98))
fig.suptitle("Activity shift consensus → most-specific variant, by tier",y=1.03,fontsize=12)
fig.tight_layout(rect=[0,0,1,.93]); fig.savefig(FIGS/"fig3b_sns.png",dpi=130,bbox_inches="tight")

# ---- fig5b_sns: Goldilocks histogram --------------------------------------
pcts=[]
for k,g in df.groupby("pwm_key"):
    g=g[g[OV8]>=floor]
    if len(g)<4: continue
    pcts.append(100*(g["rel_affinity"]<g.loc[g["log2ratio"].idxmax(),"rel_affinity"]).mean())
gp=pd.DataFrame({"pct":pcts})
gp["tier"]=pd.cut(gp.pct,[-1,20,80,101],labels=["weakest 20%","middle","near-consensus 20%"])
fig,ax=plt.subplots(figsize=(7.5,3.6))
sns.histplot(data=gp,x="pct",hue="tier",bins=np.arange(0,101,10),multiple="stack",
             palette={"weakest 20%":"#d1495b","middle":"#8d99ae","near-consensus 20%":"#2a9d8f"},ax=ax)
ax.set_xlabel("affinity rank of the most-specific variant within its PWM\n(0 = weakest motif match · 100 = consensus)")
ax.set_ylabel("PWMs"); ax.set_title("Where the best variant sits in affinity — no universal optimum")
fig.savefig(FIGS/"fig5b_sns.png",dpi=130,bbox_inches="tight")

# ---- fig6b_sns: specificity vs affinity density ---------------------------
fig,ax=plt.subplots(figsize=(7,4.4))
sns.histplot(data=df,x="rel_affinity",y="log2ratio",bins=40,cbar=True,cmap="magma",
             cbar_kws={"label":"number of variants"},ax=ax)
b=np.linspace(0,1,21); idx=np.clip(np.digitize(df["rel_affinity"],b)-1,0,19)
med=[np.median(df["log2ratio"][idx==i]) if (idx==i).any() else np.nan for i in range(20)]
ax.plot((b[:-1]+b[1:])/2,med,color="cyan",lw=2.5,label="median specificity (flat = no trend)")
ax.axhline(df["log2ratio"].median(),color="white",ls=":",lw=1)
ax.set_xlabel("relative affinity (1 = consensus motif)"); ax.set_ylabel("specificity  log2(OV8/IOSE)")
ax.set_title("Specificity vs affinity — flat median = affinity doesn't predict specificity"); ax.legend(loc="upper right",fontsize=8)
fig.savefig(FIGS/"fig6b_sns.png",dpi=130,bbox_inches="tight")
print("wrote fig1b_sns, fig3b_sns, fig5b_sns, fig6b_sns")
