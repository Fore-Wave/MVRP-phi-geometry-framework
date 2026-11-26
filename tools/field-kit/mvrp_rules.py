#!/usr/bin/env python3
"""
MVRP decision rules and cell-test analysis · v1.2 (paper sections 4.5 and 6; revised after XReview 29771c7e)

ONE DECISION HIERARCHY, used by every confirmatory test. Steps run in order; the first that fires decides.
    1  GATES         any eligibility gate fails (too few complete blocks, invalid fit, failed instrument
                     check, quadratic and spline disagree) ......................... INCONCLUSIVE
    2  KILL          the test's kill condition holds ................................ KILL
    3  PASS          the test's pass condition holds ................................ PASS
    4  otherwise ................................................................... INCONCLUSIVE
Single contrast:  KILL = upper bound < SESOI;  PASS = lower bound > 0 AND estimate >= SESOI AND extra conditions.
Conjunctive tests (all contrasts must pass, e.g. edge ΔDB and ΔDC): KILL if any contrast is KILL, PASS if all
are PASS, else INCONCLUSIVE. There are no disjunctive confirmatory families: S1 is decided on tone-ON only.

Commands
  selftest                                   boundary and combination tests for every rule
  schedule <S1|S1c|C0|pilot> <blocks> <seed> block schedule (order, tone, polarity), deterministic
  s1     <s1.csv>                            columns block,ratio,tone,v10_mv[,flag]  (tone = on|off)
  s1c    <s1c.csv>                           same columns, L0 = 6.0 cm with the 12.94 cm setting added
  c0     <c0.csv>                            columns block,run,v10_mv[,flag]  (run = tone|notone|dummy|lead)
  power  <pilot_s1.csv>                      deterministic N for S1 from the 4 pilot blocks

Data conventions
  v10_mv is sign-normalized: potential of the ANODE rod minus the CATHODE rod, in mV, 10 s after opening,
  minus the OCP measured the same way. The logger multiplies the raw differential reading by +1 when the
  left rod is the anode (odd blocks) and -1 when the right rod is (even blocks), so polarity never flips the sign.
  flag = 1 for runs flagged at the bench (OCP reset not reached in 10 min, or timing outside 20 ms).
  Flagged runs STAY in the primary analysis; a sensitivity analysis without them is always reported.
  Exclusion is only for a run with no V10 value (hardware failure, spill), recorded before unblinding.
  A block that lacks any primary run is dropped whole and replaced by the next scheduled block.

Dependencies: numpy.
"""
import csv, sys, math
import numpy as np

PHI = (1 + 5 ** 0.5) / 2
S1_RATIOS = [1.00, 1.15, 1.30, 1.45, 1.618, 1.75, 1.90, 2.10, 2.30]
L0_S1, L0_S1C = 8.0, 6.0                                  # reference lengths (cm)
ABS_SPACING_CM = 1.618 * L0_S1                            # 12.94 cm: the S1 phi spacing
S1C_RATIOS = sorted(S1_RATIOS + [round(ABS_SPACING_CM / L0_S1C, 4)])   # adds r = 2.1573 (12.94 cm at L0 = 6 cm)
SESOI_S1_MV = 5.0      # smallest S1 excess of interest (mV)
SESOI_C0_MV = 5.0      # smallest C0 tone effect of interest (mV)
ART_EQUIV = 0.25       # C0 equivalence margin: |artefact| < 25% of the tone effect D
ART_KILL = 0.50        # C0 artefact kill: artefact > 50% of D
BOOT_REPS = 4000       # block-bootstrap replicates for S1, S1c and C0
C0_BLOCKS = 10         # C0 uses a fixed 10 blocks
# deterministic S1 sample-size procedure (section 6, S1)
POWER = dict(pilot_blocks=4, design_effect_mv=1.5 * SESOI_S1_MV, target=0.80, n_grid=list(range(6, 31, 2)),
             n_max=30, sims=400, boot_reps=300, seed=20261124)

