#!/usr/bin/env python
"""Build the T-cell per-variant table (mirror of trend_ovca_variants.csv) and
print the key replication stats vs OvCa. stim = activation 'on', rest = 'off';
selectivity = log2(stim/rest), raw (no pseudocount), matching the OvCa bundle."""
import re, numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"C:\Dev\TREND_bioinformatics_pipeline")
PWM_FILE = ROOT / "references" / "all_ENCODE_MotifDb_ppm_no_NA_v1.txt"
CSV = ROOT / "project_data" / "final_enhancer_activity_results" / "T_cell_activation" / "activation_responsive_enhancer_screening_result_donor1.csv"
OUT = ROOT / "revision_analysis" / "standalone_tcell"
OUT.mkdir(parents=True, exist_ok=True)
PSEUDO = 1e-3; FLOOR = 0.1
BASES = "ACGT"; BIDX = {b: i for i, b in enumerate(BASES)}
S, R = "median_stim_Lib4_RD_ratio_r1", "median_rest_Lib4_RD_ratio_r1"

def load_pwms():
    pwms, name, rows = {}, None, []
    with PWM_FILE.open() as fh:
        for raw in fh:
            line = raw.strip()
            if not line: continue
            if line.startswith(">"):
                if name and len(rows) == 4: pwms[name] = np.array(rows, float)
                name = line[1:].split()[0]; rows = []
            else: rows.append([float(x) for x in line.split()])
    if name and len(rows) == 4: pwms[name] = np.array(rows, float)
    for k, m in pwms.items():
        m = m + PSEUDO; pwms[k] = m / m.sum(axis=0, keepdims=True)
    return pwms

def rel_affinity(seq, ppm):
    W, L = ppm.shape[1], len(seq)
    if L < W: return np.nan
    colmax = ppm.max(axis=0); best = 0.0
    for off in range(0, L - W + 1):
        sub = seq[off:off + W]
        try: idx = [BIDX[b] for b in sub]
        except KeyError: continue
        best = max(best, float(np.prod(ppm[idx, range(W)] / colmax)))
    return best if best > 0 else np.nan

pwms = load_pwms()
df = pd.read_csv(CSV)
df = df[df[S].notna() & df[R].notna()].copy()
df["pwm"] = df["by_ppm_name"].map(lambda b: re.sub(r"_v\d+$", "", b) if isinstance(b, str) else None)
df["lookup"] = df["pwm"].map(lambda k: k.split()[0] if isinstance(k, str) else None)

aff, nrep = [], []
for _, r in df.iterrows():
    seq, ppm = r["TFBS_sequence"], pwms.get(r["lookup"])
    aff.append(rel_affinity(seq, ppm) if (ppm is not None and isinstance(seq, str)) else np.nan)
    vr = r["variable_region"]
    nrep.append(vr.count(seq) if isinstance(vr, str) and isinstance(seq, str) and seq else np.nan)
df["rel_affinity"] = aff; df["n_repeats"] = nrep
df = df[df["rel_affinity"].notna()].copy()
df["log2r"] = np.log2(df[S] / df[R])

out = df.rename(columns={"TF_name_human_curated": "tf", "promoter_name": "promoter",
                         "TFBS_sequence": "tfbs_sequence", S: "stim", R: "rest"})
out = out[["pwm", "tf", "promoter", "tfbs_sequence", "rel_affinity", "n_repeats", "stim", "rest", "log2r"]]
out.to_csv(OUT / "trend_tcell_variants.csv", index=False)
print(f"wrote {len(out)} variants across {out.pwm.nunique()} PWMs -> {OUT/'trend_tcell_variants.csv'}")

# ---- replication stats ----
print(f"\nneutral center (KDE mode) of log2(stim/rest):")
from scipy import stats
lr = out.log2r.values
grid = np.linspace(lr.min(), lr.max(), 2000); center = grid[np.argmax(stats.gaussian_kde(lr)(grid))]
print(f"  center = {center:+.3f} log2   (0 = ratio 1)")
for T in (1, 2):
    up = int((lr - center >= T).sum()); dn = int((lr - center <= -T).sum())
    print(f"  |dev|>={T}: stim-selective={up}  rest-selective={dn}  ratio={up/max(dn,1):.2f}")

rows = []
for k, g in out.groupby("pwm"):
    cons = g.loc[g.rel_affinity.idxmax()]; elig = g[g.stim >= FLOOR]
    if elig.empty: continue
    best = elig.loc[elig.log2r.idxmax()]
    rows.append(dict(cons_spec=cons.log2r, best_spec=best.log2r, cons_stim=cons.stim,
                     dT=np.log2(best.stim/cons.stim), dN=np.log2(best.rest/cons.rest)))
Sd = pd.DataFrame(rows); Sd["gain"] = 2**(Sd.best_spec - Sd.cons_spec)
print(f"\ndecomposition across {len(Sd)} PWMs (best - consensus):")
print(f"  median d-stim={Sd.dT.median():+.2f} ({2**Sd.dT.median():.2f}x)  median d-rest={Sd.dN.median():+.2f} ({2**Sd.dN.median():.2f}x)")
print(f"  PWMs needing non-consensus for >=2x: {(Sd.gain>=2).mean()*100:.1f}%")
Sd = Sd.sort_values("best_spec", ascending=False).reset_index(drop=True)
for pct in [10, 20]:
    s = Sd.head(max(3, int(len(Sd)*pct/100)))
    print(f"  top {pct}%: %gain>=2 = {(s.gain>=2).mean()*100:.0f}")
print("\nnecessity (threshold counterfactual):")
for thr in [2, 4, 8]:
    l2 = np.log2(thr)
    full = (Sd.best_spec >= l2).sum(); cons = ((Sd.cons_stim >= FLOOR) & (Sd.cons_spec >= l2)).sum()
    print(f"  >={thr}x: full={full} cons-only={cons} missed={100*(full-cons)/max(full,1):.0f}%")
# Goldilocks
pcts = []
for k, g in out.groupby("pwm"):
    g = g[g.stim >= FLOOR]
    if len(g) < 4: continue
    pcts.append(100 * (g.rel_affinity < g.loc[g.log2r.idxmax(), "rel_affinity"]).mean())
pcts = np.array(pcts)
print(f"\nGoldilocks (best variant's within-PWM affinity rank, n={len(pcts)} PWMs):")
print(f"  low(<20%)={100*(pcts<20).mean():.0f}%  mid={100*((pcts>=20)&(pcts<80)).mean():.0f}%  near-consensus(>=80%)={100*(pcts>=80).mean():.0f}%")
