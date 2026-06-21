#!/usr/bin/env python
"""
TF mRNA abundance does NOT predict synthetic-enhancer activity/selectivity.
=========================================================================
Self-contained reproduction of the seven matplotlib figures for the revision.

Reads ONE data file (mrna_vs_activity_data.csv) — one row per quantified enhancer
sensor — and regenerates every figure as a vector PDF + PNG into figures/.

Run:   python plot_mrna_vs_activity.py
Deps:  numpy  pandas  scipy  matplotlib  adjustText
       (pip install numpy pandas scipy matplotlib adjustText)

Data columns (mrna_vs_activity_data.csv):
  tf                       transcription-factor (human-curated)
  sensor_log2_selectivity  this sensor's tumour selectivity, log2(OV8/IOSE)
  tf_mrna_log10_ratio      the TF's differential mRNA, log10(OV8 TPM / IOSE TPM)
                           (constant across that TF's sensors)

Everything else (per-TF best/median selectivity, ranks, the three reference TF
categories, the recovery curve, ROC, variance decomposition) is derived here, so
this script + the one CSV fully reproduce the figures.
"""
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from adjustText import adjust_text
from scipy import stats

HERE = Path(__file__).resolve().parent
DATA = HERE / "mrna_vs_activity_data.csv"
OUT = HERE / "figures"; OUT.mkdir(exist_ok=True)
K = 50                                    # target size for the recovery curve
RED, BLUE, GREY, GREEN2 = "#d1495b", "#1f6feb", "#8b949e", "#198754"
CAT_STYLE = {
    "screen-best": ("#198754", "Most tumour-selective sensors (screen)"),
    "literature":  ("#1f6feb", "Field-acknowledged ovarian-cancer TFs"),
    "mRNA-top":    ("#d1495b", "Most over-expressed (OV8/IOSE mRNA)"),
}
CAT_ORDER = ["screen-best", "literature", "mRNA-top"]
BOX = dict(boxstyle="round", fc="white", ec=GREY, alpha=.92)

def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig); print("  wrote", name)

# ----------------------------------------------------------------- derive everything
sen = pd.read_csv(DATA)
M = (sen.groupby("tf")
     .agg(n=("sensor_log2_selectivity", "size"),
          med_log2=("sensor_log2_selectivity", "median"),
          best_log2=("sensor_log2_selectivity", "max"),
          mrna_l10=("tf_mrna_log10_ratio", "first"))
     .reset_index())
M["good"] = M.best_log2 >= 1
M["rank_mrna"] = M.mrna_l10.rank(ascending=False)
M["rank_sensor"] = M.best_log2.rank(ascending=False)
N = len(M)
r_ref = stats.pearsonr(M.mrna_l10, M.med_log2)[0]

# three reference TF categories (priority literature > screen-best > mRNA-top)
tfset = set(M.tf)
LIT = [t for t in ["PAX8", "WT1", "SOX17", "MECOM", "FOXM1"] if t in tfset]
screen_best = [t for t in M.sort_values("best_log2", ascending=False).tf if t not in LIT][:6]
mrna_top = [t for t in M.sort_values("mrna_l10", ascending=False).tf
            if t not in LIT and t not in screen_best][:6]
cat = {**{t: "mRNA-top" for t in mrna_top},
       **{t: "screen-best" for t in screen_best}, **{t: "literature" for t in LIT}}
M["category"] = M.tf.map(cat).fillna("")

# recovery curve
order = M.sort_values("mrna_l10", ascending=False).reset_index(drop=True)
target = set(M.sort_values("best_log2", ascending=False).head(K).tf)
xs = np.arange(1, N + 1)
mrna_rec = np.cumsum([1 if t in target else 0 for t in order.tf]) / K
rand_rec = xs / N
screen_rec = np.minimum(xs, K) / K
nrec = int(mrna_rec[K - 1] * K)

# ROC of mRNA differential -> "good" TF
score, label = M.mrna_l10.values, M.good.values
P, Nn = label.sum(), (~label).sum()
tpr, fpr = [0.0], [0.0]
for t in np.sort(np.unique(score))[::-1]:
    pred = score >= t
    tpr.append((pred & label).sum() / P); fpr.append((pred & ~label).sum() / Nn)