# ------------------------------------------------------------------ the hierarchy
def classify(est, lo, hi, sesoi, extra_pass=True):
    """Steps 2-4 for one contrast. Regions are exclusive: PASS needs est >= SESOI and hi >= est, so hi < SESOI is impossible."""
    if any(map(math.isnan, (est, lo, hi))) or not (lo <= est <= hi):
        return "INCONCLUSIVE"            # malformed interval is a failed gate
    if hi < sesoi: return "KILL"
    if lo > 0 and est >= sesoi and extra_pass: return "PASS"
    return "INCONCLUSIVE"

def combine_all(outcomes):
    """Conjunctive test: every contrast must pass."""
    if any(o == "KILL" for o in outcomes): return "KILL"
    if outcomes and all(o == "PASS" for o in outcomes): return "PASS"
    return "INCONCLUSIVE"

def decide(gates, kill, pass_):
    """Generic hierarchy. gates: list of (name, ok). Returns (outcome, reason)."""
    for name, ok in gates:
        if not ok: return "INCONCLUSIVE", f"gate failed: {name}"
    if kill: return "KILL", ""
    if pass_: return "PASS", ""
    return "INCONCLUSIVE", ""

# ------------------------------------------------------------------ schedules
def schedule(test, blocks, seed):
    """Deterministic block schedule. Polarity: left rod anode in odd blocks, right rod in even blocks.
    S1 / S1c / pilot: every block runs each ratio with tone ON and tone OFF (18 or 20 runs), random order,
    fresh electrolyte per block. C0: 4 runs per block (tone, notone, dummy, lead), random order."""
    rng = np.random.default_rng(seed); rows = []
    for b in range(1, blocks + 1):
        if test == "C0": runs = [("", r) for r in ("tone", "notone", "dummy", "lead")]
        else: runs = [(r, t) for r in (S1C_RATIOS if test == "S1c" else S1_RATIOS) for t in ("on", "off")]
        for pos, i in enumerate(rng.permutation(len(runs)), 1):
            r, t = runs[i]
            rows.append(dict(block=b, position=pos, ratio=r, tone_or_run=t, anode="left" if b % 2 else "right"))
    return rows

# ------------------------------------------------------------------ S1: spacing sweep
def quad_fit_predict(x, y, x0):
    c = np.polyfit(x, y, 2); return float(np.polyval(c, x0))

def ns_basis(x, knots):
    """Natural cubic spline basis (ESL 5.4), K knots -> K columns incl. intercept."""
    x = np.asarray(x, float); K = len(knots); k = np.asarray(knots, float)
    def d(j):
        a = np.clip(x - k[j], 0, None) ** 3 - np.clip(x - k[K - 1], 0, None) ** 3
        return a / (k[K - 1] - k[j])
    return np.column_stack([np.ones_like(x), x] + [d(j) - d(K - 2) for j in range(K - 2)])

def spline_fit_predict(x, y, x0):
    """Natural cubic spline, 3 df beyond the intercept (4 knots at the quantiles of x)."""
    knots = np.quantile(x, [0, 1 / 3, 2 / 3, 1])
    coef, *_ = np.linalg.lstsq(ns_basis(x, knots), y, rcond=None)
    return float((ns_basis([x0], knots) @ coef)[0])

def excess_at(means, target, exclude):
    """Observed mean m(target) minus the background prediction p(target), with the background (quadratic and
    spline) fitted to every setting not in `exclude`. Returns (quadratic excess, spline excess)."""
    r = np.array(sorted(means)); y = np.array([means[k] for k in r])
    keep = np.array([all(abs(v - e) > 1e-6 for e in exclude) for v in r])
    it = int(np.argmin(abs(r - target)))
    return (y[it] - quad_fit_predict(r[keep], y[keep], r[it]), y[it] - spline_fit_predict(r[keep], y[keep], r[it]))

