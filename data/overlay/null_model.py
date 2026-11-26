#!/usr/bin/env python3
"""
Field Desk Overlay · thread-network null models · v1.0
Input : guest_thread_matrix.csv (guest_id, status, one 0/1 column per thread)
Sample: interviewed guests only (11). Unit of analysis = guest pair (pairs are NOT independent; only
        whole-network permutation is used for inference, never a per-pair binomial).
Statistics (all fixed before running):
  S1 density      share of guest pairs sharing >= 1 thread
  S2 strong pairs number of guest pairs sharing >= 2 threads
  S3 max degree   largest number of guests any one guest is linked to
Null models:
  N1 uniform         each guest keeps its thread COUNT; threads drawn uniformly without replacement
  N2 exact margins   curveball randomisation of the guest x thread matrix: every guest's thread count
                     AND every thread's guest count are held exactly (Strona et al. 2014)
p-value: (1 + #{null >= observed}) / (1 + n_sims), one-sided (upper tail only). n_sims = 20,000. Seed 20261124.
N2 schedule: chain starts at the observed matrix; 2,000 curveball trades of burn-in; then 20 trades between
retained matrices. Stability check: the whole N2 run is repeated with a second seed (20261125); p-values must agree
within Monte Carlo error.
Usage: python null_model.py guest_thread_matrix.csv
"""
import csv, sys, random, itertools

def load(path):
    rows = [r for r in csv.DictReader(open(path)) if r["status"] == "interviewed"]
    keys = [k for k in rows[0] if k not in ("guest_id", "status")]
    return [r["guest_id"] for r in rows], [{k for k in keys if r[k] == "1"} for r in rows], keys

def stats(sets):
    n = len(sets); pairs = list(itertools.combinations(range(n), 2))
    sh = [len(sets[a] & sets[b]) for a, b in pairs]
    deg = [0] * n
    for (a, b), s in zip(pairs, sh):
        if s: deg[a] += 1; deg[b] += 1
    return sum(1 for s in sh if s) / len(pairs), sum(1 for s in sh if s >= 2), max(deg)

def curveball(sets, rng, rounds=200):
    s = [set(x) for x in sets]
    for _ in range(rounds):
        i, j = rng.sample(range(len(s)), 2)
        common = s[i] & s[j]
        a, b = s[i] - common, s[j] - common
        pool = list(a | b); rng.shuffle(pool)
        s[i] = common | set(pool[:len(a)]); s[j] = common | set(pool[len(a):])
    return s

def main(path, n=20000, seed=20261124):
    names, sets, keys = load(path); rng = random.Random(seed)
    obs = stats(sets); sizes = [len(x) for x in sets]
    nulls = {"N1 uniform": [], "N2 exact margins": []}
    cur = curveball([set(x) for x in sets], rng, rounds=2000)   # burn-in
    for _ in range(n):
        nulls["N1 uniform"].append(stats([set(rng.sample(keys, k)) for k in sizes]))
        cur = curveball(cur, rng, rounds=20)
        nulls["N2 exact margins"].append(stats(cur))
    # margin check for N2
    assert sorted(len(x) for x in cur) == sorted(sizes)
    assert all(sum(k in x for x in cur) == sum(k in x for x in sets) for k in keys)
    print(f"guests {len(names)}, pairs {len(names)*(len(names)-1)//2}, sims {n}")
    labels = ["S1 density", "S2 pairs sharing >=2", "S3 max degree"]
    for i, lab in enumerate(labels):
        print(f"\n{lab}: observed {obs[i]:.3f}" if i == 0 else f"\n{lab}: observed {obs[i]}")
        for name, sims in nulls.items():
            v = sorted(s[i] for s in sims); m = sum(v) / n
            lo, hi = v[int(0.025 * n)], v[int(0.975 * n) - 1]
            p = (1 + sum(1 for x in v if x >= obs[i])) / (1 + n)
            print(f"  {name:17s} mean {m:.3f}  95% range {lo:.3f}-{hi:.3f}  p = {p:.3f}")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "guest_thread_matrix.csv"
    main(path)
    print("\n--- stability check, second seed ---"); main(path, seed=20261125)
