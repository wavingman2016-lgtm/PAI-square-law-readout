# -*- coding: utf-8 -*-
"""
Fig. S4 -- audit of the Plan-B background annulus (review round 8, item 4).

Rows 1-2 : the six in-house datasets, coherent baseline C on a log display,
           with the pre-fixed lesion disk (solid), the background annulus
           (dashed), every local maximum of C above 20% of the peak that lies
           inside the annulus (orange x), and a sector dial just outside the
           outer ring: green = 10-degree sector whose own maximum stays below
           20% of the peak ("clean"), red = contaminated.
Row 3    : the paired difference d_gCNR(E_EI - M^2) of the common-domain
           control under the original annulus and under the de-contaminated
           backgrounds (V1 peak-excluded; V2 clean sectors at 10/20/40%).
           "sat" marks datasets where both arms saturate gCNR at 1.0000
           (paired difference exactly zero, not testable); "NA" marks a
           variant whose background sample fell below the pre-specified
           500-pixel minimum.

Display convention: array row i is drawn at y = q[i] (origin="lower"), which
is the same coordinate convention the ROI code uses, so the overlays coincide
with the image content.

Data: results/wire/<Wn>/*_results.mat (archived 2-D images; pure
      post-processing, no re-run) + results/registry/planB_roi_audit.csv.
Code: pipeline/study/pa_planB_roi_audit.py (ROI/metric code shared with
      pa_planB_common_domain_2d.py).
"""
import csv
import io
import os
import sys

import numpy as np
import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "study"))

from pa_planB_roi_audit import (N_SECTOR, peak_inventory,  # noqa: E402
                                clean_sector_mask, sector_masks, MIN_BG_PX)
from pa_planB_common_domain_2d import make_roi  # noqa: E402

OUT = os.path.join(ROOT, "paper", "figures", "FigS4_roi_audit.png")
AUDIT_CSV = os.path.join(ROOT, "results", "registry", "planB_roi_audit.csv")

plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 7.0

CMAP = matplotlib.colormaps["inferno"]
VLO, VHI = 1e-3, 1.0
NORM = matplotlib.colors.LogNorm(vmin=VLO, vmax=VHI)

DATASETS = [
    ("W1_single", "W1  single wire", "semicircle-128"),
    ("W2_double", "W2  two wires", "semicircle-128"),
    ("W3_cross", "W3  crossed filaments", "semicircle-128"),
    ("W4_depth", "W4  V-shaped filament", "rotational 1440"),
    ("W5_ring", "W5  ring phantom", "rotational 1440"),
    ("W6_rot200", "W6  rotational scan", "rotational 1440"),
]

VARIANTS = [("ring", "ring"), ("V1_peakexcl", "V1"), ("V2_clean10", "c10"),
            ("V2_clean20", "c20"), ("V2_clean40", "c40")]


def load(wid):
    p = os.path.join(ROOT, "results", "wire", wid, wid[:2] + "_results.mat")
    with h5py.File(p, "r") as f:
        coh = np.array(f["IM/coh"])
        dx = float(np.array(f["cfg/dx"]).item())
    return coh, dx