fpr, tpr = np.array(fpr), np.array(tpr)
pos, neg = score[label], score[~label]
auc = stats.mannwhitneyu(pos, neg, alternative="two-sided").statistic / (len(pos) * len(neg))

# variance decomposition + per-sensor frame for fig B
within = sen.groupby("tf").sensor_log2_selectivity.var().mean()
between = M.med_log2.var()
sm = sen.rename(columns={"sensor_log2_selectivity": "log2spec", "tf_mrna_log10_ratio": "mrna_l10"})

xthr, ythr = np.log10(2), 1.0
topm = M.sort_values("mrna_l10", ascending=False).head(20)

# ----------------------------------------------------------------- shared TF labeller
def label_categories(ax, xcol, ycol, line_for=(), below=()):
    """Scatter the 3 reference categories with repelled labels. A colour-matched
    leader line is drawn only for TFs in `line_for`; TFs in `below` are pinned
    just under their dot; all other labels sit beside their dot with no line."""
    line_for, below = set(line_for), set(below)
    texts, anchors = [], []
    for c in CAT_ORDER:
        col, labl = CAT_STYLE[c]; sub = M[M.category == c]
        ax.scatter(sub[xcol], sub[ycol], s=36, color=col, edgecolors="white", linewidths=.5, zorder=5, label=labl)
        for _, row in sub.iterrows():
            texts.append(ax.text(row[xcol], row[ycol], row.tf, fontsize=7, color=col, zorder=7))
            anchors.append((row[xcol], row[ycol], col, row.tf))
    adjust_text(texts, ax=ax, expand=(1.3, 1.6), force_text=(0.3, 0.45))
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
        if tf in below:
            pdot = np.array(ax.transData.transform((x0, y0)))
            t.set_position(inv.transform(pdot + np.array([0.0, -13.0])))
            t.set_ha("center"); t.set_va("top")

# ============================================================ fig0 reference (S3A)
fig, ax = plt.subplots(figsize=(4.6, 4.2))
ax.scatter(M.mrna_l10, 2 ** M.med_log2, s=10, color="k", alpha=.5, edgecolors="none")
ax.axhline(1, color=GREY, ls=":", lw=1)
ax.set_xlabel("Differential TF expression (log10 OV8/IOSE TPM)")
ax.set_ylabel("Median enhancer selectivity (OV8/IOSE)")
ax.set_title("Current view: TF mRNA vs enhancer selectivity")
ax.text(.97, .95, f"r = {r_ref:.2f}", transform=ax.transAxes, ha="right", va="top", fontsize=11)
save(fig, "fig0_reference")

# ============================================================ figA recovery
fig, ax = plt.subplots(figsize=(5.6, 4.4))
ax.plot(xs, screen_rec * 100, color=GREEN2, lw=2, label="Screen-guided (ideal)")
ax.plot(xs, mrna_rec * 100, color=RED, lw=2.2, label="mRNA-ranked selection")
ax.plot(xs, rand_rec * 100, color=GREY, lw=1.5, ls="--", label="Random selection")
ax.axvline(K, color="k", ls=":", lw=.8)
ax.set_xlabel("Number of TFs selected"); ax.set_ylabel(f"% of the {K} most-selective enhancers recovered")
ax.set_title("Selecting enhancers by TF mRNA is no better than chance")
ax.set_xlim(0, N); ax.set_ylim(0, 100)
ax.legend(fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False)
ax.text(.97, .06, f"Top {K} TFs by mRNA recover\nonly {nrec}/{K} of the best",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=9, bbox=BOX)
save(fig, "figA_recovery")

# ============================================================ figB variance
fig, ax = plt.subplots(figsize=(6.2, 4.4))
ax.scatter(sm.mrna_l10, sm.log2spec, s=4, color=BLUE, alpha=.12, edgecolors="none")
ax.scatter(M.mrna_l10, M.med_log2, s=12, color="k", alpha=.7, edgecolors="none", label="Per-TF median")
ax.axhline(0, color=GREY, ls=":", lw=1)
ax.set_xlabel("Differential TF expression (log10 OV8/IOSE TPM)")
ax.set_ylabel("Per-sensor selectivity, log2(OV8/IOSE)")
ax.set_title("The signal lives within each TF — where mRNA cannot see it")
ax.text(.03, .97, f"Within-TF variance = {within:.2f}\nBetween-TF variance = {between:.2f}\n"
        f"within / between = {within/between:.1f}×", transform=ax.transAxes, va="top", fontsize=9, bbox=BOX)
