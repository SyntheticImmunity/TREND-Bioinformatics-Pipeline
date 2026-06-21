"""ggplot2-style versions via plotnine (grammar of graphics), saved as *_gg.png
for three-way comparison against matplotlib and seaborn. Native R ggplot2 is not
installed locally; plotnine is its Python port and reads our pandas frames directly."""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, textwrap, re
from plotnine import *

OUT=Path(r"C:\Dev\TREND_bioinformatics_pipeline\revision_analysis"); FIGS=OUT/"figs"
OV8,IOSE="mean_OV8_RD_ratio","mean_IOSE_RD_ratio"; floor=0.1
df=pd.read_csv(OUT/"per_variant_ovca.csv").dropna(subset=["rel_affinity",OV8,IOSE])
_DBS=("jaspar2018","jaspar2016","jaspar","SwissRegulon","HOCOMOCOv11","HOCOMOCOv10","HOCOMOCO",
      "jolma2013","jolma","hPDI","transfac","cisbp","UniPROBE","bulyk","pazar")
def short_pwm(k):                      # -> "TF · source · accession", de-duplicated
    k=" ".join(k.split())
    tf=re.split(r"[_\- ]",k)[0]
    src=next((d for d in _DBS if d.lower() in k.lower()),"")
    m=re.search(r"(MA\d+\.\d+|M\d{3,}|H\w+\.\w+)",k); acc=m.group(1) if m else ""
    if acc and tf.lower() in acc.lower(): acc=""
    return " · ".join(dict.fromkeys([p for p in (tf,src,acc) if p]))

summ=[]
for k,g in df.groupby("pwm_key"):
    cons=g.loc[g["rel_affinity"].idxmax()]; elig=g[g[OV8]>=floor]
    if elig.empty: continue
    best=elig.loc[elig["log2ratio"].idxmax()]
    summ.append(dict(pwm=k,nvar=len(g),cons_OV8=cons[OV8],cons_IOSE=cons[IOSE],best_OV8=best[OV8],
        best_IOSE=best[IOSE],best_spec=best["log2ratio"],cons_spec=cons["log2ratio"],cons_aff=cons["rel_affinity"],
        cons_prom=cons["promoter_name"],best_prom=best["promoter_name"]))
S=pd.DataFrame(summ).sort_values("best_spec",ascending=False).reset_index(drop=True)

# ---- fig1b_gg: per-PWM facets --------------------------------------------
# Feature PWMs that ILLUSTRATE variant improvement: genuine consensus present
# (cons_aff>=0.8 -> real, ~yellow triangle) AND a clear specificity gain (>=2x),
# most tumor-specific first. Avoids overlap panels (gain~1) and low-aff proxies.
S["gain"]=2**(S.best_spec-S.cons_spec)
top=S[(S.nvar>=8)&(S.cons_aff>=0.8)&(S.gain>=2)].sort_values("best_spec",ascending=False).head(12)
print(f"featured panels: {len(top)} (cons_aff>=0.8 & gain>=2x)")
gmax=max(max(df[df.pwm_key==r.pwm][OV8].max(),df[df.pwm_key==r.pwm][IOSE].max()) for _,r in top.iterrows())*1.05
V=[]; M=[]; Tx=[]
for _,row in top.iterrows():
    gp=df[df.pwm_key==row.pwm].copy(); lab="\n".join(textwrap.wrap(short_pwm(row.pwm),26))
    gp["lab"]=lab; V.append(gp[[OV8,IOSE,"rel_affinity","lab","promoter_name"]])
    c=gp[gp.promoter_name==row.cons_prom].iloc[0]; b=gp[gp.promoter_name==row.best_prom].iloc[0]
    M.append(dict(OV8=c[OV8],IOSE=c[IOSE],aff=c["rel_affinity"],lab=lab,role="consensus"))
    M.append(dict(OV8=b[OV8],IOSE=b[IOSE],aff=b["rel_affinity"],lab=lab,role="most-specific"))
    Tx.append(dict(lab=lab,x=gmax*0.03,y=gmax*0.97,txt=f"gain {2**(row.best_spec-row.cons_spec):.1f}×"))
