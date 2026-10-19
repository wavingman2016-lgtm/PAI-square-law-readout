#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Distribution-free coverage of an order-statistic interval for the 95th
percentile, for n = 40 draws (v0.47).

The detection threshold is the 95th percentile of 40 noise-only maxima.  For a
continuous i.i.d. sample, [X_(r), X_(s)] covers the population p-quantile with
probability

    sum_{i=r}^{s} C(n,i) p^i (1-p)^(n-i),

with no distributional assumption.  This script evaluates that sum and writes
the tightest interval that reaches 95% coverage, which is the statement quoted
in section 3.5 of the manuscript.

Output: results/study_detection_threshold_ci.json
"""
from math import comb
import io
import json
import os

N = 40
P = 0.95
TARGET = 0.95


def coverage(r, s, n=N, p=P):
    """P(X_(r) <= xi_p <= X_(s)), both bounds inclusive."""
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(r, s + 1))


def main():
    rows = []
    for s in range(N, N - 8, -1):
        for r in range(max(1, s - 8), s + 1):
            c = coverage(r, s)
            if c >= TARGET:
                rows.append({"r": r, "s": s, "coverage": round(c, 4)})
    if not rows:
        raise SystemExit("no interval reaches the target coverage")
    best = min(rows, key=lambda d: (d["s"] - d["r"], -d["coverage"]))
    out = {"n": N, "p": P, "target_coverage": TARGET, "best": best,
           "candidates": sorted(rows, key=lambda d: (d["s"] - d["r"], -d["coverage"]))[:8]}
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dst = os.path.join(root, "results", "study_detection_threshold_ci.json")
    with io.open(dst, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