def loo_residuals(means):
    r = np.array(sorted(means)); y = np.array([means[k] for k in r]); out = {}
    for i in range(len(r)):
        m = np.arange(len(r)) != i; out[float(r[i])] = float(y[i] - quad_fit_predict(r[m], y[m], r[i]))
    return out

def _block_means(rows, tone, keep_flagged=True):
    by = {}
    for row in rows:
        b, r, t, v = row[:4]; fl = row[4] if len(row) > 4 else 0
        if t != tone or (fl and not keep_flagged) or v is None or (isinstance(v, float) and math.isnan(v)): continue
        by.setdefault(b, {}).setdefault(round(r, 4), []).append(v)
    return by

def _bootstrap_excess(by, settings, targets, exclude, reps, seed):
    """Whole-block bootstrap of the excess at each target. Only complete blocks are used."""
    blocks = [b for b in sorted(by) if all(round(s, 4) in by[b] for s in settings)]
    def means(bs):
        return {s: float(np.mean([v for b in bs for v in by[b][round(s, 4)]])) for s in settings}
    m = means(blocks) if blocks else {}
    est = {t: excess_at(m, t, exclude) for t in targets} if blocks else {}
    rng = np.random.default_rng(seed); boots = {t: ([], []) for t in targets}
    for _ in range(reps if len(blocks) >= 2 else 0):
        mm = means(list(rng.choice(blocks, size=len(blocks), replace=True)))
        for t in targets:
            q, s = excess_at(mm, t, exclude); boots[t][0].append(q); boots[t][1].append(s)
    ci = {t: (tuple(np.percentile(boots[t][0], [2.5, 97.5])), tuple(np.percentile(boots[t][1], [2.5, 97.5])))
          for t in targets} if len(blocks) >= 2 else {}
    return blocks, m, est, ci

def s1_decide(est, ci, phi_max, n_blocks, n_required):
    """S1 hierarchy. Gates: >= n_required complete blocks; finite intervals; quadratic and spline agree."""
    (eq, es), ((lq, hq), (ls, hs)) = est, ci
    oq = classify(eq, lq, hq, SESOI_S1_MV, phi_max); os_ = classify(es, ls, hs, SESOI_S1_MV, phi_max)
    out, why = decide([("complete blocks >= registered N", n_blocks >= n_required),
                       ("finite intervals", all(np.isfinite([lq, hq, ls, hs]))),
                       ("quadratic and spline agree", oq == os_)], oq == "KILL", oq == "PASS")
    return out, why, oq, os_

def s1_analyse(rows, n_required=None, reps=BOOT_REPS, seed=11, keep_flagged=True):
    """rows: (block, ratio, tone, v10_mv[, flag]). Primary = tone ON. Tone OFF is a secondary, descriptive result."""
    res = {}
    for tone in ("on", "off"):
        by = _block_means(rows, tone, keep_flagged)
        blocks, m, est, ci = _bootstrap_excess(by, S1_RATIOS, [1.618], [1.618], reps, seed)
        if not blocks: res[tone] = dict(blocks=0, outcome="INCONCLUSIVE", reason="gate failed: no complete blocks"); continue
        loo = loo_residuals(m); phi_max = max(loo, key=loo.get) == 1.618
        nreq = n_required if n_required is not None else len(blocks)
        out, why, oq, os_ = s1_decide(est[1.618], ci[1.618], phi_max, len(blocks), nreq)
        res[tone] = dict(blocks=len(blocks), excess_quad=est[1.618][0], ci_quad=ci[1.618][0], excess_spline=est[1.618][1],
                         ci_spline=ci[1.618][1], loo=loo, phi_largest_loo=phi_max, outcome_quad=oq, outcome_spline=os_,
                         outcome=out, reason=why)
    res["outcome"] = res["on"]["outcome"]   # S1 verdict = tone-ON verdict
    return res