def main():
    audit = {}
    with io.open(AUDIT_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            audit[r["id"]] = r

    fig = plt.figure(figsize=(7.3, 8.4))
    gs = fig.add_gridspec(3, 3, height_ratios=[1.0, 1.0, 0.60],
                          hspace=0.14, wspace=0.08,
                          left=0.045, right=0.925, top=0.955, bottom=0.065)

    for k, (wid, title, geo) in enumerate(DATASETS):
        coh, dx = load(wid)
        n = coh.shape[0]
        q = (np.arange(n) - n // 2) * dx
        in_mask, out_mask, roi = make_roi(coh, dx)
        r_l = roi["r_lesion_mm"]
        peaks = peak_inventory(coh, in_mask, roi, dx)
        ring_peaks = [pk for pk in peaks if pk["zone"] == "ring"]
        rec = audit[wid]

        ax = fig.add_subplot(gs[k // 3, k % 3])
        ext = [q[0] * 1e3, q[-1] * 1e3, q[0] * 1e3, q[-1] * 1e3]
        ax.imshow(np.clip(coh, VLO, VHI), cmap=CMAP, norm=NORM, extent=ext,
                  origin="lower", interpolation="nearest", aspect="equal")
        cx, cy = roi["cx"] * 1e3, roi["cy"] * 1e3
        ax.add_patch(Circle((0, 0), (n * dx / 2) * 1e3, fill=False,
                            edgecolor="0.8", lw=0.6))
        ax.add_patch(Circle((cx, cy), r_l * 1e3, fill=False,
                            edgecolor="white", lw=1.1))
        for rr in (3.0, 6.0):
            ax.add_patch(Circle((cx, cy), rr * r_l * 1e3, fill=False,
                                edgecolor="white", lw=0.8, ls=(0, (4, 3))))
        # sector dial just outside the outer ring (20% rule)
        thr20 = clean_sector_mask(coh, roi, dx, 0.20)
        secs = sector_masks(roi, dx, n)
        r_dial = 6.7 * r_l * 1e3
        for s, sm in enumerate(secs):
            if not sm.any():
                continue
            clean = bool(thr20[s].any())
            a0 = -180.0 + 360.0 * s / N_SECTOR
            ax.add_patch(Wedge((cx, cy), r_dial, a0, a0 + 360.0 / N_SECTOR,
                               width=0.22 * r_l * 1e3,
                               facecolor="#2ca02c" if clean else "#d62728",
                               edgecolor="none", alpha=0.95))
        for pk in ring_peaks[:14]:
            ax.plot(pk["x_mm"], pk["y_mm"], marker="x", color="#ff7f0e",
                    markersize=4.5, markeredgewidth=1.0, linestyle="none")
        ax.set_xlim(cx - 7.4 * r_l * 1e3, cx + 7.4 * r_l * 1e3)
        ax.set_ylim(cy - 7.4 * r_l * 1e3, cy + 7.4 * r_l * 1e3)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title("%s\n%s" % (title, geo), fontsize=7.2, pad=3)
        txt = "ring max %4.1f%% of peak\n%d peaks >20%% in ring" % (
            100.0 * float(rec["ring_max_fracC"]),
            int(rec["n_peaks_above20_in_ring"]))
        ax.text(0.03, 0.03, txt, transform=ax.transAxes, fontsize=6.0,
                color="white", va="bottom", ha="left",
                bbox=dict(facecolor="black", alpha=0.55, pad=1.6, lw=0))

    # ---- row 3: paired difference by background variant
    for k, (wid, title, geo) in enumerate(DATASETS):
        ax = fig.add_subplot(gs[2, k % 3])
        rec = audit[wid]
        vals, labs, cols = [], [], []
        for key, lab in VARIANTS:
            d = rec.get("d_gCNR_%s" % key, "NA")
            nb = int(rec.get("n_bg_%s" % key, 0))
            if d == "NA" or nb < MIN_BG_PX:
                vals.append(np.nan); labs.append(lab + "\nNA"); cols.append("0.8")
            elif abs(float(d)) < 5e-5 and float(rec["gCNR_%s_E_EI" % key]) >= 0.99995:
                vals.append(0.0); labs.append(lab + "\nsat"); cols.append("0.6")
            else:
                vals.append(float(d)); labs.append(lab)
                cols.append("#1f77b4" if float(d) < 0 else "#d62728")
        x = np.arange(len(vals))
        ax.bar(x, vals, color=cols, width=0.62)
        ax.axhline(0, color="black", lw=0.7)
        ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=5.6)
        ax.tick_params(axis="y", labelsize=5.8)
        fin = [v for v in vals if np.isfinite(v)] or [0.0]
        lo, hi = min(fin + [0.0]), max(fin + [0.0])
        pad = max(0.015, 0.28 * (hi - lo))
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_title("$\\Delta$gCNR($E$-$M^2$): %s" % title.split()[0],
                     fontsize=6.8, pad=2)
        if k % 3 == 0:
            ax.set_ylabel("$\\Delta$gCNR", fontsize=6.5)

    cax = fig.add_axes([0.935, 0.36, 0.010, 0.56])
    cb = fig.colorbar(matplotlib.cm.ScalarMappable(norm=NORM, cmap=CMAP),
                      cax=cax)
    cb.set_label("$C$ (normalised, log)", fontsize=6.5)
    cb.ax.tick_params(labelsize=6.0)

    fig.suptitle("Background-annulus audit of the 2-D common-domain control "
                 "(Plan B)", fontsize=8.4, y=0.975)
    fig.savefig(OUT, dpi=300)
    print("written:", OUT)


if __name__ == "__main__":
    main()
