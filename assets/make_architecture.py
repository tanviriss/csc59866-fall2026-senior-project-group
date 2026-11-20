"""Generates assets/context_view.svg and assets/architecture_view.svg.

Edit the boxes and arrows below, then run:
  python3 assets/make_architecture.py
  rsvg-convert -w 1600 assets/context_view.svg -o assets/context_view.png
  rsvg-convert -w 1800 assets/architecture_view.svg -o assets/architecture_view.png
"""

import os
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "DejaVu Sans, Arial, sans-serif"
BUILD, REUSE, SIM, STATE, ACTOR = "#dbe8f7", "#dcefd9", "#fde3c4", "#eeeeee", "#ffffff"
EDGE = "#333333"


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.parts = w, h, []
        self.parts.append(
            f'<rect x="0" y="0" width="{w}" height="{h}" fill="#ffffff"/>'
            f'<text x="20" y="34" font-size="22" font-weight="bold">{escape(title)}</text>'
        )

    def text(self, x, y, lines, size=14, anchor="middle", weight="normal", color="#111"):
        out = [f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
               f'font-weight="{weight}" fill="{color}">']
        for i, ln in enumerate(lines):
            out.append(f'<tspan x="{x}" dy="{0 if i == 0 else size * 1.25}">{escape(ln)}</tspan>')
        out.append("</text>")
        self.parts.append("".join(out))

    def box(self, x, y, w, h, title, lines, fill, dash=False, size=13):
        d = ' stroke-dasharray="7 4"' if dash else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
                          f'fill="{fill}" stroke="{EDGE}" stroke-width="1.6"{d}/>')
        self.text(x + w / 2, y + 22, [title], size=15, weight="bold")
        self.text(x + w / 2, y + 44, lines, size=size)

    def stack(self, x, y, w, h, title, lines, fill):
        for k in (2, 1):
            self.parts.append(f'<rect x="{x + 8 * k}" y="{y - 8 * k}" width="{w}" height="{h}" '
                              f'rx="8" fill="{fill}" stroke="{EDGE}" stroke-width="1.2"/>')
        self.box(x, y, w, h, title, lines, fill)

    def cylinder(self, x, y, w, h, title, lines, size=13):
        ry = 9
        self.parts.append(
            f'<path d="M{x},{y + ry} a{w / 2},{ry} 0 0,1 {w},0 v{h - 2 * ry} '
            f'a{w / 2},{ry} 0 0,1 {-w},0 z" fill="{STATE}" stroke="{EDGE}" stroke-width="1.6"/>'
            f'<path d="M{x},{y + ry} a{w / 2},{ry} 0 0,0 {w},0" fill="none" stroke="{EDGE}" stroke-width="1.6"/>'
        )
        self.text(x + w / 2, y + 34, [title], size=14, weight="bold")
        self.text(x + w / 2, y + 54, lines, size=size)

    def arrow(self, pts, label=None, lx=None, ly=None, anchor="middle", dash=False, size=12.5):
        d = " ".join(f"{'M' if i == 0 else 'L'}{px},{py}" for i, (px, py) in enumerate(pts))
        da = ' stroke-dasharray="6 4"' if dash else ""
        self.parts.append(f'<path d="{d}" fill="none" stroke="{EDGE}" stroke-width="1.8" '
                          f'marker-end="url(#ah)"{da}/>')
        if label:
            lines = label if isinstance(label, list) else [label]
            self.text(lx, ly, lines, size=size, anchor=anchor, color="#1a1a1a")

    def save(self, name):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" font-family="{FONT}">'
                '<defs><marker id="ah" markerWidth="10" markerHeight="8" refX="9" refY="4" '
                'orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#333"/></marker></defs>')
        with open(os.path.join(HERE, name), "w") as f:
            f.write(head + "".join(self.parts) + "</svg>")


def legend(s, x, y, items=None):
    items = items or [(BUILD, "I build it"), (REUSE, "Reused open source or public data"),
                      (SIM, "Simulated stand in for a real thing"), (STATE, "Saved state on disk")]
    for i, (fill, label) in enumerate(items):
        yy = y + i * 24
        s.parts.append(f'<rect x="{x}" y="{yy}" width="22" height="16" fill="{fill}" stroke="{EDGE}"/>')
        s.text(x + 32, yy + 13, [label], size=13, anchor="start")


