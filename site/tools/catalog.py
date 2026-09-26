#!/usr/bin/env python3
"""Builds V54_UPGRADE_CATALOG.txt from catalog_a.py + catalog_b.py.
Fails unless there are exactly 15 areas of 40 items (600 total)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from catalog_a import AREAS as A
from catalog_b import AREAS as B
AREAS = {**A, **B}
LABEL = {"S57": "SHIPPED V57", "S56": "SHIPPED V56", "S54": "SHIPPED V54", "S53": "SHIPPED V53", "N": "NEXT", "D": "DEFERRED", "R": "REJECTED"}
assert len(AREAS) == 15, len(AREAS)
for k, v in AREAS.items():
    assert len(v) == 40, (k, len(v))
    assert all(s in LABEL for s, _, _ in v), k
out, counts, n = [], {s: 0 for s in LABEL}, 0
out.append("QUADCOM ❖ GENESIS PUBLIC SITE — BUILD 54 UPGRADE CATALOG (UPDATED BUILD 57)\n")
out.append("600 improvements across the public site and the Bitcoin Desk, each with an honest status.")
out.append("SHIPPED = built and verified in that build. NEXT = recommended. DEFERRED = blocked (reason given).")
out.append("REJECTED = conflicts with the site's principles (reason given). Nothing is marked shipped unless it was verified.\n")
body = []
for area, items in AREAS.items():
    letter = area.split(" ")[0]
    body.append(f"\n{area}\n" + "─" * len(area))
    for i, (s, title, note) in enumerate(items, 1):
        n += 1; counts[s] += 1
        body.append(f"[{letter}{i:02d}] {LABEL[s]:<11} {title}" + (f"\n{'':17}{note}" if note else ""))
summary = "SUMMARY  " + " · ".join(f"{LABEL[s]} {c}" for s, c in counts.items()) + f" · TOTAL {n}"
assert n == 600
open(os.path.join(os.path.dirname(__file__), "..", "V54_UPGRADE_CATALOG.txt"), "w").write("\n".join(out) + summary + "\n" + "\n".join(body) + "\n")
print(summary)
