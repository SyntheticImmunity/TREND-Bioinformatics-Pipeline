#!/usr/bin/env python
"""TF mRNA abundance does NOT predict enhancer activity/selectivity.

Shows, several ways, that you cannot shortcut the TREND screen with RNA-seq
differential TF expression. Joins per-TF mRNA (OV8 vs IOSE TPM) to the ovarian
sensor screen (per-sensor OV8/IOSE selectivity).

Outputs vector PDF + PNG into mrna_figs/:
  fig0_reference          reproduction of the current Fig S3A (flat scatter)
  figA_recovery           mRNA-ranked selection recovers ~no top enhancers (vs random/screen)
  figB_variance           within-TF sensor spread dwarfs any mRNA trend (the 'why')
  figC_roc                mRNA as a classifier of selective TFs -> AUC ~ 0.5
  figD_quadrant           wasted (high mRNA/no sensor) vs missed (low mRNA/great sensor)
  figE_top_overexpressed  the most-overexpressed TFs are unremarkable sensors
  figF_rank_rank          mRNA rank vs sensor-selectivity rank: a scramble
"""
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

HERE = Path(__file__).resolve().parent
OUT = HERE / "mrna_figs"; OUT.mkdir(exist_ok=True)
RNA = Path(r"d:\Dropbox (Personal)\paper writing working folder\ovarian cancer"
           r"\restructure for Cell resource\TREND Cell revision 061526\data for figures"
           r"\RNAseq_TPM_OV8_and_IOSE_050724.csv")
SEN = HERE.parent / "project_data" / "final_enhancer_activity_results" / "ovarian_cancer" / "ovca_sensor_activity_result_concise.csv"
EPS = 0.1
RED, BLUE, GREY, GREEN = "#d1495b", "#1f6feb", "#8b949e", "#2da44e"

def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig); print("  wrote", name)

# ----------------------------------------------------------------- load + join
rna = pd.read_csv(RNA)
rna["OV8_TPM"] = pd.to_numeric(rna.OV8_TPM, errors="coerce")
rna["IOSE_TPM"] = pd.to_numeric(rna.IOSE_TPM, errors="coerce")
rna = rna.dropna(subset=["OV8_TPM", "IOSE_TPM"])
rna["mrna_l10"] = np.log10((rna.OV8_TPM + EPS) / (rna.IOSE_TPM + EPS))
rna = rna[rna[["OV8_TPM", "IOSE_TPM"]].max(axis=1) > 1]   # expressed only

sen = pd.read_csv(SEN).dropna(subset=["mean_OV8_RD_ratio", "mean_IOSE_RD_ratio"])
sen = sen[(sen.mean_OV8_RD_ratio > 0) & (sen.mean_IOSE_RD_ratio > 0)]
sen["log2spec"] = np.log2(sen.mean_OV8_RD_ratio / sen.mean_IOSE_RD_ratio)

per_tf = sen.groupby("TF_name_human_curated").agg(
    n=("log2spec", "size"), med_log2=("log2spec", "median"),
    best_log2=("log2spec", "max")).reset_index().rename(columns={"TF_name_human_curated": "tf"})
M = per_tf.merge(rna[["hgnc_symbol", "mrna_l10"]], left_on="tf", right_on="hgnc_symbol", how="inner")
print(f"joined {len(M)} expressed TFs; median {int(M.n.median())} sensors/TF")
M["good"] = M.best_log2 >= 1   # TF has a >=2x tumour-selective sensor
N = len(M)

# =========================================================== fig0 reference (current S3A)
r = stats.pearsonr(M.mrna_l10, M.med_log2)[0]
fig, ax = plt.subplots(figsize=(4.6, 4.2))
ax.scatter(M.mrna_l10, 2 ** M.med_log2, s=10, color="k", alpha=.5, edgecolors="none")
ax.axhline(1, color=GREY, ls=":", lw=1)
ax.set_xlabel("Differential TF expression (log10 OV8/IOSE TPM)")
ax.set_ylabel("Median enhancer selectivity (OV8/IOSE)")
ax.set_title("Current view: TF mRNA vs enhancer selectivity")
ax.text(.97, .95, f"r = {r:.2f}", transform=ax.transAxes, ha="right", va="top", fontsize=11)
save(fig, "fig0_reference")

