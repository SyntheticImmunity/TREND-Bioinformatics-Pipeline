#!/usr/bin/env python
"""mRNA-does-not-predict-activity figures — plotnine (ggplot) renderer.
Same numbers as the matplotlib / seaborn renderers (shared _mrna_data)."""
import numpy as np, pandas as pd
from pathlib import Path
from scipy import stats as _st
from plotnine import (ggplot, aes, geom_point, geom_line, geom_hline, geom_vline,
                      geom_abline, geom_histogram, geom_text, annotate, labs,
                      scale_color_manual, scale_fill_manual, coord_fixed, theme_bw,
                      theme, element_text)
import _mrna_data as D

d = D.compute(); c = d.colors
OUT = Path(__file__).resolve().parent / "mrna_figs" / "ggplot"; OUT.mkdir(parents=True, exist_ok=True)
TH = theme_bw() + theme(figure_size=(5.4, 4.4), plot_title=element_text(size=11))

def save(p, name, w=5.4, h=4.4):
    p.save(OUT / f"{name}.pdf", width=w, height=h, verbose=False)
    p.save(OUT / f"{name}.png", width=w, height=h, dpi=150, verbose=False)
    print("  ggplot/", name)

M = d.M.copy(); M["med_ratio"] = 2 ** M.med_log2

# fig0 reference
p = (ggplot(M, aes("mrna_l10", "med_ratio")) + geom_point(color="#33373b", alpha=.5, size=1.4)
     + geom_hline(yintercept=1, linetype=":", color=c.GREY)
     + annotate("text", x=M.mrna_l10.max(), y=M.med_ratio.max(), label=f"r = {d.r_ref:.2f}", ha="right", size=10)
     + labs(x="Differential TF expression (log10 OV8/IOSE TPM)", y="Median enhancer selectivity (OV8/IOSE)",
            title="Current view: TF mRNA vs enhancer selectivity") + TH)
save(p, "fig0_reference", 4.8, 4.4)

# figA recovery
long = pd.DataFrame({"x": d.xs,
                     "Screen-guided (ideal)": d.screen_rec * 100,
                     "mRNA-ranked selection": d.mrna_rec * 100,
                     "Random selection": d.rand_rec * 100}).melt("x", var_name="Strategy", value_name="pct")
order = ["Screen-guided (ideal)", "mRNA-ranked selection", "Random selection"]
long["Strategy"] = pd.Categorical(long.Strategy, categories=order, ordered=True)
p = (ggplot(long, aes("x", "pct", color="Strategy")) + geom_line(size=1.1)
     + geom_vline(xintercept=d.K, linetype=":", color="black", size=.4)
     + scale_color_manual(values={order[0]: c.GREEN, order[1]: c.RED, order[2]: c.GREY})
     + annotate("label", x=d.N, y=8, label=f"Top {d.K} TFs by mRNA recover only {d.nrec}/{d.K} of the best",
                ha="right", size=8)
     + labs(x="Number of TFs selected", y=f"% of the {d.K} most-selective enhancers recovered",
            title="Selecting enhancers by TF mRNA is no better than chance")
     + theme_bw() + theme(figure_size=(5.6, 4.4), legend_position=(0.32, 0.82),
                          legend_title=element_text(size=0), plot_title=element_text(size=11)))
save(p, "figA_recovery", 5.6, 4.4)

# figB variance
med = M[["mrna_l10", "med_log2"]].copy()
p = (ggplot(d.sm, aes("mrna_l10", "log2spec")) + geom_point(color=c.BLUE, alpha=.10, size=.7)
     + geom_point(med, aes("mrna_l10", "med_log2"), color="black", alpha=.7, size=1.2)
     + geom_hline(yintercept=0, linetype=":", color=c.GREY)
     + annotate("label", x=d.sm.mrna_l10.min(), y=d.sm.log2spec.max(), ha="left", va="top", size=8,
                label=f"within-TF variance = {d.within:.2f}\nbetween-TF variance = {d.between:.2f}\n"
                      f"within / between = {d.within/d.between:.1f}x")
     + labs(x="Differential TF expression (log10 OV8/IOSE TPM)", y="Per-sensor selectivity, log2(OV8/IOSE)",
            title="The signal lives within each TF — where mRNA cannot see it")
     + theme_bw() + theme(figure_size=(6.2, 4.4), plot_title=element_text(size=11)))
save(p, "figB_variance", 6.2, 4.4)

# figC ROC
roc = pd.DataFrame({"fpr": d.fpr, "tpr": d.tpr})
p = (ggplot(roc, aes("fpr", "tpr")) + geom_line(color=c.RED, size=1.1)
     + geom_abline(slope=1, intercept=0, linetype="--", color=c.GREY)
     + annotate("label", x=.97, y=.06, ha="right", va="bottom", size=10, label=f"AUC = {d.auc:.2f}\n(chance = 0.50)")
     + coord_fixed() + labs(x="False-positive rate", y="True-positive rate",
            title="Can mRNA flag a TF with a selective enhancer?")
     + theme_bw() + theme(figure_size=(4.4, 4.4), plot_title=element_text(size=10)))
