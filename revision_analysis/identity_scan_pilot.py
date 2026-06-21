#!/usr/bin/env python
"""
Pass-2 identity scan — PILOT on the tumor-gain gainers (OvCa).
==============================================================
Question: for variants whose BEST (most tumor-specific) sequence gained tumor
ACTIVITY vs the consensus, is that variant still read by its assigned TF, or did
a single-/few-nt change move in a DIFFERENT TF?

Method (FIMO-style, self-contained numpy):
  * log-odds PSSM per PWM (uniform background, column pseudocount)
  * best-window score over both strands / all offsets for each (variant, PWM)
  * Stage A: rank all 6,012 PWMs per variant by a fast Gaussian-null p-value
  * Stage B: EXACT upper-tail p-value (DP over discretized column score pmfs)
             for the assigned PWM + the top-ranked PWMs
  * family collapse: a hit counts as a "switch" only if it is a DIFFERENT TF
    family — different TF-name root AND low motif correlation with the assigned
    PWM (handles the 6,012-PWM / 1,370-TF redundancy, e.g. MYC x42, E2F x38)

Output: per-variant call (retained / switched / ambiguous / lost) + confidence,
written to identity_scan_pilot.csv, plus a summary and worked examples.
"""
import re, numpy as np, pandas as pd
from pathlib import Path
from scipy import stats

ROOT = Path(r"C:\Dev\TREND_bioinformatics_pipeline")
PWM_FILE = ROOT / "references" / "all_ENCODE_MotifDb_ppm_no_NA_v1.txt"
CSV = ROOT / "revision_analysis" / "standalone" / "trend_ovca_variants.csv"
OUT = ROOT / "revision_analysis"
BASES = "ACGT"; BIDX = {b: i for i, b in enumerate(BASES)}
BG = 0.25; PSEUDO = 1e-3; SCALE = 20
FLOOR = 0.1
P_SIG = 1e-4            # per-match significance
SWITCH_MARGIN = 2.0     # log10(p_own / p_other) needed to call a switch
FAM_CORR = 0.60         # motif correlation -> same family

# ---------------------------------------------------------------- PWM parsing
def load_pwms():
    pwms, names, name, rows = [], [], None, []
    with PWM_FILE.open() as fh:
        for raw in fh:
            line = raw.strip()
            if not line: continue
            if line.startswith(">"):
                if name and len(rows) == 4: pwms.append(np.array(rows, float)); names.append(name)
                name = line[1:].split()[0]; rows = []
            else: rows.append([float(x) for x in line.split()])
    if name and len(rows) == 4: pwms.append(np.array(rows, float)); names.append(name)
    los, mu, var, width, ppms = [], [], [], [], []
    for m in pwms:
        m = m + PSEUDO; m = m / m.sum(axis=0, keepdims=True)
        lo = np.log2(m / BG)                       # 4 x w log-odds
        los.append(lo); ppms.append(m); width.append(lo.shape[1])
        mu.append(lo.mean(axis=0).sum()); var.append(lo.var(axis=0).sum())  # Gaussian null
    root = [re.split(r"[_\-]", n)[0] for n in names]
    return names, root, los, ppms, np.array(mu), np.array(var), np.array(width)

NAMES, ROOT, LOS, PPMS, MU, VAR, WIDTH = load_pwms()
NP = len(NAMES)
print(f"loaded {NP} PWMs")
# group PWM indices by width for vectorized scoring
BYW = {}
for i, w in enumerate(WIDTH): BYW.setdefault(int(w), []).append(i)
LOW = {w: np.stack([LOS[i] for i in idx]) for w, idx in BYW.items()}   # w -> (n,4,w)

def encode(seq):
    try: return np.array([BIDX[b] for b in seq], dtype=int)
    except KeyError: return None
def rc(e): return (3 - e)[::-1]

def best_scores(seq):
    """best-window log-odds of seq vs EVERY PWM -> array (NP,), -inf if unplaceable."""
    e = encode(seq)
    out = np.full(NP, -np.inf)
    if e is None: return out
    strands = [e]
    r = rc(e); strands.append(r)
    L = len(e)
    for w, lo_w in LOW.items():
        if w > L: continue
        wins = []
        for s in strands:
            for off in range(0, L - w + 1):
                wins.append(s[off:off + w])
        W = np.array(wins)                                  # (k,w)
        col = np.arange(w)
        sc = lo_w[:, W, col].sum(axis=2)                    # (n,k)
        best = sc.max(axis=1)
        for j, i in enumerate(BYW[w]): out[i] = best[j]
    return out

