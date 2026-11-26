#!/usr/bin/env python3
"""
Golden-mean locking test (positive control) · v1.0 · MVRP
Paper: "The Golden Ratio in Time" (Howell 2026), section 4.

Input CSV columns: block, ratio, a_lock   (a_lock = drive amplitude, V rms, at which locking first occurs)
Estimand: D = a_lock(phi) - median of a_lock over the 8 comparator ratios, per block, averaged over blocks.
SESOI    = 10% of the comparator median (averaged over blocks).
Interval : whole-block bootstrap, 4,000 replicates, 95% percentile.
Hierarchy: gates -> KILL (upper bound < SESOI) -> PASS (lower bound > 0 and D >= SESOI) -> INCONCLUSIVE.
Gates    : >= 10 complete blocks (all 9 ratios); per-block locking gate (rational controls lock first) passed.
Secondary: Spearman correlation between a_lock and continued-fraction sum (descriptive).

Usage: python golden_lock.py data.csv     |     python golden_lock.py selftest
"""
import csv, sys
import numpy as np

PHI = 1.6180
RATIOS = [1.3820, 1.4142, 1.5708, 1.5811, 1.6180, 1.7183, 1.7321, 1.9000, 2.1213]
SESOI_FRAC, REPS, MIN_BLOCKS = 0.10, 4000, 10

def cf_sum(x, n=6):
    """Sum of the first n continued-fraction partial quotients after the integer part (lower = more 'noble')."""
    s, f = 0, x - int(x)
    for _ in range(n):
        if f < 1e-9: s += 1000; break
        x = 1 / f; a = int(x); s += a; f = x - a
    return s

def per_block(rows):
    by = {}
    for b, r, a, gate in rows:
        by.setdefault(b, {})[round(r, 4)] = (a, gate)
    out = []
    for b, d in sorted(by.items()):
        if len(d) == 9 and all(g for _, g in d.values()):
            phi = d[round(PHI, 4)][0]; comp = np.median([v for k, (v, _) in d.items() if k != round(PHI, 4)])
            out.append((phi - comp, comp))
    return np.array(out)

def classify(est, lo, hi, sesoi):
    if hi < sesoi: return "KILL"
    if lo > 0 and est >= sesoi: return "PASS"
    return "INCONCLUSIVE"

def analyse(rows, seed=1):
    B = per_block(rows)
    if len(B) < MIN_BLOCKS: return dict(outcome="INCONCLUSIVE", reason=f"gate: {len(B)} complete gated blocks < {MIN_BLOCKS}")
    D, M = B[:, 0].mean(), B[:, 1].mean(); sesoi = SESOI_FRAC * M
    rng = np.random.default_rng(seed)
    boot = np.array([B[rng.integers(len(B), size=len(B)), 0].mean() for _ in range(REPS)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return dict(D=D, ci=(lo, hi), sesoi=sesoi, blocks=len(B), outcome=classify(D, lo, hi, sesoi), reason="")

def selftest():
    rng = np.random.default_rng(0)
    def sim(phi_gain, nb=10, gate=True):
        return [(b, r, (1.0 + (phi_gain if r == PHI else 0.0)) * (1 + 0.02 * cf_sum(r) ** -0.5) + rng.normal(0, 0.03), gate)
                for b in range(nb) for r in RATIOS]
    assert analyse(sim(0.30))["outcome"] == "PASS"
    assert analyse(sim(0.00))["outcome"] == "KILL"
    assert analyse(sim(0.30, nb=8))["outcome"] == "INCONCLUSIVE"
    assert analyse(sim(0.30, gate=False))["outcome"] == "INCONCLUSIVE"
    assert cf_sum(PHI) < cf_sum(1.4142) < cf_sum(1.9)
    print("selftest OK: PASS, KILL, block gate, locking gate, continued-fraction ordering")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    if sys.argv[1] == "selftest": selftest(); sys.exit()
    rows = [(r["block"], float(r["ratio"]), float(r["a_lock"]), r.get("gate", "1") == "1") for r in csv.DictReader(open(sys.argv[1]))]
    res = analyse(rows); print(res)