save(p, "figC_roc", 4.4, 4.4)

# figD quadrant — three labelled categories
lab = M[M.category != ""].copy()
lab["category"] = pd.Categorical(lab.category, categories=d.cat_order, ordered=True)
catcol = {k: v[0] for k, v in d.cat_style.items()}
catlab = {k: v[1] for k, v in d.cat_style.items()}
p = (ggplot(M, aes("mrna_l10", "best_log2")) + geom_point(color=c.GREY, alpha=.35, size=1.0)
     + geom_vline(xintercept=d.xthr, linetype=":", color=c.GREY) + geom_hline(yintercept=d.ythr, linetype=":", color=c.GREY)
     + geom_point(lab, aes("mrna_l10", "best_log2", color="category"), size=2.6)
     + geom_text(lab, aes("mrna_l10", "best_log2", label="tf", color="category"), size=7, show_legend=False,
                 adjust_text=dict(arrowprops=dict(arrowstyle="-", color="gray", lw=.4), expand=(1.3, 1.5)))
     + scale_color_manual(values=catcol, labels=[catlab[k] for k in d.cat_order], name="")
     + labs(x="Differential TF expression (log10 OV8/IOSE TPM)", y="Best sensor's selectivity per TF, log2(OV8/IOSE)",
            title="Neither mRNA abundance nor prior literature finds the best enhancers")
     + theme_bw() + theme(figure_size=(6.4, 5.0), legend_position="bottom", plot_title=element_text(size=10)))
save(p, "figD_quadrant", 6.4, 5.2)

# figE top-overexpressed
he = pd.concat([M.assign(grp="All TFs"), d.topm.assign(grp="Top 20 mRNA-overexpressed TFs")])
he["grp"] = pd.Categorical(he.grp, categories=["All TFs", "Top 20 mRNA-overexpressed TFs"], ordered=True)
p = (ggplot(he, aes("best_log2", fill="grp")) + geom_histogram(aes(y="..density.."), bins=30, position="identity", alpha=.55, color=None)
     + geom_vline(xintercept=M.best_log2.median(), color=c.GREY, size=1)
     + geom_vline(xintercept=d.topm.best_log2.median(), color=c.RED, size=1)
     + scale_fill_manual(values={"All TFs": c.GREY, "Top 20 mRNA-overexpressed TFs": c.RED})
     + annotate("label", x=M.best_log2.min(), y=0, ha="left", va="bottom", size=8,
                label=f"median best sensor — all: {2**M.best_log2.median():.2f}x, top-mRNA: {2**d.topm.best_log2.median():.2f}x")
     + labs(x="Best-sensor selectivity, log2(OV8/IOSE)", y="Density", fill="",
            title="The most-overexpressed TFs are unremarkable sensors")
     + theme_bw() + theme(figure_size=(5.6, 4.2), legend_position=(0.34, 0.82), plot_title=element_text(size=11)))
save(p, "figE_top_overexpressed", 5.6, 4.2)

# figF rank-rank — three labelled categories
rho = _st.spearmanr(M.rank_mrna, M.rank_sensor)[0]
labF = M[M.category != ""].copy()
labF["category"] = pd.Categorical(labF.category, categories=d.cat_order, ordered=True)
p = (ggplot(M, aes("rank_mrna", "rank_sensor")) + geom_point(color=c.GREY, alpha=.3, size=.9)
     + geom_point(labF, aes("rank_mrna", "rank_sensor", color="category"), size=2.6)
     + geom_text(labF, aes("rank_mrna", "rank_sensor", label="tf", color="category"), size=7, show_legend=False,
                 adjust_text=dict(arrowprops=dict(arrowstyle="-", color="gray", lw=.4), expand=(1.3, 1.5)))
     + scale_color_manual(values=catcol, labels=[catlab[k] for k in d.cat_order], name="")
     + annotate("label", x=M.rank_mrna.max(), y=M.rank_sensor.max(), ha="right", va="top", size=9,
                label=f"Spearman rho = {rho:.2f}")
     + labs(x="TF rank by mRNA differential (1 = most over-expressed)",
            y="TF rank by best-sensor selectivity (1 = most selective)",
            title="mRNA rank vs enhancer rank — a scramble")
     + theme_bw() + theme(figure_size=(5.8, 5.2), legend_position="bottom", plot_title=element_text(size=11)))
save(p, "figF_rank_rank", 5.8, 5.4)

print("done — plotnine")
