#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Nonparametric bootstrap for the fixed-false-alarm detection budget.

Why this exists
---------------
The v0.40 review asked for confidence intervals on a50 and on the threshold
rule.  The per-realisation dark maxima were not archived by the MATLAB run
(only the realised 95th percentile per chain was kept), so no interval can be
placed on the threshold itself without re-running the experiment.  The 20
per-realisation hit/miss outcomes *were* archived under ``C/Pd`` with shape
(rep, arm, amplitude), so a50 can be bootstrapped honestly and without
touching the simulation.

Which amplitudes are archived
-----------------------------
The fifteen-amplitude ladder of the manuscript (0.0002 to 0.40) was run in
three staged passes, each keeping its own ``fivechain_sim.mat``:

  results/fivechain/fivechain_sim.mat          4 amplitudes   0.05  - 0.40
  results/fivechain/_patchC2/fivechain_sim.mat 10 amplitudes  0.0002 - 0.01
  results/fivechain/_patchCE/fivechain_sim.mat 7 amplitudes   0.005 - 0.40

The passes are not independent: at every shared amplitude the five-arm Pd
arrays agree to the bit (checked below), i.e. the later passes extend the
same 20 realisations rather than redrawing them.  Merging is therefore
legitimate and the union is exactly the fifteen amplitudes of the text.
``load()`` asserts the agreement and refuses to merge if it fails.

Rule (identical to ``pa_study_fivechain.m``)
--------------------------------------------
a50 = first amplitude whose mean Pd reaches 0.5, linearly interpolated
between that amplitude and the one below it.  Reproduces the reported
values exactly: C 0.001857, M 0.004545, EH 0.004545, EL 0.004455, SQ 0.003857.

Resampling
----------
Percentile bootstrap, B = 4000, seed fixed.  At each amplitude the 20 trial
indices are resampled with replacement, and the *same* index set is applied to
all five arms, because all five arms see the same synthetic record at a given
amplitude and only their read-out differs.  Replicates in which an arm never
reaches Pd >= 0.5 are censored (a50 = +inf); they are counted and reported
rather than silently dropped.

Outputs
-------
  paper/tables/TS4_detection_bootstrap.csv
  results/study_detection_bootstrap.json
