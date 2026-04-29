"""How well do the assigned TFBS-variant ranks match the PWM log-probability
ordering? Samples 10 PWMs from the OvCa CSV that have all 10 variants present,
scores each variant against its PWM, and reports the per-PWM rank discrepancy.

Metrics per PWM:
  - max delta:       max |assigned_rank - logP_rank| across the 10 variants
  - exact matches:   variants where assigned_rank == logP_rank
  - top-3 preserved: assigned ranks {1,2,3} also among PWM-rank top 3
  - Spearman rho:    rank correlation (1.0 = perfect, 0 = random, -1 = inverted)

Aggregate at the bottom: mean Spearman over the 10 PWMs, mean max-delta,
fraction of PWMs where ranks 1-3 are preserved.
"""
import csv
import math
import random
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PPM_PATH = REPO / "references" / "all_ENCODE_MotifDb_ppm_no_NA_v1.txt"
CSV_PATH = (
    REPO / "project_data" / "final_enhancer_activity_results"
    / "ovarian_cancer" / "ovca_sensor_activity_result_concise.csv"
)


# ---------- PPM loader ----------
def parse_ppms(path):
    ppms = {}
    with open(path) as f:
        name = None
        rows = []
        for ln in f:
            ln = ln.rstrip("\n")
            if ln.startswith(">"):
                if name and len(rows) == 4:
                    ppms[name] = rows
                # Header may contain tab-separated junk after the canonical name.
                # Take the first whitespace-split token, then strip _vN suffix.
                first = ln[1:].strip().split()[0]
                first = re.sub(r"_v\d+$", "", first)
                name = first
                rows = []
            elif ln.strip():
                vals = [float(x) for x in ln.split()]
                rows.append(vals)
        if name and len(rows) == 4:
            ppms[name] = rows
    return ppms


def normalize_pwm_name(s):
    """Mirror dashboard backend `_normalize_pwm_name`: split on whitespace + strip _vN."""
    if not s:
        return ""
    head = s.split()[0]
    return re.sub(r"_v\d+$", "", head)


def log_prob(seq, ppm):
    """log10 P(seq | PWM). Substitute 1e-9 for exact zero probabilities."""
    base_to_row = {"A": 0, "C": 1, "G": 2, "T": 3}
    s = 0.0
    for i, b in enumerate(seq):
        if b not in base_to_row or i >= len(ppm[0]):
            return float("-inf")
        p = ppm[base_to_row[b]][i]
        s += math.log10(p if p > 0 else 1e-9)
    return s


def spearman_rho(xs, ys):
    """Spearman rank correlation between two equal-length integer-rank arrays."""
    n = len(xs)
    if n < 2:
        return float("nan")
    d2 = sum((a - b) ** 2 for a, b in zip(xs, ys))
    return 1 - (6 * d2) / (n * (n * n - 1))


# ---------- Load CSV: group variants by normalized PWM name ----------
def load_variants():
    by_pwm = defaultdict(list)  # normalized_pwm -> [(rank, seq, raw_pwm_name), ...]
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row.get("by_ppm_name") or ""
            seq = row.get("TFBS_sequence") or ""
            try:
                rk = int(row.get("rank") or 0)
            except ValueError:
                continue
            if not raw or not seq or rk <= 0:
                continue
            norm = normalize_pwm_name(raw)
            by_pwm[norm].append((rk, seq, raw))
    return by_pwm


def main():
    ppms = parse_ppms(PPM_PATH)
    by_pwm = load_variants()

    # Keep only PWMs with exactly 10 distinct variant ranks AND a matching PPM.
    eligible = []
    for pwm_name, variants in by_pwm.items():
        # Dedupe by (rank, seq) — multiple promoters can share a (PWM, rank, seq)
        # via different variable_regions; we just need one row per variant.
        unique = {}
        for rk, seq, _raw in variants:
            unique.setdefault(rk, seq)
        if len(unique) == 10 and pwm_name in ppms:
            eligible.append((pwm_name, unique))

    print(f"PWMs with all 10 variants present and a known PPM: {len(eligible)}")
    print()

    random.seed(11)
    sample = random.sample(eligible, min(10, len(eligible)))

    rhos = []
    max_deltas = []
    top3_preserved_count = 0

    for pwm_name, unique in sample:
        ppm = ppms[pwm_name]
        scored = []
        for rk in sorted(unique):
            seq = unique[rk]
            lp = log_prob(seq, ppm)
            scored.append((rk, seq, lp))

        # PWM rank: sort by descending logP, assign 1..10. Ties broken by
        # (logP, sequence) so the ordering is stable and reproducible.
        sorted_by_lp = sorted(scored, key=lambda r: (-r[2], r[1]))
        pwm_rank_of = {r[0]: i + 1 for i, r in enumerate(sorted_by_lp)}

        deltas = [abs(rk - pwm_rank_of[rk]) for rk, _, _ in scored]
        exact = sum(1 for d in deltas if d == 0)
        max_d = max(deltas)
        rho = spearman_rho(
            [rk for rk, _, _ in scored],
            [pwm_rank_of[rk] for rk, _, _ in scored],
        )

        # Are the top-3 preserved as a SET?
        assigned_top3 = {1, 2, 3}
        pwm_top3 = {rk for rk, _, _ in scored if pwm_rank_of[rk] <= 3}
        top3_match = assigned_top3 == pwm_top3
        if top3_match:
            top3_preserved_count += 1

        rhos.append(rho)
        max_deltas.append(max_d)

        print(f"PWM: {pwm_name}")
        print(
            f"  Spearman rho = {rho:+.3f}   exact matches = {exact}/10   "
            f"max rank delta = {max_d}   top-3 preserved = {top3_match}"
        )
        print(f"  {'rk':>3} {'seq':<14} {'logP':>8} {'pwm_rk':>7} {'delta':>4}")
        for rk, seq, lp in scored:
            print(
                f"  {rk:>3} {seq:<14} {lp:>8.3f} {pwm_rank_of[rk]:>7} "
                f"{abs(rk - pwm_rank_of[rk]):>4}"
            )
        print()

    print("=" * 70)
    print(f"Aggregate over {len(sample)} PWMs:")
    print(f"  Mean Spearman rho:           {sum(rhos)/len(rhos):+.3f}")
    print(f"  Median Spearman rho:         {sorted(rhos)[len(rhos)//2]:+.3f}")
    print(f"  Mean max rank delta:         {sum(max_deltas)/len(max_deltas):.2f}")
    print(f"  Worst max rank delta:        {max(max_deltas)}")
    print(
        f"  Top-3 preserved as a set:    "
        f"{top3_preserved_count}/{len(sample)} PWMs"
    )


if __name__ == "__main__":
    main()
