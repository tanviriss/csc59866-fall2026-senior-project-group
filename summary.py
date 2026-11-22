"""Summarize random workloads by users within their share (light) vs above it (heavy)."""
import sys; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gpu_sched import *

def split(jobs):
    dem = {}
    for j in jobs: dem[j.user] = dem.get(j.user, 0) + j.gpus * j.run
    tot = sum(dem.values()); n = len(dem)
    return {u: dem[u] / tot <= 1 / n for u in dem}, {u: round(dem[u] / tot, 2) for u in dem}

out = []
for kind in ("burst", "balanced", "heavy"):
    seeds = [None] if kind == "burst" else range(1, 11)
    passes = 0
    out.append(f"\n{kind.upper()}: light users = users whose GPU-hour demand is at most 1/3 of the total")
    for seed in seeds:
        base = burst() if kind == "burst" else random_workload(kind, seed)
        light, share = split(base); row = {}
        for pol in ("fifo", "fair"):
            js = fresh(base); st, ev = simulate(js, pol); r = check_and_report(js, pol, st, ev)
            lw = max((v["max_slow"] for u, v in r["per"].items() if light[u]), default=float('nan'))
            hv = max((v["max_slow"] for u, v in r["per"].items() if not light[u]), default=float('nan'))
            row[pol] = (lw, hv, r["makespan"], r["util"])
        (fl, fh, fm, fu), (sl, sh, sm, su) = row["fifo"], row["fair"]
        cut = 1 - sl / fl; ch = sm / fm - 1; ok = cut >= 0.5 and ch <= 0.10; passes += ok
        out.append(f"  seed {seed}: demand shares {share} | light worst slowdown FIFO {fl:6.2f} -> FAIR {sl:6.2f} "
                   f"({100*cut:+.0f}% cut) | heavy worst slowdown {fh:6.2f} -> {sh:6.2f} | completion {100*ch:+.1f}% | util {100*fu:.1f}% -> {100*su:.1f}% | Q1 {'PASS' if ok else 'fail'}")
    out.append(f"  Q1 passed in {passes} of {len(list(seeds))} runs")
print("\n".join(out)); open(sys.argv[1], "w").write("\n".join(out) + "\n")