def exact_p(lo, score):
    """upper-tail p-value of a window score under uniform-bg null (exact DP)."""
    q = np.rint(lo * SCALE).astype(int)                     # 4 x w integer scores
    dist = np.array([1.0]); base = 0                        # dist[k] = P(sum == base+k)
    for j in range(q.shape[1]):
        vals = q[:, j]; lo_v, hi_v = vals.min(), vals.max()
        col = np.zeros(hi_v - lo_v + 1)
        for v in vals: col[v - lo_v] += BG
        dist = np.convolve(dist, col); base += lo_v
    thr = int(np.ceil(score * SCALE)) - base
    if thr <= 0: return 1.0
    if thr >= len(dist): return 1.0 / 4 ** q.shape[1]
    return float(dist[thr:].sum())

def motif_corr(a, b):
    """max correlation of two PPMs over offsets + RC (family test)."""
    def one(x, y):                      # x narrower or equal
        wx, wy = x.shape[1], y.shape[1]
        best = -1.0
        for off in range(0, wy - wx + 1):
            sub = y[:, off:off + wx]
            ov = min(wx, sub.shape[1])
            if ov < 4: continue
            c = np.corrcoef(x[:, :ov].ravel(), sub[:, :ov].ravel())[0, 1]
            if c > best: best = c
        return best
    brc = b[[3, 2, 1, 0], ::-1]
    if a.shape[1] <= b.shape[1]:
        return max(one(a, b), one(a, brc))
    return max(one(b, a), one(brc, a))

# ---------------------------------------------------------------- pilot set
df = pd.read_csv(CSV)
rows = []
for k, g in df.groupby("pwm"):
    cons = g.loc[g.rel_affinity.idxmax()]; elig = g[g.ov8 >= FLOOR]
    if elig.empty: continue
    best = elig.loc[elig.log2r.idxmax()]
    if best.promoter == cons.promoter: continue
    gain = best.log2r - cons.log2r
    dT = np.log2(best.ov8 / cons.ov8)
    if gain >= 1 and dT >= 0.5:        # >=2x specificity gain, tumor-activity driven
        rows.append(dict(pwm=k, tf=cons.tf, seq=best.tfbs_sequence,
                         gain=2 ** gain, dT=dT, best_ov8=best.ov8, best_log2r=best.log2r))
pilot = pd.DataFrame(rows).drop_duplicates("seq").reset_index(drop=True)
print(f"tumor-gain gainer pilot set: {len(pilot)} variants")

# library index + TF-family key per PWM. famkey strips trailing -/_ + digit groups
# REPEATEDLY so NKX6-1 -> NKX6 -> NKX and E2F3 -> E2F collapse consistently.
name2i = {n: i for i, n in enumerate(NAMES)}
def famkey(x):
    s = str(x).upper()
    while True:
        t = re.sub(r"[-_]?\d+$", "", s)
        if t == s or not t: break
        s = t
    return s
ROOTU = np.array([str(x).upper() for x in ROOT], dtype=object)
FAM = np.array([famkey(r) for r in ROOT], dtype=object)

