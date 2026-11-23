#!/usr/bin/env python3
"""
MVRP decision rules and cell-test analysis (paper sections 4.5 and 6).

Every primary test ends in exactly one outcome: PASS, KILL or INCONCLUSIVE.
The regions are mutually exclusive by construction:

    KILL          upper CI bound  <  SESOI              (any effect is smaller than the
                                                          smallest effect of interest)
    PASS          lower CI bound  >  0
                  AND point estimate >= SESOI
                  AND every extra pass condition holds
    INCONCLUSIVE  everything else

PASS needs estimate >= SESOI, and the upper bound is always >= the estimate, so PASS
and KILL can never both be true. `python mvrp_rules.py selftest` checks this on a grid
of boundary cases.

Commands
  selftest                       boundary tests for every classifier
  s1     <s1.csv>  [--pilot]     spacing sweep: columns block,ratio,v10_mv
  c0     <c0.csv>                artefact screen: columns block,run,v10_mv
                                 (run = tone | notone | dummy | lead)
  power  <pilot_s1.csv>          simulated N for 80% power at the SESOI (pilot data only)

Dependencies: numpy.
"""
import csv, sys, math
import numpy as np

PHI = (1 + 5 ** 0.5) / 2
S1_RATIOS = [1.00, 1.15, 1.30, 1.45, 1.618, 1.75, 1.90, 2.10, 2.30]
SESOI_S1_MV = 5.0      # smallest effect of interest for the S1 excess at phi (mV)
SESOI_C0_MV = 5.0      # smallest tone effect of interest for C0 (mV)
ART_EQUIV = 0.25       # C0: artefact upper bound must be < 25% of the tone effect
ART_KILL = 0.50        # C0: artefact lower bound > 50% of the tone effect = artefact explains it

# ------------------------------------------------------------------ core classifier
def classify(est, lo, hi, sesoi, extra_pass=True, extra_kill=False):
    """Exclusive three-way rule. extra_kill can only add KILL when PASS is impossible."""
    if not (lo <= est <= hi) or any(map(math.isnan, (est, lo, hi))):
        return "INCONCLUSIVE"            # malformed interval: never pass or kill on it
    if hi < sesoi:
        return "KILL"
    if lo > 0 and est >= sesoi and extra_pass:
        return "PASS"
    if extra_kill and not (lo > 0 and est >= sesoi and extra_pass):
        return "KILL"
    return "INCONCLUSIVE"

def combine_all(outcomes):
    """Several contrasts that must all pass (e.g. edge-test D-B and D-C)."""
    if any(o == "KILL" for o in outcomes): return "KILL"
    if all(o == "PASS" for o in outcomes): return "PASS"
    return "INCONCLUSIVE"

# ------------------------------------------------------------------ S1: spacing sweep
def quad_fit_predict(x, y, x0):
    c = np.polyfit(x, y, 2); return float(np.polyval(c, x0))

def ns_basis(x, knots):
    """Natural cubic spline basis (ESL 5.4), K knots -> K columns incl. intercept."""
    x = np.asarray(x, float); K = len(knots); k = np.asarray(knots, float)
    def d(j):
        a = np.clip(x - k[j], 0, None) ** 3 - np.clip(x - k[K - 1], 0, None) ** 3
        return a / (k[K - 1] - k[j])
    cols = [np.ones_like(x), x] + [d(j) - d(K - 2) for j in range(K - 2)]
    return np.column_stack(cols)

def spline_fit_predict(x, y, x0):
    """Natural cubic spline, 3 df beyond the intercept (4 knots at the quantiles of x)."""
    knots = np.quantile(x, [0, 1 / 3, 2 / 3, 1])
    B = ns_basis(x, knots); coef, *_ = np.linalg.lstsq(B, y, rcond=None)
    return float((ns_basis([x0], knots) @ coef)[0])

def s1_stats(means):
    """means: dict ratio -> mean V10 (mV). Returns excess at phi (quadratic and spline) and LOO residuals."""
    r = np.array(sorted(means)); y = np.array([means[k] for k in r])
    iphi = int(np.argmin(abs(r - PHI)))
    mask = np.arange(len(r)) != iphi
    ex_q = y[iphi] - quad_fit_predict(r[mask], y[mask], r[iphi])
    ex_s = y[iphi] - spline_fit_predict(r[mask], y[mask], r[iphi])
    # leave-one-out residual for every setting i: e_i = y_i - quadratic fitted to all other settings, evaluated at r_i
    loo = {}
    for i in range(len(r)):
        m = np.arange(len(r)) != i
        loo[float(r[i])] = float(y[i] - quad_fit_predict(r[m], y[m], r[i]))
    phi_is_max = max(loo, key=loo.get) == float(r[iphi])
    return ex_q, ex_s, loo, phi_is_max

