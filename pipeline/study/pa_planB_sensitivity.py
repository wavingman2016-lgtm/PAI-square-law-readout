# -*- coding: utf-8 -*-
"""v0.30 round-8 sensitivity: ROI scale, gCNR bin count, bin-edge shift, and an
alternative distribution distance -- all on the ARCHIVED two-dimensional images
already consumed by pa_planB_common_domain_2d.py.

Why this exists (review round 8, items 4 and 5):
  the reviewer asks whether (a) the C-defined 2-D ROI biases the E-vs-M^2
  comparison, and (b) the 65-bin histogram estimator resolves the small paired
  differences (-0.0385 ... -0.0009 gCNR).  The manuscript previously answered
  both with an argument ("harmless because one normalisation / one ROI / one
  binning"); this script replaces that argument with a measurement.

No MATLAB is re-run.  Every number below is a pure post-processing of
results/wire/W*/*_results.mat.

Three knobs, one at a time, everything else held at the Plan B setting:

  ROI   : lesion radius = k x (C FWHM / 2), k in {0.5, 1, 1.5, 2, 3};
          centre stays at the C global peak; background annulus stays [3r, 6r]
          and is clipped by the FOV disc.  k = 1 reproduces Plan B exactly and
          is asserted against planB_common_domain_2d.csv.
  BINS  : gCNR linear bin count in {17, 33, 65, 129, 257}.
  SHIFT : with the bin count fixed at 65, the lower bin edge is displaced by
          frac in {0, 0.25, 0.5, 0.75} of one bin width.
  ALT   : an alternative distribution distance, the sup-norm of the empirical
          CDF difference (Kolmogorov-Smirnov statistic) on 257 bins, reported
          alongside W1 so the sign of d(E - M^2) can be checked for robustness.

Output: results/registry/planB_sensitivity.csv and .log
"""
import glob
import io
import os
import sys

import h5py
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WIRE = os.path.join(ROOT, "results", "wire")
OUT_CSV = os.path.join(ROOT, "results", "registry", "planB_sensitivity.csv")
OUT_LOG = os.path.join(ROOT, "results", "registry", "planB_sensitivity.log")
PLANB_CSV = os.path.join(ROOT, "results", "registry", "planB_common_domain_2d.csv")

W1_BINS = 257


# ---------------------------------------------------------------- estimators
# NOTE ON THE BIN COUNT.  The released estimator (pa_metrics.m:local_gcnr and
# pa_planB_common_domain_2d.py:gcnr) uses `edges = linspace(lo, hi, 65)`, i.e.
# 65 EDGES = 64 BINS.  This script keeps that exact convention so that the
# BINS = 65 / SHIFT = 0 setting reproduces Plan B bit for bit; the manuscript
# wording is corrected to "64 bins (65 edges)" to match.  `bins` below is the
# linspace third argument, i.e. the edge count.
def gcnr(a, b, bins=65, shift=0.0):
    """Linear-histogram overlap, MATLAB histcounts semantics.  `shift` moves the
    lower edge up by `shift` bin widths while keeping the upper edge at `hi`
    (0 <= shift < 1); the same rule is applied to both arms."""
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    lo, hi = min(a.min(), b.min()), max(a.max(), b.max())
    if hi <= lo:
        return 1.0
    w = (hi - lo) / float(bins - 1)
    edges = np.linspace(lo + shift * w, hi, bins)
    pa, _ = np.histogram(a, bins=edges)
    pb, _ = np.histogram(b, bins=edges)
    pa = pa / max(pa.sum(), 1)
    pb = pb / max(pb.sum(), 1)
    return float(1.0 - np.minimum(pa, pb).sum())


def w1(a, b, bins=W1_BINS):
    """First-order Wasserstein distance between two samples: the L1 distance of
    the empirical CDFs.  w1(x, x) = 0, so a SMALLER value means the two
    distributions are CLOSER, i.e. LESS separable."""
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    lo, hi = min(a.min(), b.min()), max(a.max(), b.max())
    if hi <= lo:
        return 0.0
    edges = np.linspace(lo, hi, bins + 1)
    ca = np.cumsum(np.histogram(a, bins=edges)[0]) / max(a.size, 1)
    cb = np.cumsum(np.histogram(b, bins=edges)[0]) / max(b.size, 1)
    return float(np.abs(ca - cb).sum() * (edges[1] - edges[0]))


