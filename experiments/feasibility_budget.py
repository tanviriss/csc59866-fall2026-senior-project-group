"""Feasibility experiment F1 for DESIGN.md Section 9.

Question: at the two smallest per host budgets (512 bytes = 32 bins and
2 KiB = 128 bins, at 16 bytes per bin), which way of fitting DDSketch keeps
the merged fleet p99 closer to the exact value?

  A. collapse lowest bins: alpha = 0.01, bin limit = budget / 16
  B. coarser alpha: alpha chosen so 1 ms to 10 s fits in budget / 16 bins,
     with the same bin limit as a safety cap

Also checks, for option A, whether merging 64 host sketches in different
orders and groupings gives identical bins (requirement C1), and whether the
stored bins stay within the bin limit after merging (requirement F2).

Setting: 64 hosts, traffic skew 1 (host i gets a share proportional to 1/i),
1,000,000 synthetic latencies per run, lognormal and Pareto, seeds 1 to 5.
Exact p99 uses the nearest rank definition from Section 2.

Run: python3 experiments/feasibility_budget.py
Needs: Python 3, numpy, ddsketch (tested with Python 3.12.1 and 3.13, numpy 2.5.5
and 2.5.3, ddsketch 3.0.1; identical results).
Writes: evidence/feasibility_budget.csv and evidence/feasibility_merge_order.csv
"""

import csv
import math
import os
import random
import sys
import time

import numpy as np
import ddsketch
from ddsketch import DDSketch, LogCollapsingLowestDenseDDSketch

N = 1_000_000
HOSTS = 64
SKEW = 1.0
SEEDS = [1, 2, 3, 4, 5]
BUDGETS_BYTES = [512, 2048, 8192, 32768]
BYTES_PER_BIN = 16
Q = 0.99
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evidence")


def coarse_alpha(bins, lo=1.0, hi=10_000.0):
    """Smallest alpha whose log spaced bins cover lo..hi ms in `bins` bins."""
    ratio = math.exp(math.log(hi / lo) / bins)  # gamma = (1 + a) / (1 - a)
    return (ratio - 1) / (ratio + 1)


def latencies(dist, seed):
    rng = np.random.default_rng(seed)
    if dist == "lognormal":
        # median 20 ms, sigma 1.0, so p99 is near 205 ms
        return rng.lognormal(mean=math.log(20.0), sigma=1.0, size=N)
    # Pareto with shape 2.5 and minimum 5 ms, heavier tail
    return (rng.pareto(2.5, size=N) + 1.0) * 5.0


def split(values, seed):
    """Assign each latency to one host with share proportional to 1 / i^SKEW."""
    rng = np.random.default_rng(seed + 1000)
    shares = 1.0 / np.arange(1, HOSTS + 1) ** SKEW
    shares /= shares.sum()
    hosts = rng.choice(HOSTS, size=len(values), p=shares)
    return [values[hosts == h] for h in range(HOSTS)]


def exact_nearest_rank(values, q):
    s = np.sort(values)
    return float(s[math.ceil(q * len(s)) - 1])


def make_sketch(option, bins):
    if option == "A_collapse_lowest":
        return LogCollapsingLowestDenseDDSketch(relative_accuracy=0.01, bin_limit=bins)
    if option == "B_coarse_alpha":
        return LogCollapsingLowestDenseDDSketch(
            relative_accuracy=coarse_alpha(bins), bin_limit=bins
        )
    if option == "unbounded_reference":
        return DDSketch(relative_accuracy=0.01)
    raise ValueError(option)


def build(option, bins, parts):
    sketches = []
    for part in parts:
        s = make_sketch(option, bins)
        for v in part.tolist():
            s.add(v)
        sketches.append(s)
    return sketches


def merge_chain(sketches, order, option, bins):
    m = make_sketch(option, bins)
    for i in order:
        m.merge(sketches[i])
    return m


def merge_tree(sketches, option, bins):
    level = []
    for s in sketches:
        c = make_sketch(option, bins)
        c.merge(s)
        level.append(c)
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            a = level[i]
            if i + 1 < len(level):
                a.merge(level[i + 1])
            nxt.append(a)
        level = nxt
    return level[0]


def bin_snapshot(sk):
    st = sk._store
    return {st.offset + i: c for i, c in enumerate(st.bins) if c}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows, merge_rows = [], []
    print("python", sys.version.split()[0], "numpy", np.__version__,
          "ddsketch", ddsketch.__version__)
    t0 = time.time()
    for dist in ["lognormal", "pareto"]:
        for seed in SEEDS:
            vals = latencies(dist, seed)
            parts = split(vals, seed)
            exact = exact_nearest_rank(vals, Q)
            busiest = max(len(p) for p in parts) / N
            quietest = min(len(p) for p in parts)
            for budget in BUDGETS_BYTES:
                bins = budget // BYTES_PER_BIN
                options = ["A_collapse_lowest"]
                if coarse_alpha(bins) > 0.01:
                    options.append("B_coarse_alpha")
                if budget == BUDGETS_BYTES[0]:
                    options.append("unbounded_reference")
                for opt in options:
                    sks = build(opt, bins, parts)
                    host_bins = max(len(s._store.bins) for s in sks)
                    merged = merge_chain(sks, range(HOSTS), opt, bins)
                    est = merged.get_quantile_value(Q)
                    alpha = merged._mapping.relative_accuracy
                    stored = len(merged._store.bins)
                    lowest_kept = merged._mapping.value(merged._store.min_key)
                    rows.append({
                        "dist": dist, "seed": seed, "budget_bytes": budget,
                        "bin_limit": bins if opt != "unbounded_reference" else "none",
                        "option": opt, "alpha": round(alpha, 5),
                        "exact_p99_ms": round(exact, 4),
                        "estimate_p99_ms": round(est, 4),
                        "rel_error_pct": round(abs(est - exact) / exact * 100, 4),
                        "max_host_bins": host_bins, "merged_bins": stored,
                        "merged_count": int(merged.count),
                        "lowest_uncollapsed_ms": round(lowest_kept, 4),
                        "collapsed": getattr(merged._store, "is_collapsed", False),
                        "busiest_host_share": round(busiest, 4),
                        "quietest_host_requests": quietest,
                    })
                    if opt == "A_collapse_lowest" and seed == 1:
                        ref = bin_snapshot(merged)
                        orders = {"chain_sorted": list(range(HOSTS))}
                        for k in range(3):
                            o = list(range(HOSTS))
                            random.Random(k).shuffle(o)
                            orders[f"chain_shuffle_{k}"] = o
                        results = {n: bin_snapshot(merge_chain(sks, o, opt, bins))
                                   for n, o in orders.items()}
                        results["pairwise_tree"] = bin_snapshot(merge_tree(sks, opt, bins))
                        for name, snap in results.items():
                            merge_rows.append({
                                "dist": dist, "budget_bytes": budget, "merge": name,
                                "identical_to_chain_sorted": snap == ref,
                                "nonzero_bins": len(snap),
                                "total_count": sum(snap.values()),
                            })
                    print(f"{dist:9s} seed {seed} {budget:5d}B {opt:20s} "
                          f"exact {exact:9.3f} est {est:9.3f} "
                          f"err {abs(est-exact)/exact*100:7.3f}%  ({time.time()-t0:5.0f}s)",
                          flush=True)
    with open(os.path.join(OUT_DIR, "feasibility_budget.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(OUT_DIR, "feasibility_merge_order.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(merge_rows[0]))
        w.writeheader()
        w.writerows(merge_rows)
    print(f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
