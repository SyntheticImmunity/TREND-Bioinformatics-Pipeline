"""Quick audit: how peaked are the PWMs in references/all_ENCODE_MotifDb_ppm_no_NA_v1.txt?

Computes per-position information content (bits) for a random sample of PWMs,
plus aggregate stats — to sanity-check whether the source data really is as
clean as the rendered logos suggest, or whether something upstream (e.g.,
pseudocount-free conversion of low-count count-matrices) is making them
look artificially peaked.
"""
import math
import random
from pathlib import Path

PPM_PATH = Path(__file__).resolve().parents[1] / "references" / "all_ENCODE_MotifDb_ppm_no_NA_v1.txt"


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
                name = ln[1:].strip().split()[0]
                rows = []
            elif ln.strip():
                vals = [float(x) for x in ln.split()]
                rows.append(vals)
        if name and len(rows) == 4:
            ppms[name] = rows
    return ppms


def ic(col):
    h = 0.0
    for p in col:
        if p > 0:
            h -= p * math.log2(p)
    return max(0.0, 2.0 - h)


def main():
    ppms = parse_ppms(PPM_PATH)
    print(f"Total PPMs in file: {len(ppms)}\n")

    random.seed(7)
    sample_names = random.sample(list(ppms.keys()), min(20, len(ppms)))

    all_ic = []
    zero_p = 0
    total_cells = 0

    print(
        f"{'PWM':60} | {'len':>3} | {'meanIC':>6} | "
        f"{'>1.5':>4} | {'>1.9':>4} | consensus"
    )
    print("-" * 130)
    for nm in sample_names:
        rows = ppms[nm]
        n = len(rows[0])
        cols = [[rows[b][i] for b in range(4)] for i in range(n)]
        ics = [ic(c) for c in cols]
        consensus = "".join(
            "ACGT"[max(range(4), key=lambda b: rows[b][i])] for i in range(n)
        )
        n_peaked = sum(1 for v in ics if v > 1.5)
        n_extreme = sum(1 for v in ics if v > 1.9)
        n_zero = sum(1 for c in cols for p in c if p == 0)
        all_ic.extend(ics)
        zero_p += n_zero
        total_cells += n * 4
        print(
            f"{nm[:58]:60} | {n:>3} | {sum(ics) / n:>6.2f} | "
            f"{n_peaked:>4} | {n_extreme:>4} | {consensus}"
        )

    print()
    print(f"Aggregate over {len(sample_names)} sampled PWMs:")
    print(
        f"  Mean IC across all positions:        "
        f"{sum(all_ic) / len(all_ic):.3f} bits (max = 2.0)"
    )
    print(
        f"  Positions with IC > 1.5 (peaked):    "
        f"{sum(1 for v in all_ic if v > 1.5) / len(all_ic) * 100:.1f}%"
    )
    print(
        f"  Positions with IC > 1.9 (extreme):   "
        f"{sum(1 for v in all_ic if v > 1.9) / len(all_ic) * 100:.1f}%"
    )
    print(
        f"  Positions with IC < 0.5 (low info):  "
        f"{sum(1 for v in all_ic if v < 0.5) / len(all_ic) * 100:.1f}%"
    )
    print(
        f"  Probability cells == 0 exactly:      "
        f"{zero_p / total_cells * 100:.1f}% of all (base, position) cells"
    )


if __name__ == "__main__":
    main()