def ks(a, b, bins=W1_BINS):
    """Kolmogorov-Smirnov statistic = sup |CDF difference| (scale-free)."""
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    lo, hi = min(a.min(), b.min()), max(a.max(), b.max())
    if hi <= lo:
        return 0.0
    edges = np.linspace(lo, hi, bins + 1)
    ca = np.cumsum(np.histogram(a, bins=edges)[0]) / max(a.size, 1)
    cb = np.cumsum(np.histogram(b, bins=edges)[0]) / max(b.size, 1)
    return float(np.abs(ca - cb).max())


# ---------------------------------------------------------------- ROI
def roi_masks(coh, dx, k):
    """Plan B ROI with the lesion radius scaled by k (k=1 reproduces Plan B)."""
    n = coh.shape[0]
    q = (np.arange(n) - n // 2) * dx
    X, Y = np.meshgrid(q, q)
    r = np.hypot(X, Y)
    i, j = np.unravel_index(int(np.argmax(coh)), coh.shape)
    y0, x0 = q[i], q[j]

    def fwhm_of(profile):
        pk = float(profile.max())
        if pk <= 0:
            return float("nan")
        idx = np.flatnonzero(profile >= pk / 2.0)
        if idx.size == 0:
            return float("nan")
        return float(q[idx[-1]] - q[idx[0]])

    fw = [v for v in (fwhm_of(coh[i, :]), fwhm_of(coh[:, j]))
          if np.isfinite(v) and v > 0]
    fwhm = float(np.mean(fw)) if fw else 6.0 * dx
    r_l = float(np.clip(k * fwhm / 2.0, 6.0 * dx, 0.05 * (n * dx)))
    d = np.hypot(X - x0, Y - y0)
    in_mask = d <= r_l
    out_mask = (d >= 3.0 * r_l) & (d <= 6.0 * r_l) & (r <= (n * dx) / 2.0)
    return in_mask, out_mask, r_l


def load(p):
    with h5py.File(p, "r") as f:
        coh = np.array(f["IM/coh"])
        m_img = np.array(f["IM/env"])
        e_ei = np.array(f["IM/sqlaw"])
        e_se = np.array(f["IM/env2"])
        dx = float(np.array(f["cfg/dx"]).item())
    return coh, m_img, e_ei, e_se, dx


def normalise(img, out_mask):
    """Common Plan B convention: divide by the background-ROI median."""
    med = float(np.median(img[out_mask]))
    return img / (med if med > 0 else 1.0)


# ---------------------------------------------------------------- main
def main():
    files = sorted(glob.glob(os.path.join(WIRE, "W*", "*_results.mat")))
    if not files:
        raise SystemExit("no *_results.mat under results/wire")

    planb = {}
    if os.path.exists(PLANB_CSV):
        with io.open(PLANB_CSV, encoding="utf-8") as fh:
            hdr = fh.readline().strip().split(",")
            for line in fh:
                if not line.strip():
                    continue
                r = dict(zip(hdr, line.strip().split(",")))
                planb[r["id"]] = r

    rows = []
    log = []
    log.append("v0.30 第八轮敏感性：ROI 尺度 / gCNR 分箱数 / 分箱起点 / 替代分布距离")
    log.append("载体：results/wire/W*/*_results.mat 的归档二维图（纯后处理，未重跑 MATLAB）")
    log.append("W1 方向约定：w1(x,x)=0 ⇒ W1 越小 = 两分布越接近 = 越不可分。")
    log.append("")

    for p in files:
        wid = os.path.basename(os.path.dirname(p))
        coh, m_img, e_ei, e_se, dx = load(p)
        arms = {"E_EI": e_ei, "M_sq": m_img ** 2}

        # ---- sanity: k=1 must reproduce the archived Plan B row
        in1, out1, r1 = roi_masks(coh, dx, 1.0)
        ref = planb.get(wid)
        chk = ""
        if ref:
            g_ref = float(ref["gCNR_E_EI"])
            g_new = gcnr(e_ei[in1], e_ei[out1])
            chk = "k=1 复现 Plan B: gCNR_E_EI %.4f vs %.4f (diff %.2e)" % (
                g_new, g_ref, abs(g_new - g_ref))
            assert abs(g_new - g_ref) < 5e-4, "%s: %s" % (wid, chk)

        for k in (0.5, 1.0, 1.5, 2.0, 3.0):
            inm, outm, rl = roi_masks(coh, dx, k)
            if inm.sum() < 60 or outm.sum() < 2000:
                log.append("%-10s ROI k=%.1f SKIP (in=%d out=%d)"
                           % (wid, k, inm.sum(), outm.sum()))
                continue
            # gCNR on the archived (already peak-normalised) image, exactly as
            # pa_planB_common_domain_2d.py does; W1/KS are dimensional, so each
            # arm is re-scaled by its own background median (Plan B convention).
            dg = gcnr(e_ei[inm], e_ei[outm]) - gcnr((m_img ** 2)[inm], (m_img ** 2)[outm])
            ne, nm = normalise(e_ei, outm), normalise(m_img ** 2, outm)
            rows.append(dict(id=wid, knob="ROI_k", setting="%.1f" % k,
                             r_lesion_mm="%.4f" % rl,
                             n_in=int(inm.sum()), n_out=int(outm.sum()),
                             d_gCNR="%+.5f" % dg,
                             d_W1="%+.5f" % (w1(ne[inm], ne[outm])
                                             - w1(nm[inm], nm[outm])),
                             d_KS="%+.5f" % (ks(ne[inm], ne[outm])
                                             - ks(nm[inm], nm[outm])),
                             note=chk if k == 1.0 else ""))

        for nb in (33, 65, 129, 257, 513):
            dg = gcnr(e_ei[in1], e_ei[out1], nb) - gcnr((m_img ** 2)[in1], (m_img ** 2)[out1], nb)
            ne, nm = normalise(e_ei, out1), normalise(m_img ** 2, out1)
            rows.append(dict(id=wid, knob="BINS", setting="%d" % nb,
                             r_lesion_mm="%.4f" % r1,
                             n_in=int(in1.sum()), n_out=int(out1.sum()),
                             d_gCNR="%+.5f" % dg,
                             d_W1="%+.5f" % (w1(ne[in1], ne[out1], nb - 1)
                                             - w1(nm[in1], nm[out1], nb - 1)),
                             d_KS="%+.5f" % (ks(ne[in1], ne[out1], nb - 1)
                                             - ks(nm[in1], nm[out1], nb - 1)),
                             note="65 edges = Plan B setting" if nb == 65 else ""))

        for sh in (0.0, 0.25, 0.5, 0.75):
            dg = (gcnr(e_ei[in1], e_ei[out1], 65, sh)
                  - gcnr((m_img ** 2)[in1], (m_img ** 2)[out1], 65, sh))
            ne, nm = normalise(e_ei, out1), normalise(m_img ** 2, out1)
            rows.append(dict(id=wid, knob="SHIFT", setting="%.2f" % sh,
                             r_lesion_mm="%.4f" % r1,
                             n_in=int(in1.sum()), n_out=int(out1.sum()),
                             d_gCNR="%+.5f" % dg,
                             d_W1="%+.5f" % (w1(ne[in1], ne[out1])
                                             - w1(nm[in1], nm[out1])),
                             d_KS="%+.5f" % (ks(ne[in1], ne[out1])
                                             - ks(nm[in1], nm[out1])),
                             note=""))

        log.append("%-10s %s" % (wid, chk))

    # ---- write CSV
    cols = ["id", "knob", "setting", "r_lesion_mm", "n_in", "n_out",
            "d_gCNR", "d_W1", "d_KS", "note"]
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with io.open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(str(r[c]) for c in cols) + "\n")

    # ---- summarise sign stability per knob
    log.append("")
    log.append("=== 符号稳定性（逐 knob；只看 d<0 即 E 落后的数据集数）===")
    for knob in ("ROI_k", "BINS", "SHIFT"):
        for setting in sorted(set(r["setting"] for r in rows
                                  if r["knob"] == knob), key=float):
            sub = [r for r in rows if r["knob"] == knob and r["setting"] == setting]
            gneg = [r["id"] for r in sub if float(r["d_gCNR"]) < 0]
            wneg = [r["id"] for r in sub if float(r["d_W1"]) < 0]
            kneg = [r["id"] for r in sub if float(r["d_KS"]) < 0]
            log.append("  %-7s %-6s n=%d  d_gCNR<0 %d/6  d_W1<0 %d/6  d_KS<0 %d/6"
                       % (knob, setting, len(sub), len(gneg), len(wneg), len(kneg)))
    log.append("")
    log.append("=== 差值范围（逐 knob，全设置合并）===")
    for knob in ("ROI_k", "BINS", "SHIFT"):
        sub = [r for r in rows if r["knob"] == knob]
        for key in ("d_gCNR", "d_W1", "d_KS"):
            v = [float(r[key]) for r in sub]
            log.append("  %-7s %-6s min %+.5f  max %+.5f  (n=%d)"
                       % (knob, key, min(v), max(v), len(v)))

    with io.open(OUT_LOG, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(log) + "\n")
    print("\n".join(log))
    print("\nwrote %s (%d rows)" % (os.path.relpath(OUT_CSV, ROOT), len(rows)))


if __name__ == "__main__":
    sys.exit(main())