def s1_analyse(rows, reps=2000, seed=11):
    """rows: list of (block, ratio, v10_mv). Block = one full randomized pass over all 9 ratios."""
    rng = np.random.default_rng(seed)
    blocks = sorted({b for b, _, _ in rows})
    by_block = {b: {} for b in blocks}
    for b, r, v in rows: by_block[b].setdefault(r, []).append(v)
    def means_of(bs):
        acc = {}
        for b in bs:
            for r, vs in by_block[b].items(): acc.setdefault(r, []).extend(vs)
        return {r: float(np.mean(v)) for r, v in acc.items()}
    m = means_of(blocks); ex_q, ex_s, loo, phi_max = s1_stats(m)
    bq, bs = [], []
    for _ in range(reps):   # block bootstrap: resample whole passes
        samp = list(rng.choice(blocks, size=len(blocks), replace=True))
        mm = means_of(samp)
        if len(mm) < len(m): continue
        q, s, _, _ = s1_stats(mm); bq.append(q); bs.append(s)
    lo_q, hi_q = np.percentile(bq, [2.5, 97.5]); lo_s, hi_s = np.percentile(bs, [2.5, 97.5])
    out_q = classify(ex_q, lo_q, hi_q, SESOI_S1_MV, extra_pass=phi_max)
    out_s = classify(ex_s, lo_s, hi_s, SESOI_S1_MV, extra_pass=phi_max)
    # quadratic and spline must agree; any disagreement is INCONCLUSIVE
    final = out_q if out_q == out_s else "INCONCLUSIVE"
    return dict(blocks=len(blocks), excess_quad=ex_q, ci_quad=(lo_q, hi_q), excess_spline=ex_s, ci_spline=(lo_s, hi_s),
                loo=loo, phi_largest_loo=phi_max, outcome_quad=out_q, outcome_spline=out_s, outcome=final)

def s1_power(pilot_rows, target=0.80, max_blocks=40, sims=300, seed=5):
    """Simulated power at the SESOI from PILOT data only. Pilot data never enter the confirmatory set."""
    rng = np.random.default_rng(seed)
    res = np.array([v for _, _, v in pilot_rows]); sd = float(np.std(res - np.mean(res), ddof=1)) if len(res) > 2 else 5.0
    # use within-ratio residual SD from the pilot
    by = {}
    for _, r, v in pilot_rows: by.setdefault(r, []).append(v)
    if all(len(v) > 1 for v in by.values()):
        sd = float(np.sqrt(np.mean([np.var(v, ddof=1) for v in by.values()])))
    base = {r: 20.0 + 3.0 * (r - 1.6) for r in S1_RATIOS}   # smooth background; shape does not matter for a quadratic
    for nb in range(4, max_blocks + 1, 2):
        wins = 0
        for _ in range(sims):
            rows = []
            for b in range(nb):
                for r in S1_RATIOS:
                    mu = base[r] + (SESOI_S1_MV * 1.5 if abs(r - 1.618) < 1e-9 else 0.0)
                    rows.append((b, r, rng.normal(mu, sd)))
            wins += s1_analyse(rows, reps=200, seed=int(rng.integers(1e9)))["outcome"] == "PASS"
        if wins / sims >= target:
            return nb, wins / sims, sd
    return None, None, sd

# ------------------------------------------------------------------ C0: artefact screen
def c0_analyse(rows, reps=4000, seed=3):
    """rows: (block, run, v10_mv). D = tone - notone; artefacts = dummy - notone, lead - notone, per block."""
    rng = np.random.default_rng(seed)
    blk = {}
    for b, run, v in rows: blk.setdefault(b, {})[run] = v
    B = [b for b in blk if all(k in blk[b] for k in ("tone", "notone", "dummy", "lead"))]
    D = np.array([blk[b]["tone"] - blk[b]["notone"] for b in B])
    A1 = np.array([blk[b]["dummy"] - blk[b]["notone"] for b in B])
    A2 = np.array([blk[b]["lead"] - blk[b]["notone"] for b in B])
    def ci(x):
        bs = [np.mean(rng.choice(x, size=len(x))) for _ in range(reps)]
        return float(np.mean(x)), *np.percentile(bs, [2.5, 97.5])
    d, dlo, dhi = ci(D); a1, a1lo, a1hi = ci(A1); a2, a2lo, a2hi = ci(A2)
    scale = max(d, SESOI_C0_MV)
    equiv = (abs(a1lo) < ART_EQUIV * scale and abs(a1hi) < ART_EQUIV * scale and
             abs(a2lo) < ART_EQUIV * scale and abs(a2hi) < ART_EQUIV * scale)
    art_explains = (a1lo > ART_KILL * scale) or (a2lo > ART_KILL * scale)
    out = classify(d, dlo, dhi, SESOI_C0_MV, extra_pass=equiv, extra_kill=art_explains)
    return dict(blocks=len(B), D=(d, dlo, dhi), dummy=(a1, a1lo, a1hi), lead=(a2, a2lo, a2hi),
                artefacts_equivalent_to_zero=equiv, artefact_explains=art_explains, outcome=out,
                wording="PASS means: tone effect present and no artefact large enough to matter was detected. "
                        "It is an artefact screen, not proof that no artefact exists.")