"""
import csv
import io
import json
import os

import h5py
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MATS = [os.path.join(ROOT, "results", "fivechain", name, "fivechain_sim.mat")
        for name in ("", "_patchC2", "_patchCE")]
OUT_CSV = os.path.join(ROOT, "paper", "tables", "TS4_detection_bootstrap.csv")
OUT_JSON = os.path.join(ROOT, "results", "study_detection_bootstrap.json")

ARMS = ["C", "M", "EH", "EL", "SQ"]
B = 4000
SEED = 20261018


def _one(path):
    with h5py.File(path, "r") as f:
        g = f["C"]
        pd = np.asarray(g["Pd"][:], dtype=float)        # (rep, arm, amp)
        amps = np.asarray(g["aList"]).ravel().astype(float)
    return np.transpose(pd, (1, 2, 0)), amps            # (arm, amp, rep)


def load():
    """Merge the three staged archives into the full fifteen-amplitude ladder.

    Overlapping amplitudes must agree exactly, otherwise the passes drew
    different realisations and merging would fabricate a common design.
    """
    merged = {}                                          # round(a, 9) -> (pd_arm_block, a)
    for path in MATS:
        if not os.path.exists(path):
            raise SystemExit("missing archive: %s" % path)
        pd, amps = _one(path)
        tag = os.path.relpath(os.path.dirname(path), ROOT)
        for j, a in enumerate(amps):
            key = round(float(a), 9)
            if key in merged:
                prev = merged[key]
                dmax = float(np.abs(prev - pd[:, j, :]).max())
                if dmax > 1e-12:
                    raise SystemExit(
                        "archives disagree at a=%g (max |dPd| = %.3e): %s is a "
                        "different draw, refusing to merge" % (a, dmax, tag))
            else:
                merged[key] = pd[:, j, :]
    amps = np.array(sorted(merged), dtype=float)
    pd = np.stack([merged[round(float(a), 9)] for a in amps], axis=1)   # (arm, amp, rep)
    return pd, amps


def a50(pd_arm, amps):
    """pd_arm: (amp, rep) -> a50 by the script's rule, or +inf."""
    m = pd_arm.mean(axis=1)
    for i, p in enumerate(m):
        if p >= 0.5:
            if i == 0:
                return float(amps[0])
            a0, p0 = amps[i - 1], m[i - 1]
            a1, p1 = amps[i], m[i]
            return float(a0 + (0.5 - p0) * (a1 - a0) / (p1 - p0 + np.finfo(float).eps))
    return float("inf")


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    pd, amps = load()
    n_rep = pd.shape[2]
    rng = np.random.default_rng(SEED)

    point = [a50(pd[k], amps) for k in range(len(ARMS))]

    boot = np.empty((B, len(ARMS)))
    for b in range(B):
        idx = rng.integers(0, n_rep, size=(len(amps), n_rep))
        for k in range(len(ARMS)):
            res = np.take_along_axis(pd[k], idx, axis=1)   # (amp, rep) resampled
            boot[b, k] = a50(res, amps)

    rows = []
    summary = {"mat": [os.path.relpath(p, ROOT) for p in MATS], "B": B, "seed": SEED,
               "n_rep": int(n_rep), "amplitudes": [float(a) for a in amps],
               "arms": {}}
    for k, arm in enumerate(ARMS):
        col = boot[:, k]
        cens = int(np.isinf(col).sum())
        fin = col[np.isfinite(col)]
        lo, med, hi = np.percentile(fin, [2.5, 50, 97.5]) if fin.size else (np.nan,) * 3
        # Pd and Wilson interval at the two amplitudes that bracket a50
        i_hi = int(np.searchsorted(amps, point[k])) if np.isfinite(point[k]) else None
        bracket = []
        for j in ([i_hi - 1, i_hi] if i_hi else [len(amps) - 1]):
            if j is None or j < 0:
                continue
            k_hits = int(pd[k, j].sum())
            wlo, whi = wilson(k_hits, n_rep)
            bracket.append({"a": float(amps[j]), "hits": k_hits, "n": int(n_rep),
                            "Pd": k_hits / n_rep,
                            "wilson_lo": float(wlo), "wilson_hi": float(whi)})
        summary["arms"][arm] = {"a50": point[k], "a50_boot_lo": float(lo),
                                "a50_boot_med": float(med), "a50_boot_hi": float(hi),
                                "censored": cens, "bracket": bracket,
                                "curve": [float(x) for x in pd[k].mean(axis=1)]}
        rows.append([arm,
                     "%.6f" % point[k],
                     "%.6f" % lo, "%.6f" % hi,
                     "%.4f" % bracket[0]["a"],
                     "%.2f" % bracket[0]["Pd"],
                     "%.4f" % bracket[1]["a"],
                     "%.2f" % bracket[1]["Pd"],
                     "%.3f–%.3f" % (bracket[1]["wilson_lo"], bracket[1]["wilson_hi"])])

    # ratio EL / C, replicate-wise (same resampled trial indices -> paired)
    ic, iel = ARMS.index("C"), ARMS.index("EL")
    ratio = boot[:, iel] / boot[:, ic]
    ratio = ratio[np.isfinite(ratio)]
    r_lo, r_hi = np.percentile(ratio, [2.5, 97.5])
    summary["ratio_EL_over_C"] = {"point": point[iel] / point[ic],
                                  "lo": float(r_lo), "hi": float(r_hi)}

    head = ["arm", "a50", "boot 2.5%", "boot 97.5%",
            "lower $a$", "lower $P_d$", "upper $a$", "upper $P_d$",
            "Wilson 95% at upper $a$"]
    with io.open(OUT_CSV, "w", encoding="utf-8", newline="\n") as fh:
        w = csv.writer(fh)
        w.writerow(head)
        w.writerows(rows)
    with io.open(OUT_JSON, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    print("merged %d amplitudes from %d archives: %s" % (len(amps), len(MATS),
          " ".join("%g" % a for a in amps)))
    print("a50 point :", ["%.6f" % x for x in point])
    for k, arm in enumerate(ARMS):
        s = summary["arms"][arm]
        print("%-3s a50=%.6f  CI [%.6f, %.6f]  censored=%d" %
              (arm, s["a50"], s["a50_boot_lo"], s["a50_boot_hi"], s["censored"]))
    print("EL/C ratio %.3f  CI [%.3f, %.3f]" %
          (summary["ratio_EL_over_C"]["point"],
           summary["ratio_EL_over_C"]["lo"], summary["ratio_EL_over_C"]["hi"]))
    print("wrote", os.path.relpath(OUT_CSV, ROOT))


if __name__ == "__main__":
    main()
