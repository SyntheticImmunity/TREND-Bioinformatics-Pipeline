#!/usr/bin/env python
"""mRNA-does-not-predict-activity figures — seaborn renderer (whitegrid look).
Same numbers as the matplotlib / plotnine renderers (shared _mrna_data)."""
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from adjustText import adjust_text
import _mrna_data as D
from scipy import stats as _st

sns.set_theme(style="whitegrid", context="notebook")
d = D.compute(); c = d.colors
OUT = Path(__file__).resolve().parent / "mrna_figs" / "seaborn"; OUT.mkdir(parents=True, exist_ok=True)
BOX = dict(boxstyle="round", fc="white", ec=c.GREY, alpha=.92)

def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig); print("  seaborn/", name)

def label_categories(ax, xcol, ycol, line_for=(), below=()):
    """Scatter the 3 categories with repelled labels. A colour-matched leader line
    is drawn only for the TFs named in `line_for` (the genuinely piled-up dots);
    every other label sits next to its dot with no line. TFs in `below` are pinned
    just under their dot (no line)."""
    line_for = set(line_for); below = set(below)
    texts, anchors = [], []
    for cat in d.cat_order:
        col, labl = d.cat_style[cat]; sub = d.M[d.M.category == cat]
        ax.scatter(sub[xcol], sub[ycol], s=36, color=col, edgecolors="white", linewidths=.5, zorder=5, label=labl)
        for _, row in sub.iterrows():
            texts.append(ax.text(row[xcol], row[ycol], row.tf, fontsize=7, color=col, zorder=7))
            anchors.append((row[xcol], row[ycol], col, row.tf))
    adjust_text(texts, ax=ax, expand=(1.3, 1.6), force_text=(0.3, 0.45))
    import numpy as np
    inv = ax.transData.inverted(); MIN = 26
    for t, (x0, y0, col, tf) in zip(texts, anchors):
        if tf not in line_for:
            continue
        pdot = np.array(ax.transData.transform((x0, y0)))
        plab = np.array(ax.transData.transform(t.get_position()))
        vec = plab - pdot; dist = np.hypot(*vec)
        if dist < MIN:
            vec = np.array([14.0, 16.0]) if dist < 1e-6 else vec / dist * MIN
            t.set_position(inv.transform(pdot + vec))
        tx, ty = t.get_position()
        ax.plot([x0, tx], [y0, ty], color=col, lw=0.5, alpha=.8, zorder=4)
    for t, (x0, y0, col, tf) in zip(texts, anchors):
        if tf in below:  # pin directly under the dot, no line
            pdot = np.array(ax.transData.transform((x0, y0)))
            t.set_position(inv.transform(pdot + np.array([0.0, -13.0])))
            t.set_ha("center"); t.set_va("top")

# fig0 reference
fig, ax = plt.subplots(figsize=(4.6, 4.2))
sns.scatterplot(x=d.M.mrna_l10, y=2 ** d.M.med_log2, s=16, color="#33373b", alpha=.55, edgecolor="none", ax=ax)
ax.axhline(1, color=c.GREY, ls=":", lw=1)
ax.set_xlabel("Differential TF expression (log10 OV8/IOSE TPM)")
ax.set_ylabel("Median enhancer selectivity (OV8/IOSE)")
ax.set_title("Current view: TF mRNA vs enhancer selectivity")
ax.text(.97, .95, f"r = {d.r_ref:.2f}", transform=ax.transAxes, ha="right", va="top", fontsize=11)
save(fig, "fig0_reference")

# figA recovery
long = pd.DataFrame({"x": d.xs,
                     "Screen-guided (ideal)": d.screen_rec * 100,
                     "mRNA-ranked selection": d.mrna_rec * 100,
                     "Random selection": d.rand_rec * 100}).melt("x", var_name="Strategy", value_name="pct")
fig, ax = plt.subplots(figsize=(5.6, 4.4))
sns.lineplot(data=long, x="x", y="pct", hue="Strategy", style="Strategy",
             palette={"Screen-guided (ideal)": c.GREEN, "mRNA-ranked selection": c.RED, "Random selection": c.GREY},
             dashes={"Screen-guided (ideal)": "", "mRNA-ranked selection": "", "Random selection": (4, 3)},
             lw=2, ax=ax)
ax.axvline(d.K, color="k", ls=":", lw=.8)
ax.set_xlabel("Number of TFs selected"); ax.set_ylabel(f"% of the {d.K} most-selective enhancers recovered")
ax.set_title("Selecting enhancers by TF mRNA is no better than chance")
ax.set_xlim(0, d.N); ax.set_ylim(0, 100)
ax.legend(fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, title=None, frameon=False)
ax.text(.97, .06, f"Top {d.K} TFs by mRNA recover\nonly {d.nrec}/{d.K} of the best",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=9, bbox=BOX)
save(fig, "figA_recovery")