V=pd.concat(V).rename(columns={OV8:"OV8",IOSE:"IOSE","rel_affinity":"aff"})
M=pd.DataFrame(M); Tx=pd.DataFrame(Tx)
order=[ "\n".join(textwrap.wrap(short_pwm(r.pwm),26)) for _,r in top.iterrows()]
for d in (V,M,Tx): d["lab"]=pd.Categorical(d["lab"],categories=order,ordered=True)
p=(ggplot(V,aes("OV8","IOSE"))
   + geom_abline(slope=1,intercept=0,linetype="dashed",color="grey")
   + geom_point(aes(fill="aff"),shape="o",color="black",size=2.6,stroke=.2)
   + geom_point(M[M.role=="consensus"],aes("OV8","IOSE",fill="aff"),shape="o",color="black",size=3.4,stroke=1.7)
   + geom_point(M[M.role=="most-specific"],aes("OV8","IOSE"),shape="*",color="red",size=6)
   + geom_text(Tx,aes(x="x",y="y",label="txt"),ha="left",va="top",size=8)
   + facet_wrap("lab",ncol=4)
   + scale_fill_cmap(cmap_name="viridis",name="motif affinity\n(1 = consensus)")
   + coord_fixed(ratio=1,xlim=(0,gmax),ylim=(0,gmax))
   + labs(x="OV8 (tumor) RD ratio",y="IOSE (normal) RD ratio",
          title="Per-PWM variant clouds (ggplot/plotnine) — thick-edged dot = consensus, ★ = most-specific, below diagonal = tumor-specific")
   + theme_gray() + theme(figure_size=(15,11),strip_text=element_text(size=7),plot_title=element_text(size=11)))
p.save(FIGS/"fig1b_gg.png",dpi=120,verbose=False)

# ---- fig3b_gg: tiered slopegraph -----------------------------------------
TIERS=[(0.1,"top 0.1%"),(1,"top 1%"),(10,"top 10%"),(20,"top 20%"),(40,"top 40%"),(100,"all PWMs")]
recs=[]
for pp,lab in TIERS:
    s=S.head(max(3,int(len(S)*pp/100)))
    for cell,cV,bV in [("tumor (OV8)",s.cons_OV8.median(),s.best_OV8.median()),
                       ("normal (IOSE)",s.cons_IOSE.median(),s.best_IOSE.median())]:
        recs.append(dict(tier=f"{lab} (n={len(s)})",pos="consensus",x=0,cell=cell,val=cV))
        recs.append(dict(tier=f"{lab} (n={len(s)})",pos="best",x=1,cell=cell,val=bV))
D=pd.DataFrame(recs); D["lbl"]=D.val.map(lambda v:f"{v:.2f}")
D["tier"]=pd.Categorical(D.tier,categories=[f"{l} (n={len(S.head(max(3,int(len(S)*pp/100))))})" for pp,l in TIERS],ordered=True)
p=(ggplot(D,aes("x","val",color="cell",group="cell"))
   + geom_line(size=1.1)+geom_point(size=3)
   + geom_text(aes(label="lbl"),va="bottom",size=8,nudge_y=0.02,show_legend=False)
   + facet_wrap("tier",ncol=3,scales="free_y")
   + scale_x_continuous(breaks=[0,1],labels=["consensus","best"],limits=(-.3,1.3))
   + scale_color_manual(values={"tumor (OV8)":"#d1495b","normal (IOSE)":"#3a7ca5"})
   + labs(x="",y="median activity (RD ratio)",color="",
          title="Activity shift consensus → most-specific variant, by tier (ggplot/plotnine)")
   + theme_bw() + theme(figure_size=(12,7),legend_position="top"))
p.save(FIGS/"fig3b_gg.png",dpi=130,verbose=False)
print("wrote fig1b_gg, fig3b_gg")