def s1c_analyse(rows, n_required=None, reps=BOOT_REPS, seed=13, keep_flagged=True):
    """S1c at L0 = 6 cm. Two excesses, each against a background fitted to the 8 settings that are neither target:
       ratio target r = 1.618 (9.71 cm) and absolute target r = 2.1573 (12.94 cm).
       PASS (ratio effect): ratio-target PASS and absolute-target KILL.
       KILL (position effect, not ratio): absolute-target PASS and ratio-target KILL.
       Everything else INCONCLUSIVE. Gates as in S1, applied to both targets."""
    rabs = round(ABS_SPACING_CM / L0_S1C, 4); tg = [1.618, rabs]
    by = _block_means(rows, "on", keep_flagged)
    blocks, m, est, ci = _bootstrap_excess(by, S1C_RATIOS, tg, tg, reps, seed)
    if not blocks: return dict(outcome="INCONCLUSIVE", reason="gate failed: no complete blocks")
    nreq = n_required if n_required is not None else len(blocks)
    o = {}
    for t in tg:
        (eq, es), ((lq, hq), (ls, hs)) = est[t], ci[t]
        o[t] = (classify(eq, lq, hq, SESOI_S1_MV), classify(es, ls, hs, SESOI_S1_MV))
    agree = all(a == b for a, b in o.values())
    out, why = decide([("complete blocks >= registered N", len(blocks) >= nreq), ("quadratic and spline agree", agree)],
                      o[rabs][0] == "PASS" and o[1.618][0] == "KILL", o[1.618][0] == "PASS" and o[rabs][0] == "KILL")
    return dict(blocks=len(blocks), excess_ratio=est[1.618], excess_abs=est[rabs], ci_ratio=ci[1.618], ci_abs=ci[rabs],
                outcome_ratio=o[1.618], outcome_abs=o[rabs], outcome=out, reason=why)

# ------------------------------------------------------------------ S1: deterministic sample size
def s1_power(pilot_rows, P=POWER):
    """Registered algorithm. Inputs: exactly 4 pilot blocks (tone ON runs), never reused.
    1  Background = quadratic fitted to the pilot tone-ON ratio means; noise SD = pooled within-ratio SD across pilot blocks.
    2  For N in 6, 8, ..., 30 (even, so polarity is balanced): simulate `sims` datasets with true excess 7.5 mV
       (1.5 x SESOI) at phi, run the complete S1 rule, record the PASS rate.
    3  N = the smallest N with PASS rate >= 0.80. If none, N = 30 and the achieved power is reported.
    No interim looks; the seed is fixed, so the same pilot data always give the same N."""
    by = _block_means(pilot_rows, "on")
    if len(by) != P["pilot_blocks"]: raise SystemExit(f"power needs exactly {P['pilot_blocks']} pilot blocks, got {len(by)}")
    rs = S1_RATIOS; mean = {r: np.mean([v for b in by for v in by[b][round(r, 4)]]) for r in rs}
    c = np.polyfit(rs, [mean[r] for r in rs], 2)
    sd = float(np.sqrt(np.mean([np.var([np.mean(by[b][round(r, 4)]) for b in by], ddof=1) for r in rs])))
    rng = np.random.default_rng(P["seed"]); table = []
    for n in P["n_grid"]:
        wins = 0
        for _ in range(P["sims"]):
            rows = [(b, r, "on", float(np.polyval(c, r)) + (P["design_effect_mv"] if r == 1.618 else 0) + rng.normal(0, sd))
                    for b in range(n) for r in rs]
            wins += s1_analyse(rows, n_required=n, reps=P["boot_reps"], seed=int(rng.integers(1e9)))["outcome"] == "PASS"
        rate = wins / P["sims"]; se = math.sqrt(rate * (1 - rate) / P["sims"]); table.append((n, rate, se))
        if rate >= P["target"]: return dict(N=n, power=rate, mc_se=se, sd=sd, table=table, capped=False)
    n, rate, se = table[-1]; return dict(N=n, power=rate, mc_se=se, sd=sd, table=table, capped=True)