def context_view():
    s = Svg(1200, 640, "Figure 3. Context view: who and what the simulator talks to")
    s.box(420, 230, 360, 170, "Fleet p99 simulator",
          ["One Python 3 program on my laptop.", "Splits latencies across simulated hosts,",
           "merges their summaries into a fleet p99,", "and scores it against the exact p99."],
          BUILD)
    s.box(40, 250, 220, 130, "Researcher (me)",
          ["Stands in for the on call", "engineer and the platform", "team from Section 1"], ACTOR)
    s.box(470, 70, 260, 100, "Alibaba 2022 trace",
          ["Public microservices call graph", "data on Alibaba's servers"], REUSE)
    s.box(40, 470, 280, 110, "Open source packages",
          ["ddsketch 3.0.1, numpy 2.5", "installed from PyPI"], REUSE)
    s.box(900, 250, 260, 130, "Git repository",
          ["zihad-patwary branch: code,", "DESIGN.md, results CSV.", "No raw trace data"], ACTOR)
    s.box(880, 470, 280, 110, "Reviewer (Tanvir, professor)",
          ["Reads results and reruns", "the grid from the repository"], ACTOR)
    s.arrow([(260, 300), (420, 300)], "grid settings (grid.json)", 340, 290)
    s.arrow([(420, 345), (260, 345)], ["results CSV, run log,", "figures"], 340, 365)
    s.arrow([(600, 170), (600, 230)], ["one 3 minute CallGraph file,", "downloaded once by hand, kept on local disk"],
            612, 196, anchor="start")
    s.arrow([(260, 470), (470, 400)], "imported at run time", 330, 470, anchor="start")
    s.arrow([(780, 315), (900, 315)], "git push", 840, 305)
    s.arrow([(1030, 470), (1030, 380)], "git pull, rerun", 1042, 430, anchor="start")
    legend(s, 470, 480, [(BUILD, "I build it"), (REUSE, "Reused open source or public data"),
                         (ACTOR, "Person or outside system")])
    s.text(600, 610, ["Nothing runs on a real network. Real hosts and the monitoring pipeline are out of scope (Section 1)."],
           size=13, color="#444")
    s.save("context_view.svg")


def architecture_view():
    s = Svg(1240, 920, "Figure 4. Architecture view: parts, messages and saved state inside one run")
    s.parts.append('<rect x="20" y="150" width="1200" height="560" rx="10" fill="none" '
                   'stroke="#666" stroke-width="1.6" stroke-dasharray="10 6"/>')
    s.text(180, 700, ["Runs in: one Python 3 process on my laptop (run_grid.py). Arrows inside are function calls passing the named record."],
           size=13.5, anchor="start", color="#444")
    s.cylinder(40, 50, 230, 88, "grid.json", ["hosts, budgets, skews, seeds"])
    s.box(40, 200, 230, 130, "1 Run controller",
          ["Reads the grid, loops over", "settings and seeds, plans", "dropped or duplicate reports"], BUILD)
    s.box(40, 400, 230, 150, "2 Data source",
          ["Synthetic generator (numpy)", "or Alibaba loader: keeps", "rt > 0, counts dropped", "rows by reason"], BUILD)
    s.box(340, 400, 205, 150, "3 Partitioner",
          ["Gives every latency one", "host ID by traffic skew", "or by container; counts", "requests per host"], BUILD)
    s.stack(615, 380, 225, 170, "4 Host builder x H",
            ["One per simulated host.", "Sees only its partition.", "Builds one DDSketch", "within its byte budget"], SIM)
    s.parts.append(f'<rect x="652" y="508" width="150" height="26" rx="5" fill="{REUSE}" stroke="{EDGE}"/>')
    s.text(727, 526, ["ddsketch (reused)"], size=12.5)
    s.box(930, 380, 260, 170, "5 Coordinator",
          ["Checks each envelope: host ID", "expected and not repeated,", "same alpha. Merges sketches.",
           "Answers quantile q with", "hosts and requests covered"], BUILD)
    s.box(615, 590, 225, 90, "6 Exact reference",
          ["Pools all latencies, takes", "nearest rank quantile"], BUILD)
    s.box(930, 590, 260, 90, "7 Scorer",
          ["Relative error, 300 ms page flip,", "bound check (C4), result row"], BUILD)
    s.cylinder(40, 745, 230, 92, "CallGraph slice", ["one 3 minute Alibaba file,", "local disk, not committed"])
    s.cylinder(930, 745, 260, 92, "evidence/results.csv", ["one row per setting, method,", "q, seed; plus run_log.txt"])
    s.arrow([(155, 138), (155, 200)], "read once", 165, 174, anchor="start")
    s.arrow([(270, 265), (1060, 265), (1060, 380)],
            "setting: H, budget, alpha, expected host IDs, fault plan (for example drop host 3, send host B twice)",
            660, 255)
    s.arrow([(155, 330), (155, 400)], "load(dataset, seed)", 165, 370, anchor="start")
    s.arrow([(155, 745), (155, 550)], ["read in 1 M", "row chunks"], 165, 722, anchor="start")
    s.arrow([(270, 475), (340, 475)], None)
    s.text(305, 440, ["latencies", "(ms)"], size=12)
    s.arrow([(545, 465), (615, 465)], None)
    s.text(580, 440, ["partition h", "+ count"], size=12)
    s.arrow([(442, 550), (442, 640), (615, 640)], "all latencies", 452, 605, anchor="start")
    s.arrow([(856, 465), (930, 465)], None)
    s.text(893, 425, ["Summary", "Envelope"], size=12, weight="bold")
    s.arrow([(1060, 550), (1060, 590)], "FleetAnswer or error", 1070, 576, anchor="start")
    s.arrow([(840, 635), (930, 635)], None)
    s.text(885, 618, ["exact q"], size=12)
    s.arrow([(1060, 680), (1060, 745)], "one row", 1070, 732, anchor="start")
    legend(s, 330, 748)
    s.text(330, 872, ["Simulated: hosts are objects, not machines, and the network is function calls, so there is no delay or loss",
                      "unless the controller injects it. Reused: ddsketch, numpy, the Alibaba trace. Everything else I build."],
           size=13, anchor="start", color="#333")
    s.save("architecture_view.svg")


if __name__ == "__main__":
    context_view()
    architecture_view()