# ------------------------------------------------------------------ self-test
def selftest():
    n = 0
    grid = [-10, -1, 0, 0.001, 1, 4.999, 5, 5.001, 10, 100]
    for est in grid:
        for lo in grid:
            for hi in grid:
                if not lo <= est <= hi: continue
                for ep in (True, False):
                    for ek in (True, False):
                        o = classify(est, lo, hi, 5.0, ep, ek); n += 1
                        is_kill_region = hi < 5.0
                        is_pass_region = lo > 0 and est >= 5.0 and ep
                        assert not (is_kill_region and is_pass_region), "regions overlap"
                        assert o in ("PASS", "KILL", "INCONCLUSIVE")
                        if is_pass_region: assert o == "PASS"
                        if is_kill_region: assert o == "KILL"
    assert classify(6, 7, 9, 5) == "INCONCLUSIVE"          # malformed interval
    assert classify(float("nan"), 0, 1, 5) == "INCONCLUSIVE"
    assert combine_all(["PASS", "PASS"]) == "PASS"
    assert combine_all(["PASS", "INCONCLUSIVE"]) == "INCONCLUSIVE"
    assert combine_all(["PASS", "KILL"]) == "KILL"
    # S1 sanity: smooth data with no excess must not pass; a large excess at phi must pass
    rng = np.random.default_rng(0)
    flat = [(b, r, 20 + 4 * (r - 1.6) ** 2 + rng.normal(0, 2)) for b in range(12) for r in S1_RATIOS]
    peak = [(b, r, 20 + 4 * (r - 1.6) ** 2 + (12 if abs(r - 1.618) < 1e-9 else 0) + rng.normal(0, 2)) for b in range(12) for r in S1_RATIOS]
    o_flat = s1_analyse(flat, reps=500)["outcome"]; o_peak = s1_analyse(peak, reps=500)["outcome"]
    assert o_flat != "PASS", o_flat
    assert o_peak == "PASS", o_peak
    # S1 with a near-zero or negative background stays defined (absolute contrast, no division)
    neg = [(b, r, -0.5 + rng.normal(0, 1)) for b in range(10) for r in S1_RATIOS]
    assert s1_analyse(neg, reps=300)["outcome"] in ("KILL", "INCONCLUSIVE")
    # C0 sanity
    c0 = [(b, run, v) for b in range(10) for run, v in
          (("notone", 10 + rng.normal(0, 1)), ("tone", 22 + rng.normal(0, 1)), ("dummy", 10 + rng.normal(0, 1)), ("lead", 10 + rng.normal(0, 1)))]
    assert c0_analyse(c0)["outcome"] == "PASS"
    c0b = [(b, run, v) for b in range(10) for run, v in
           (("notone", 10 + rng.normal(0, 1)), ("tone", 22 + rng.normal(0, 1)), ("dummy", 21 + rng.normal(0, 1)), ("lead", 10 + rng.normal(0, 1)))]
    assert c0_analyse(c0b)["outcome"] == "KILL"
    print(f"selftest OK: {n} boundary cases, every input gave exactly one outcome; S1 and C0 sanity cases behave as specified")

# ------------------------------------------------------------------ CLI
def read_rows(path, cols):
    with open(path) as f:
        return [tuple(r[c] if c == "run" else float(r[c]) for c in cols) for r in csv.DictReader(f)]

def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "selftest": return selftest()
    if cmd == "s1":
        rows = read_rows(sys.argv[2], ("block", "ratio", "v10_mv")); r = s1_analyse(rows)
        print(f"S1 · {r['blocks']} blocks · excess at phi (sampled-setting test, not peak localization)")
        print(f"  quadratic: {r['excess_quad']:+.2f} mV  95% CI {r['ci_quad'][0]:+.2f} to {r['ci_quad'][1]:+.2f}  -> {r['outcome_quad']}")
        print(f"  spline:    {r['excess_spline']:+.2f} mV  95% CI {r['ci_spline'][0]:+.2f} to {r['ci_spline'][1]:+.2f}  -> {r['outcome_spline']}")
        print("  LOO residuals (mV): " + ", ".join(f"{k:.3g}:{v:+.1f}" for k, v in r["loo"].items()))
        print(f"  phi has the largest LOO residual: {r['phi_largest_loo']}")
        print(f"  OUTCOME: {r['outcome']}   (SESOI {SESOI_S1_MV} mV; quadratic and spline must agree)")
    elif cmd == "c0":
        r = c0_analyse(read_rows(sys.argv[2], ("block", "run", "v10_mv")))
        for k in ("D", "dummy", "lead"):
            e, lo, hi = r[k]; print(f"  {k:6s} {e:+.2f} mV  95% CI {lo:+.2f} to {hi:+.2f}")
        print(f"  artefacts equivalent to zero (|bound| < {ART_EQUIV:.0%} of D): {r['artefacts_equivalent_to_zero']}")
        print(f"  OUTCOME: {r['outcome']}  ·  {r['wording']}")
    elif cmd == "power":
        nb, pw, sd = s1_power(read_rows(sys.argv[2], ("block", "ratio", "v10_mv")))
        print(f"pilot residual SD {sd:.2f} mV -> " + (f"{nb} blocks give power {pw:.2f} at 1.5x SESOI" if nb else "power target not reached within 40 blocks"))
    else:
        sys.exit(__doc__)

if __name__ == "__main__":
    main()