# ------------------------------------------------------------------ C0: artefact screen
def c0_analyse(rows, reps=BOOT_REPS, seed=3, keep_flagged=True, n_required=C0_BLOCKS):
    """Per block b: D = tone - notone; A_k = artefact_k - notone (k = dummy electrode, lead dress).
    Whole-block bootstrap of all contrasts together, so the shared no-tone baseline and the covariance of D and
    A_k are preserved. D enters the margins as a random quantity, not a fixed number:
      equivalence for artefact k (TOST, alpha 0.05):  95% upper bound of (A_k - 0.25 D) < 0
                                                  and 95% lower bound of (A_k + 0.25 D) > 0
        (impossible when D <= 0, so a small or negative D can never pass);
      artefact kill for k (Bonferroni over 2):        97.5% lower bound of (A_k - 0.50 D) > 0.
    Hierarchy: gate (>= 10 complete blocks) -> KILL (D upper bound < 5 mV, or any artefact kill)
               -> PASS (D lower bound > 0, D >= 5 mV, both artefacts equivalent) -> INCONCLUSIVE."""
    blk = {}
    for row in rows:
        b, run, v = row[:3]; fl = row[3] if len(row) > 3 else 0
        if fl and not keep_flagged: continue
        blk.setdefault(b, {})[run] = v
    B = [b for b in sorted(blk) if all(k in blk[b] for k in ("tone", "notone", "dummy", "lead"))]
    if len(B) < 2: return dict(blocks=len(B), outcome="INCONCLUSIVE", reason="gate failed: complete blocks")
    M = np.array([[blk[b]["tone"] - blk[b]["notone"], blk[b]["dummy"] - blk[b]["notone"], blk[b]["lead"] - blk[b]["notone"]] for b in B])
    def stats(X):
        D, A1, A2 = X.mean(axis=0)
        return np.array([D, A1, A2, A1 - ART_EQUIV * D, A1 + ART_EQUIV * D, A2 - ART_EQUIV * D, A2 + ART_EQUIV * D,
                         A1 - ART_KILL * D, A2 - ART_KILL * D])
    est = stats(M); rng = np.random.default_rng(seed)
    bs = np.array([stats(M[rng.integers(len(B), size=len(B))]) for _ in range(reps)])
    q = lambda j, p: float(np.percentile(bs[:, j], p))
    d, dlo, dhi = est[0], q(0, 2.5), q(0, 97.5)
    eq1 = q(3, 95) < 0 and q(4, 5) > 0; eq2 = q(5, 95) < 0 and q(6, 5) > 0
    ak1 = q(7, 2.5) > 0; ak2 = q(8, 2.5) > 0
    out, why = decide([(f"complete blocks >= {n_required}", len(B) >= n_required)],
                      dhi < SESOI_C0_MV or ak1 or ak2, dlo > 0 and d >= SESOI_C0_MV and eq1 and eq2)
    return dict(blocks=len(B), D=(d, dlo, dhi), dummy=(est[1], q(1, 2.5), q(1, 97.5)), lead=(est[2], q(2, 2.5), q(2, 97.5)),
                equivalent=dict(dummy=eq1, lead=eq2), artefact_kill=dict(dummy=ak1, lead=ak2), outcome=out, reason=why,
                wording="PASS means: a tone effect of at least 5 mV, and each artefact is shown by TOST to be within "
                        "±25% of it. It is an artefact screen for these two artefacts, not proof that no artefact exists.")