# figB variance
fig, ax = plt.subplots(figsize=(6.2, 4.4))
sns.scatterplot(x=d.sm.mrna_l10, y=d.sm.log2spec, s=6, color=c.BLUE, alpha=.12, edgecolor="none", ax=ax)
sns.scatterplot(x=d.M.mrna_l10, y=d.M.med_log2, s=14, color="#222", alpha=.75, edgecolor="none", ax=ax, label="Per-TF median")
ax.axhline(0, color=c.GREY, ls=":", lw=1)
ax.set_xlabel("Differential TF expression (log10 OV8/IOSE TPM)")
ax.set_ylabel("Per-sensor selectivity, log2(OV8/IOSE)")
ax.set_title("The signal lives within each TF — where mRNA cannot see it")
ax.text(.03, .97, f"Within-TF variance = {d.within:.2f}\nBetween-TF variance = {d.between:.2f}\n"
        f"within / between = {d.within/d.between:.1f}×", transform=ax.transAxes, va="top", fontsize=9, bbox=BOX)
ax.legend(fontsize=9, loc="lower right")
save(fig, "figB_variance")

# figC ROC
fig, ax = plt.subplots(figsize=(4.4, 4.4))
sns.lineplot(x=d.fpr, y=d.tpr, color=c.RED, lw=2.2, ax=ax)
ax.plot([0, 1], [0, 1], color=c.GREY, ls="--", lw=1)
ax.set_xlabel("False-positive rate"); ax.set_ylabel("True-positive rate")
ax.set_title("Can mRNA flag a TF with a selective enhancer?")
ax.text(.96, .06, f"AUC = {d.auc:.2f}\n(chance = 0.50)", transform=ax.transAxes, ha="right", va="bottom",
        fontsize=11, bbox=BOX)
ax.set_aspect("equal"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
save(fig, "figC_roc")

# figD quadrant — three labelled categories
fig, ax = plt.subplots(figsize=(6.2, 5.0))
sns.scatterplot(x=d.M.mrna_l10, y=d.M.best_log2, s=10, color=c.GREY, alpha=.35, edgecolor="none", ax=ax, zorder=1)
ax.axvline(d.xthr, color=c.GREY, ls=":", lw=1); ax.axhline(d.ythr, color=c.GREY, ls=":", lw=1)
label_categories(ax, "mrna_l10", "best_log2",
                 line_for={"E2F8", "E2F6", "E2F3", "NKX2-1", "ZIC2", "PITX1"}, below={"MYC"})
ax.set_xlabel("Differential TF expression (log10 OV8/IOSE TPM)")
ax.set_ylabel("Best sensor's selectivity per TF, log2(OV8/IOSE)")
ax.set_title("Neither mRNA abundance nor prior literature finds the best enhancers")
ax.legend(fontsize=7.5, loc="lower right", framealpha=.95)
save(fig, "figD_quadrant")

# figE top-overexpressed
fig, ax = plt.subplots(figsize=(5.4, 4.2))
sns.histplot(d.M.best_log2, bins=30, stat="density", color=c.GREY, alpha=.55, edgecolor="none", label="All TFs", ax=ax)
sns.histplot(d.topm.best_log2, bins=30, stat="density", color=c.RED, alpha=.5, edgecolor="none", label="Top 20 mRNA-overexpressed TFs", ax=ax)
ax.axvline(d.M.best_log2.median(), color=c.GREY, lw=1.5); ax.axvline(d.topm.best_log2.median(), color=c.RED, lw=1.5)
ax.set_xlabel("Best-sensor selectivity, log2(OV8/IOSE)"); ax.set_ylabel("Density")
ax.set_title("The most-overexpressed TFs are unremarkable sensors")
ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.0, 1.0), framealpha=.95)
ax.text(.03, .96, f"median best sensor\nall TFs: {2**d.M.best_log2.median():.2f}×\n"
        f"top-mRNA: {2**d.topm.best_log2.median():.2f}×", transform=ax.transAxes, va="top", fontsize=9, bbox=BOX)
save(fig, "figE_top_overexpressed")

# figF rank-rank — three labelled categories
rho = _st.spearmanr(d.M.rank_mrna, d.M.rank_sensor)[0]
fig, ax = plt.subplots(figsize=(5.6, 5.0))
sns.scatterplot(x=d.M.rank_mrna, y=d.M.rank_sensor, s=10, color=c.GREY, alpha=.3, edgecolor="none", ax=ax, zorder=1)
label_categories(ax, "rank_mrna", "rank_sensor", line_for={"MYC", "E2F6", "E2F8", "NKX2-1"})
ax.set_xlabel("TF rank by mRNA differential (1 = most over-expressed)")
ax.set_ylabel("TF rank by best-sensor selectivity (1 = most selective)")
ax.set_title("mRNA rank vs enhancer rank — a scramble")
ax.text(.5, .98, f"Spearman ρ = {rho:.2f}", transform=ax.transAxes, ha="center", va="top", fontsize=10, bbox=BOX)
ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False)
save(fig, "figF_rank_rank")

print("done — seaborn")