# =========================================================== figA recovery curve
order = M.sort_values("mrna_l10", ascending=False).reset_index(drop=True)
K = 50
target = set(M.sort_values("best_log2", ascending=False).head(K).tf)
xs = np.arange(1, N + 1)
mrna_rec = np.cumsum([1 if tf in target else 0 for tf in order.tf]) / K
rand_rec = xs / N                         # hypergeometric expectation
screen_rec = np.minimum(xs, K) / K        # perfect (screen-guided)
fig, ax = plt.subplots(figsize=(5.6, 4.4))
ax.plot(xs, screen_rec * 100, color=GREEN, lw=2, label="Screen-guided (ideal)")
ax.plot(xs, mrna_rec * 100, color=RED, lw=2.2, label="mRNA-ranked selection")
ax.plot(xs, rand_rec * 100, color=GREY, lw=1.5, ls="--", label="Random selection")
ax.axvline(K, color="k", ls=":", lw=.8)
nrec = int(mrna_rec[K - 1] * K)
ax.annotate(f"Top {K} TFs by mRNA\nrecover {nrec}/{K} of the best",
            (K, mrna_rec[K - 1] * 100), xytext=(K + 40, 18), fontsize=9,
            arrowprops=dict(arrowstyle="->", color="k", lw=.8))
ax.set_xlabel("Number of TFs selected"); ax.set_ylabel(f"% of the {K} most-selective enhancers recovered")
ax.set_title("Selecting enhancers by TF mRNA is no better than chance")
ax.legend(fontsize=9, loc="upper left"); ax.set_xlim(0, N); ax.set_ylim(0, 100)
save(fig, "figA_recovery")

# =========================================================== figB within vs between variance
within = sen.groupby("TF_name_human_curated").log2spec.var().mean()
between = per_tf.med_log2.var()
sm = sen.merge(M[["tf", "mrna_l10"]], left_on="TF_name_human_curated", right_on="tf", how="inner")
fig, ax = plt.subplots(figsize=(6.2, 4.4))
ax.scatter(sm.mrna_l10, sm.log2spec, s=4, color=BLUE, alpha=.12, edgecolors="none")
ax.scatter(M.mrna_l10, M.med_log2, s=12, color="k", alpha=.7, edgecolors="none", label="Per-TF median")
ax.axhline(0, color=GREY, ls=":", lw=1)
ax.set_xlabel("Differential TF expression (log10 OV8/IOSE TPM)")
ax.set_ylabel("Per-sensor selectivity, log2(OV8/IOSE)")
ax.set_title("The signal lives within each TF — where mRNA cannot see it")
ax.text(.03, .97, f"Within-TF variance = {within:.2f}\nBetween-TF variance = {between:.2f}\n"
        f"within / between = {within/between:.1f}×", transform=ax.transAxes, va="top", fontsize=9,
        bbox=dict(boxstyle="round", fc="white", ec=GREY, alpha=.9))
ax.legend(fontsize=9, loc="upper right")
save(fig, "figB_variance")

# =========================================================== figC ROC
score = M.mrna_l10.values; label = M.good.values
thr = np.sort(np.unique(score))[::-1]
tpr = [0.0]; fpr = [0.0]
P = label.sum(); Nn = (~label).sum()
for t in thr:
    pred = score >= t
    tpr.append((pred & label).sum() / P); fpr.append((pred & ~label).sum() / Nn)
pos = score[label]; neg = score[~label]
auc = stats.mannwhitneyu(pos, neg, alternative="two-sided").statistic / (len(pos) * len(neg))
fig, ax = plt.subplots(figsize=(4.4, 4.4))
ax.plot(fpr, tpr, color=RED, lw=2.2)
ax.plot([0, 1], [0, 1], color=GREY, ls="--", lw=1)
ax.set_xlabel("False-positive rate"); ax.set_ylabel("True-positive rate")
ax.set_title("Can mRNA flag a TF with a selective enhancer?")
ax.text(.96, .06, f"AUC = {auc:.2f}\n(chance = 0.50)", transform=ax.transAxes, ha="right", va="bottom",
        fontsize=11, bbox=dict(boxstyle="round", fc="white", ec=GREY, alpha=.9))
