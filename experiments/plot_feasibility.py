"""Draws Figure 5 from evidence/feasibility_budget.csv.

Run: python3 experiments/plot_feasibility.py
Writes: assets/feasibility_f1.png and assets/feasibility_f1.svg
"""

import csv
import os
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
rows = list(csv.DictReader(open(os.path.join(ROOT, "evidence", "feasibility_budget.csv"))))

worst = defaultdict(float)
for r in rows:
    if r["option"] == "unbounded_reference":
        continue
    opt = "B" if r["option"] == "B_coarse_alpha" else "A"
    b = int(r["budget_bytes"])
    if b >= 8192:  # A and B are the same setting at 8 KiB and above
        opt = "AB"
    key = (r["dist"], b, opt)
    worst[key] = max(worst[key], float(r["rel_error_pct"]))

labels = ["512 B", "2 KiB", "8 KiB", "32 KiB"]
budgets = [512, 2048, 8192, 32768]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
for ax, dist, title in zip(axes, ["lognormal", "pareto"], ["Lognormal latencies", "Pareto latencies"]):
    w = 0.38
    for i, b in enumerate(budgets):
        if b >= 8192:
            v = worst[(dist, b, "AB")]
            rects = ax.bar([i], [v], w * 1.4, color="#7f7f9f",
                           label="A = B at 8 KiB and above" if i == 2 else None)
        else:
            ra = ax.bar([i - w / 2], [worst[(dist, b, "A")]], w, color="#c0504d",
                        label="A: keep α = 0.01, collapse lowest bins" if i == 0 else None)
            rb = ax.bar([i + w / 2], [worst[(dist, b, "B")]], w, color="#4a7ebb",
                        label="B: coarser α sized to budget (chosen)" if i == 0 else None)
            rects = list(ra) + list(rb)
        for rect in rects:
            h = rect.get_height()
            txt = f"{h:,.0f}%" if h >= 100 else (f"{h:.1f}%" if h >= 10 else f"{h:.2f}%")
            ax.text(rect.get_x() + rect.get_width() / 2, h * 1.15, txt, ha="center", va="bottom", fontsize=8.5)
    x = range(len(budgets))
    ax.axhline(1.0, color="#333", linestyle="--", linewidth=1, label="Q1 target, 1 percent")
    ax.set_yscale("log")
    ax.set_ylim(0.1, 60000)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_xlabel("Memory budget per host (64 hosts, skew 1)")
    ax.set_title(title)
axes[0].set_ylabel("Worst p99 relative error over 5 seeds (log scale)")
axes[0].legend(loc="upper right", fontsize=8.5, frameon=False)
fig.suptitle("Figure 5. Experiment F1: worst merged p99 error over 5 seeds, by memory budget per host",
             fontsize=10.5)
fig.tight_layout()
for ext in ("png", "svg"):
    fig.savefig(os.path.join(ROOT, "assets", f"feasibility_f1.{ext}"), dpi=160)
print("written")
