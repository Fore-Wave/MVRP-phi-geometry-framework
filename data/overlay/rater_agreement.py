#!/usr/bin/env python3
"""
Field Desk Overlay · rater agreement · v1.0
Input CSV: item_id, cluster, compiler, rater_a, rater_b   (category labels as text; cluster = guest_id for claims,
           item_id for overlay entries, so entries resample singly)
Statistic: Krippendorff's alpha, NOMINAL distance (categories are not treated as ordered).
Reported separately:  A) rater_a vs rater_b  (does the rubric produce consistent grades?)      -> PRIMARY
                      B) each rater vs compiler (can others reproduce the existing overlay?)      -> secondary
Interval : cluster bootstrap (resample clusters with replacement), 4,000 replicates, 95% percentile.
           Uncertainty target: stability of agreement within THIS fixed collection, not generalisation to new sources.
           Claims cluster by guest (14 clusters, unequal sizes: percentile intervals with few clusters can under-cover,
           so results are reported with that caveat). Entries resample singly, except entries sharing a primary source.
           A replicate with undefined alpha (all items in one category, zero expected disagreement) is dropped and
           counted; if more than 5% of replicates are undefined, the result is INCONCLUSIVE.
Rule (Krippendorff 2004: alpha >= 0.800 reliable, >= 0.667 tentative), applied to the PRIMARY alpha of each
dimension (evidence status for claims; evidence status for entries):
  PASS if point >= 0.800 and lower bound >= 0.667;  KILL if upper bound < 0.667;  else INCONCLUSIVE.
A PASS means raters apply the rubric consistently. It does not mean the grades are true.
Usage: python rater_agreement.py ratings.csv     |     python rater_agreement.py selftest
"""
import csv, sys, random
from collections import Counter

def alpha_nominal(units):
    """units: list of lists of labels (one list per item, >= 2 labels). Krippendorff's alpha, nominal."""
    pairs = Counter(); n_tot = 0
    for labels in units:
        m = len(labels)
        if m < 2: continue
        for i in range(m):
            for j in range(m):
                if i != j: pairs[(labels[i], labels[j])] += 1 / (m - 1)
        n_tot += m
    n_c = Counter()
    for (c, _), v in pairs.items(): n_c[c] += v
    Do = sum(v for (c, k), v in pairs.items() if c != k) / n_tot
    De = sum(n_c[c] * n_c[k] for c in n_c for k in n_c if c != k) / (n_tot * (n_tot - 1))
    return None if De == 0 else 1 - Do / De

def boot(rows, cols, reps=4000, seed=1):
    clusters = {}
    for r in rows: clusters.setdefault(r["cluster"], []).append([r[c] for c in cols])
    keys = list(clusters); rng = random.Random(seed); est = alpha_nominal([u for k in keys for u in clusters[k]])
    raw = [alpha_nominal([u for k in (rng.choice(keys) for _ in keys) for u in clusters[k]]) for _ in range(reps)]
    bs = sorted(a for a in raw if a is not None); undef = (reps - len(bs)) / reps
    if est is None or undef > 0.05: return est, float("nan"), float("nan"), undef
    return est, bs[int(0.025 * len(bs))], bs[int(0.975 * len(bs)) - 1], undef

def decide(est, lo, hi, undef=0.0):
    if est is None or undef > 0.05 or lo != lo: return "INCONCLUSIVE"
    if hi < 0.667: return "KILL"
    if est >= 0.800 and lo >= 0.667: return "PASS"
    return "INCONCLUSIVE"

def selftest():
    cats = ["supported", "partly", "unresolved", "contradicted", "not assessable"]; rng = random.Random(0)
    def make(p_agree):
        rows = []
        for i in range(47):
            truth = rng.choice(cats)
            rr = lambda: truth if rng.random() < p_agree else rng.choice(cats)
            rows.append(dict(item_id=str(i), cluster=str(i % 14), compiler=truth, rater_a=rr(), rater_b=rr()))
        return rows
    assert abs(alpha_nominal([["a", "a"], ["b", "b"], ["a", "b"]]) - alpha_nominal([["a", "a"], ["b", "b"], ["b", "a"]])) < 1e-12
    assert alpha_nominal([["a", "a"], ["b", "b"], ["c", "c"]]) == 1.0
    assert alpha_nominal([["a", "a"], ["a", "a"]]) is None and decide(None, 0, 0) == "INCONCLUSIVE"
    assert decide(*boot(make(0.97), ["rater_a", "rater_b"], reps=1000)) == "PASS"
    assert decide(*boot(make(0.20), ["rater_a", "rater_b"], reps=1000)) == "KILL"
    print("selftest OK: alpha symmetry and perfect agreement; high agreement PASS; chance-level agreement KILL")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    if sys.argv[1] == "selftest": selftest(); sys.exit()
    rows = list(csv.DictReader(open(sys.argv[1])))
    e, lo, hi, u = boot(rows, ["rater_a", "rater_b"])
    print(f"PRIMARY   rater A vs B       alpha {e}  95% CI {lo:.3f} to {hi:.3f}  undefined {u:.1%}  -> {decide(e, lo, hi, u)}")
    for r in ("rater_a", "rater_b"):
        e, lo, hi, u = boot(rows, ["compiler", r])
        print(f"SECONDARY compiler vs {r[-1].upper()}     alpha {e}  95% CI {lo:.3f} to {hi:.3f}  -> {decide(e, lo, hi, u)} (reproduction of existing grades)")