ax.set_aspect("equal"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
save(fig, "figC_roc")

# =========================================================== figD quadrant
xthr = np.log10(2)   # >=2-fold mRNA up
ythr = 1.0           # >=2x selective best sensor
fig, ax = plt.subplots(figsize=(5.4, 4.6))
ax.scatter(M.mrna_l10, M.best_log2, s=10, color="k", alpha=.45, edgecolors="none")
ax.axvline(xthr, color=GREY, ls=":", lw=1); ax.axhline(ythr, color=GREY, ls=":", lw=1)
hi_m = M.mrna_l10 >= xthr; hi_s = M.best_log2 >= ythr
wasted = int((hi_m & ~hi_s).sum()); missed = int((~hi_m & hi_s).sum())
both = int((hi_m & hi_s).sum())
ax.text(.97, .04, f"High mRNA, no selective sensor\n(wasted leads): {wasted}", transform=ax.transAxes,
        ha="right", va="bottom", fontsize=8, color=RED)
ax.text(.03, .97, f"Flat mRNA, selective sensor\n(missed by RNA-seq): {missed}", transform=ax.transAxes,
        ha="left", va="top", fontsize=8, color=BLUE)
for tf in ["PAX8", "E2F7", "MYC"]:
    row = M[M.tf == tf]
    if len(row):
        ax.annotate(tf, (row.mrna_l10.iloc[0], row.best_log2.iloc[0]), fontsize=8,
                    xytext=(4, 4), textcoords="offset points")
        ax.scatter(row.mrna_l10, row.best_log2, s=22, color=GREEN, zorder=5)
ax.set_xlabel("Differential TF expression (log10 OV8/IOSE TPM)")
ax.set_ylabel("Best-sensor selectivity, log2(OV8/IOSE)")
ax.set_title("mRNA over-expression ≠ a usable enhancer")
save(fig, "figD_quadrant")

# =========================================================== figE top-overexpressed unremarkable
topm = M.sort_values("mrna_l10", ascending=False).head(20)
fig, ax = plt.subplots(figsize=(5.2, 4.2))
bins = np.linspace(M.best_log2.min(), M.best_log2.max(), 30)
ax.hist(M.best_log2, bins=bins, color=GREY, alpha=.6, density=True, label="All TFs")
ax.hist(topm.best_log2, bins=bins, color=RED, alpha=.6, density=True, label="Top 20 mRNA-overexpressed TFs")
ax.axvline(M.best_log2.median(), color=GREY, lw=1.5); ax.axvline(topm.best_log2.median(), color=RED, lw=1.5)
ax.set_xlabel("Best-sensor selectivity, log2(OV8/IOSE)"); ax.set_ylabel("Density")
ax.set_title("The most-overexpressed TFs are unremarkable sensors")
ax.text(.97, .95, f"median best sensor\nall: {2**M.best_log2.median():.2f}×\n"
        f"top-mRNA: {2**topm.best_log2.median():.2f}×", transform=ax.transAxes, ha="right", va="top", fontsize=9)
ax.legend(fontsize=8, loc="center right")
save(fig, "figE_top_overexpressed")

# =========================================================== figF rank-rank
M2 = M.copy()
M2["rank_mrna"] = M2.mrna_l10.rank(ascending=False)
M2["rank_sensor"] = M2.best_log2.rank(ascending=False)
rho = stats.spearmanr(M2.rank_mrna, M2.rank_sensor)[0]
fig, ax = plt.subplots(figsize=(4.8, 4.6))
ax.scatter(M2.rank_mrna, M2.rank_sensor, s=8, color="k", alpha=.4, edgecolors="none")
# highlight discordant: top sensor but poor mRNA rank, and top mRNA but poor sensor
disc = pd.concat([
    M2.sort_values("best_log2", ascending=False).head(3),
    M2.sort_values("mrna_l10", ascending=False).head(3)])
for _, row in disc.iterrows():
    ax.scatter(row.rank_mrna, row.rank_sensor, s=24, color=RED, zorder=5)
    ax.annotate(row.tf, (row.rank_mrna, row.rank_sensor), fontsize=8, xytext=(4, 4), textcoords="offset points")
ax.set_xlabel("TF rank by mRNA differential"); ax.set_ylabel("TF rank by best-sensor selectivity")
ax.set_title("mRNA rank vs enhancer rank — a scramble")
ax.text(.97, .06, f"Spearman ρ = {rho:.2f}", transform=ax.transAxes, ha="right", va="bottom", fontsize=10,
        bbox=dict(boxstyle="round", fc="white", ec=GREY, alpha=.9))
save(fig, "figF_rank_rank")

print("\nDone — figures in", OUT)
