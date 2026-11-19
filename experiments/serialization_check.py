"""Side check for DESIGN.md Decision 2 and Section 5.

Question: can a host send its DDSketch to the coordinator as serialized bytes
(the library's protobuf format) and have the coordinator merge it into a
bin limited sketch?

Run: python3 experiments/serialization_check.py
Needs: numpy, ddsketch, protobuf (tested with ddsketch 3.0.1).
"""

import math

import numpy as np
from ddsketch import LogCollapsingLowestDenseDDSketch
from ddsketch.pb.proto import DDSketchProto

rng = np.random.default_rng(1)
for bins, alpha in [(32, 0.14293), (128, 0.03596), (512, 0.01), (2048, 0.01)]:
    s = LogCollapsingLowestDenseDDSketch(relative_accuracy=alpha, bin_limit=bins)
    for v in rng.lognormal(math.log(20), 1.0, 15000).tolist():
        s.add(v)
    proto = DDSketchProto.to_proto(s)
    data = proto.SerializeToString()
    back = DDSketchProto.from_proto(type(proto).FromString(data))
    a, b = s.get_quantile_value(0.99), back.get_quantile_value(0.99)
    nonzero = sum(1 for c in s._store.bins if c)
    try:
        fresh = LogCollapsingLowestDenseDDSketch(relative_accuracy=alpha, bin_limit=bins)
        fresh.merge(back)
        merge = "ok"
    except Exception as e:  # report, do not hide
        merge = f"failed: {type(e).__name__}: {e}"
    print(f"bins {bins:4d} alpha {alpha:.5f} serialized {len(data):5d} B, "
          f"nonzero bins {nonzero:4d}, store type after decode {type(back._store).__name__}, "
          f"p99 change {abs(b - a) / a:.1e}, merge into bin limited sketch: {merge}")