# ------------------------------------------------------------------ self-test
def selftest():
    n = 0
    grid = [-10, -1, 0, 0.001, 1, 4.999, 5, 5.001, 10, 100]
    for est in grid:
        for lo in grid:
            for hi in grid:
                if not lo <= est <= hi: continue
                for ep in (True, False):
                    o = classify(est, lo, hi, 5.0, ep); n += 1
                    kill, pas = hi < 5.0, (lo > 0 and est >= 5.0 and ep)
                    assert not (kill and pas)
                    assert o == ("KILL" if kill else "PASS" if pas else "INCONCLUSIVE")
    assert classify(6, 7, 9, 5) == "INCONCLUSIVE" and classify(float("nan"), 0, 1, 5) == "INCONCLUSIVE"
    # every combination of two contrast outcomes, and gate precedence over KILL and PASS
    O = ("PASS", "KILL", "INCONCLUSIVE"); m = 0
    for a in O:
        for b in O:
            c = combine_all([a, b]); m += 1
            assert c == ("KILL" if "KILL" in (a, b) else "PASS" if a == b == "PASS" else "INCONCLUSIVE")
            for g in (True, False):
                out, _ = decide([("g", g)], c == "KILL", c == "PASS")
                assert out == (c if g else "INCONCLUSIVE")
    assert combine_all([]) == "INCONCLUSIVE"
    # schedules are deterministic and balanced
    s = schedule("S1", 6, 42); assert s == schedule("S1", 6, 42) and len(s) == 6 * 18
    assert sum(r["anode"] == "left" for r in s) == sum(r["anode"] == "right" for r in s)
    assert len(schedule("S1c", 2, 1)) == 40 and len(schedule("C0", 10, 1)) == 40
    rng = np.random.default_rng(0)
    def s1rows(eff_on, eff_off, nb=12, sd=2.0):
        return [(b, r, t, 20 + 4 * (r - 1.6) ** 2 + ((eff_on if t == "on" else eff_off) if r == 1.618 else 0) + rng.normal(0, sd), 0)
                for b in range(nb) for r in S1_RATIOS for t in ("on", "off")]
    assert s1_analyse(s1rows(0, 0), reps=500)["outcome"] != "PASS"
    assert s1_analyse(s1rows(12, 0), reps=500)["outcome"] == "PASS"            # tone ON decides
    assert s1_analyse(s1rows(0, 12), reps=500)["outcome"] != "PASS"            # tone OFF alone never passes S1
    assert s1_analyse(s1rows(12, 0, nb=8), n_required=10, reps=300)["outcome"] == "INCONCLUSIVE"   # gate: too few blocks
    flagged = [(b, r, t, v, 1 if b == 0 else 0) for b, r, t, v, _ in s1rows(12, 0)]
    assert s1_analyse(flagged, reps=300, keep_flagged=False)["on"]["blocks"] == 11
    # S1c: ratio effect, position effect, neither
    def s1crows(at_phi, at_abs, nb=12):
        return [(b, r, "on", 20 + 3 * (r - 1.6) + (at_phi if r == 1.618 else 0) + (at_abs if abs(r - 2.1573) < 1e-3 else 0)
                 + rng.normal(0, 1.5)) for b in range(nb) for r in S1C_RATIOS]
    assert s1c_analyse(s1crows(12, 0), reps=500)["outcome"] == "PASS"
    assert s1c_analyse(s1crows(0, 12), reps=500)["outcome"] == "KILL"
    assert s1c_analyse(s1crows(0, 0), reps=500)["outcome"] == "INCONCLUSIVE"
    # C0: clean pass, artefact kill, negative D can never pass, too few blocks
    def c0rows(tone, dummy, lead, nb=10):
        return [(b, run, base + rng.normal(0, 1)) for b in range(nb)
                for run, base in (("notone", 10), ("tone", 10 + tone), ("dummy", 10 + dummy), ("lead", 10 + lead))]
    assert c0_analyse(c0rows(12, 0, 0))["outcome"] == "PASS"
    assert c0_analyse(c0rows(12, 11, 0))["outcome"] == "KILL"
    assert c0_analyse(c0rows(-12, 0, 0))["outcome"] == "KILL"
    assert c0_analyse(c0rows(12, 0, 0, nb=6))["outcome"] == "INCONCLUSIVE"
    print(f"selftest OK: {n} boundary cases, {m} outcome combinations x gate states, schedules, S1 (tone-ON rule, "
          "block gate, flag sensitivity), S1c (ratio / position / neither) and C0 (pass, artefact kill, negative D, gate)")