# ---------------------------------------------------------------- scan
# "own family" = library PWMs whose TF root matches the curated TF (digits stripped)
# OR whose motif is highly correlated with the assigned PWM. A "switch" must beat
# the best own-family hit by >=SWITCH_MARGIN in log10 p AND be motif-dissimilar.
recs = []
n_found = 0
for _, r in pilot.iterrows():
    aname = str(r.pwm).split()[0]                          # first alias = assigned PWM (build convention)
    ai = name2i.get(aname); appm = PPMS[ai] if ai is not None else None
    n_found += ai is not None
    own_root = ROOTU[ai] if ai is not None else str(r.tf).upper()
    fams = {famkey(own_root), famkey(r.tf)}
    sc = best_scores(r.seq); finite = np.isfinite(sc)
    z = (sc - MU) / np.sqrt(VAR); papprox = stats.norm.sf(z); papprox[~finite] = 1.0
    samefam_name = np.isin(FAM, list(fams)) | (ROOTU == own_root)
    # best own-family hit (exact p)
    own_c = np.where(samefam_name & finite)[0]
    own_idx = own_c[np.argmin(papprox[own_c])] if len(own_c) else None
    p_own = exact_p(LOS[own_idx], sc[own_idx]) if own_idx is not None else 1.0
    # best DIFFERENT-family hit: skip same TF-family name AND motifs similar to assigned
    oth_idx = None
    for i in np.argsort(papprox)[:60]:
        if not finite[i] or samefam_name[i]: continue
        if appm is not None and motif_corr(appm, PPMS[i]) >= FAM_CORR: continue
        oth_idx = i; break
    p_oth = exact_p(LOS[oth_idx], sc[oth_idx]) if oth_idx is not None else 1.0
    oth_hit = NAMES[oth_idx] if oth_idx is not None else ""
    margin = np.log10(max(p_own, 1e-300)) - np.log10(max(p_oth, 1e-300))   # >0 => other stronger
    own_sig, oth_sig = p_own < P_SIG, p_oth < P_SIG
    if own_sig and oth_sig:
        call = "switched" if margin >= SWITCH_MARGIN else "dual"   # both bind; other dominates => replaced
    elif own_sig:
        call = "retained"
    elif oth_sig:
        call = "switched"
    elif p_own >= 1e-3 and p_oth >= 1e-3:
        call = "lost"
    else:
        call = "ambiguous"
    conf = "high" if (min(p_own, p_oth) < 0.05 / NP and (call != "switched" or margin >= 3)) else \
           ("low" if len(r.seq) <= 6 else "med")
    recs.append(dict(tf=r.tf, assigned=aname, seq=r.seq, len=len(r.seq), gain=round(r.gain, 2),
                     dT=round(r.dT, 2), p_ownfam=p_own, p_otherfam=p_oth, other_hit=oth_hit,
                     margin=round(float(margin), 2), call=call, confidence=conf))
res = pd.DataFrame(recs)
res.to_csv(OUT / "identity_scan_pilot.csv", index=False)
print(f"assigned PWM resolved (first alias): {n_found}/{len(pilot)}")

print("\n=== call distribution ===")
print(res.call.value_counts().to_string())
print("\n=== confidence x call ===")
print(pd.crosstab(res.call, res.confidence).to_string())
print(f"\nswitched variants: {(res.call=='switched').sum()}  "
      f"({100*(res.call=='switched').mean():.0f}% of tumor-gain gainers)")
print("\n=== example SWITCHED (single-/few-nt change moved a DIFFERENT TF in) ===")
ex = res[res.call == "switched"].sort_values("margin", ascending=False).head(10)
for _, r in ex.iterrows():
    print(f"  {r.tf:>10} -> {r.other_hit:<26} {r.seq:<20} gain {r.gain}x  "
          f"p_ownfam={r.p_ownfam:.0e} p_other={r.p_otherfam:.0e} margin={r.margin}")
print("\n=== example DUAL (keeps own TF AND gains a different TF site) ===")
for _, r in res[res.call == "dual"].sort_values("p_otherfam").head(8).iterrows():
    print(f"  {r.tf:>10} + {r.other_hit:<26} {r.seq:<20} gain {r.gain}x  "
          f"p_ownfam={r.p_ownfam:.0e} p_other={r.p_otherfam:.0e}")
print("\n=== example RETAINED (same TF family, affinity-tuned) ===")
for _, r in res[res.call == "retained"].sort_values("p_ownfam").head(6).iterrows():
    print(f"  {r.tf:>10}    {r.seq:<20} gain {r.gain}x  p_ownfam={r.p_ownfam:.0e}")
print("\n=== lost/ambiguous are mostly short/low-information sites ===")
for c in ("lost", "ambiguous", "retained", "dual", "switched"):
    s = res[res.call == c]
    if len(s): print(f"  {c:<10} n={len(s):<4} median len={s.len.median():.0f}")
print(f"\nwrote {OUT/'identity_scan_pilot.csv'}")