ax.legend(fontsize=9, loc="lower right")
save(fig, "figB_variance")

# ============================================================ figC ROC
fig, ax = plt.subplots(figsize=(4.4, 4.4))
ax.plot(fpr, tpr, color=RED, lw=2.2)
ax.plot([0, 1], [0, 1], color=GREY, ls="--", lw=1)
ax.set_xlabel("False-positive rate"); ax.set_ylabel("True-positive rate")
ax.set_title("Can mRNA flag a TF with a selective enhancer?")
ax.text(.96, .06, f"AUC = {auc:.2f}\n(chance = 0.50)", transform=ax.transAxes, ha="right", va="bottom",
        fontsize=11, bbox=BOX)
ax.set_aspect("equal"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
save(fig, "figC_roc")

# ============================================================ figD quadrant
fig, ax = plt.subplots(figsize=(6.2, 5.0))
ax.scatter(M.mrna_l10, M.best_log2, s=9, color=GREY, alpha=.35, edgecolors="none", zorder=1)
ax.axvline(xthr, color=GREY, ls=":", lw=1); ax.axhline(ythr, color=GREY, ls=":", lw=1)
label_categories(ax, "mrna_l10", "best_log2",
                 line_for={"E2F8", "E2F6", "E2F3", "NKX2-1", "ZIC2", "PITX1"}, below={"MYC"})
ax.set_xlabel("Differential TF expression (log10 OV8/IOSE TPM)")
ax.set_ylabel("Best sensor's selectivity per TF, log2(OV8/IOSE)")
ax.set_title("Neither mRNA abundance nor prior literature finds the best enhancers")
ax.legend(fontsize=7.5, loc="lower right", framealpha=.95)
save(fig, "figD_quadrant")

# ============================================================ figE top-overexpressed
fig, ax = plt.subplots(figsize=(5.4, 4.2))
bins = np.linspace(M.best_log2.min(), M.best_log2.max(), 30)
ax.hist(M.best_log2, bins=bins, color=GREY, alpha=.6, density=True, label="All TFs")
ax.hist(topm.best_log2, bins=bins, color=RED, alpha=.55, density=True, label="Top 20 mRNA-overexpressed TFs")
ax.axvline(M.best_log2.median(), color=GREY, lw=1.5); ax.axvline(topm.best_log2.median(), color=RED, lw=1.5)
ax.set_xlabel("Best-sensor selectivity, log2(OV8/IOSE)"); ax.set_ylabel("Density")
ax.set_title("The most-overexpressed TFs are unremarkable sensors")
ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.0, 1.0), framealpha=.95)
ax.text(.03, .96, f"median best sensor\nall TFs: {2**M.best_log2.median():.2f}×\n"
        f"top-mRNA: {2**topm.best_log2.median():.2f}×", transform=ax.transAxes, va="top", fontsize=9, bbox=BOX)
save(fig, "figE_top_overexpressed")

# ============================================================ figF rank-rank
rho = stats.spearmanr(M.rank_mrna, M.rank_sensor)[0]
fig, ax = plt.subplots(figsize=(5.6, 5.0))
ax.scatter(M.rank_mrna, M.rank_sensor, s=8, color=GREY, alpha=.3, edgecolors="none", zorder=1)
label_categories(ax, "rank_mrna", "rank_sensor", line_for={"MYC", "E2F6", "E2F8", "NKX2-1"})
ax.set_xlabel("TF rank by mRNA differential (1 = most over-expressed)")
ax.set_ylabel("TF rank by best-sensor selectivity (1 = most selective)")
ax.set_title("mRNA rank vs enhancer rank — a scramble")
ax.text(.5, .98, f"Spearman ρ = {rho:.2f}", transform=ax.transAxes, ha="center", va="top", fontsize=10, bbox=BOX)
ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False)
save(fig, "figF_rank_rank")

print(f"\nDone — 7 figures (PDF + PNG) in {OUT}")
print(f"TFs={N}  r={r_ref:.2f}  AUC={auc:.2f}  within/between={within/between:.1f}x  recovery@{K}={nrec}/{K}")