# ------------------------------------------------------------------ CLI
def read_csv(path):
    with open(path) as f: return list(csv.DictReader(f))

def _fl(r): return int(float(r.get("flag") or 0))

def _print_s1(r, label):
    for tone in ("on", "off"):
        x = r[tone]; tag = "PRIMARY" if tone == "on" else "secondary, descriptive"
        if x.get("blocks", 0) == 0: print(f"  tone {tone}: {x['reason']}"); continue
        print(f"  tone {tone} ({tag}) · {x['blocks']} complete blocks")
        print(f"    quadratic {x['excess_quad']:+.2f} mV  95% CI {x['ci_quad'][0]:+.2f} to {x['ci_quad'][1]:+.2f}  -> {x['outcome_quad']}")
        print(f"    spline    {x['excess_spline']:+.2f} mV  95% CI {x['ci_spline'][0]:+.2f} to {x['ci_spline'][1]:+.2f}  -> {x['outcome_spline']}")
        print(f"    phi has the largest LOO residual: {x['phi_largest_loo']}  ·  outcome {x['outcome']} {x['reason']}")
    print(f"  {label}: {r['outcome']}")

def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "selftest": return selftest()
    if cmd == "schedule":
        test, nb, seed = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]); w = csv.DictWriter(sys.stdout, ["block", "position", "ratio", "tone_or_run", "anode"])
        w.writeheader(); [w.writerow(r) for r in schedule(test if test != "pilot" else "S1", nb, seed)]; return
    nreq = int(sys.argv[3]) if len(sys.argv) > 3 else None
    if cmd in ("s1", "s1c"):
        rows = [(float(r["block"]), float(r["ratio"]), r["tone"], float(r["v10_mv"]) if r["v10_mv"] else float("nan"), _fl(r)) for r in read_csv(sys.argv[2])]
        f = s1_analyse if cmd == "s1" else s1c_analyse
        prim, sens = f(rows, nreq), f(rows, nreq, keep_flagged=False)
        if cmd == "s1":
            print("S1 · primary analysis (flagged runs included)"); _print_s1(prim, "S1 VERDICT")
            print(f"Sensitivity (flagged runs excluded): {sens['outcome']}")
        else:
            print(f"S1c · ratio target {prim.get('outcome_ratio')} · absolute 12.94 cm target {prim.get('outcome_abs')}")
            print(f"  S1c VERDICT: {prim['outcome']} {prim.get('reason', '')}  ·  sensitivity: {sens['outcome']}")
    elif cmd == "c0":
        rows = [(float(r["block"]), r["run"], float(r["v10_mv"]), _fl(r)) for r in read_csv(sys.argv[2])]
        r, sens = c0_analyse(rows), c0_analyse(rows, keep_flagged=False)
        for k in ("D", "dummy", "lead"):
            e, lo, hi = r[k]; print(f"  {k:6s} {e:+.2f} mV  95% CI {lo:+.2f} to {hi:+.2f}")
        print(f"  TOST equivalence (±25% of D): {r['equivalent']}  ·  artefact kill (>50% of D): {r['artefact_kill']}")
        print(f"  C0 VERDICT: {r['outcome']} {r['reason']}  ·  sensitivity (flagged excluded): {sens['outcome']}\n  {r['wording']}")
    elif cmd == "power":
        rows = [(float(r["block"]), float(r["ratio"]), r.get("tone", "on"), float(r["v10_mv"])) for r in read_csv(sys.argv[2])]
        p = s1_power(rows)
        for n, rate, se in p["table"]: print(f"  N={n:2d}  PASS rate {rate:.3f} ± {se:.3f} (MC SE)")
        print(f"pilot noise SD {p['sd']:.2f} mV -> registered N = {p['N']}" + (" (cap reached; achieved power reported)" if p["capped"] else ""))
    else:
        sys.exit(__doc__)

if __name__ == "__main__":
    main()
