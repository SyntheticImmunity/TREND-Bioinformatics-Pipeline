"""Score the 10 TFBS variants of jaspar2016-E2F8-MA0865.1 against the PWM
and compare PWM-derived ordering against the assigned rank labels."""
import math

# PPM rows are A, C, G, T. Position 1-indexed in comments below.
PPM = {
    "A": [0.0319, 0,      0,      0,      0,      0,      0.0308, 0,      0.0202, 0.9412, 1.0,    0.9186],
    "C": [0.0319, 0.0323, 0,      0.9899, 0.9697, 0.9898, 0.0538, 0.9897, 0.9394, 0.0118, 0,      0.0233],
    "G": [0.0106, 0,      0.0108, 0,      0,      0.0102, 0.9154, 0,      0.0404, 0.0353, 0,      0.0116],
    "T": [0.9255, 0.9677, 0.9892, 0.0101, 0.0303, 0,      0,      0.0103, 0,      0.0118, 0,      0.0465],
}

# (variant_label, sequence, assigned_rank)
VARIANTS = [
    ("v1",  "TTTCCCGCCAAC",  1),
    ("v2",  "TTTCCCGCAAAA",  2),
    ("v3",  "TTTCCCGCCAAG",  3),
    ("v4",  "TTTCCCGTCAAA",  4),
    ("v5",  "TTTCCCGCCCAA",  5),
    ("v6",  "GTTCCCGCCAAA",  6),
    ("v7",  "TTTCCGGCCAAA",  7),
    ("v8",  "TTTCCCGCCTAA",  8),  # the clicked one
    ("v9",  "TTGCCCGCCAAA",  9),
    ("v10", "TTTTCCGCCAAA", 10),
]


def log_prob(seq):
    """log10 P(sequence | PWM). Treat 0 probabilities as 1e-9 to avoid -inf."""
    s = 0.0
    for i, base in enumerate(seq):
        p = PPM[base][i]
        s += math.log10(p if p > 0 else 1e-9)
    return s


# Score every variant.
scored = []
for label, seq, assigned in VARIANTS:
    lp = log_prob(seq)
    scored.append((label, seq, assigned, lp))

# What the rank WOULD be if assigned strictly by PWM log-probability.
by_logprob = sorted(scored, key=lambda r: -r[3])

# Find substitution position vs consensus.
consensus = "TTTCCCGCCAAA"
def diff(seq):
    diffs = [(i + 1, consensus[i], seq[i]) for i in range(len(seq)) if seq[i] != consensus[i]]
    return diffs

print(f"{'label':<5} {'sequence':<14} {'assigned':>9} {'logP':>10} {'rank-if-by-logP':>17}  substitutions")
print("-" * 95)
for label, seq, assigned, lp in scored:
    pwm_rank = next(i for i, r in enumerate(by_logprob) if r[0] == label) + 1
    diffs = diff(seq)
    diff_str = ", ".join(f"pos{p}: {a}->{b}" for p, a, b in diffs) or "(consensus)"
    print(f"{label:<5} {seq:<14} {assigned:>9} {lp:>10.4f} {pwm_rank:>17}  {diff_str}")
