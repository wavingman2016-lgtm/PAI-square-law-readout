# -*- coding: utf-8 -*-
"""pa_planB_roi_audit.py -- v0.31 round-8: audit of the Plan-B background annulus.

Review round 8, item 4 ("共同域 ROI 偏差风险"): the pre-fixed background annulus
of the Plan-B common-domain control is a geometric ring at 3-6x the lesion
radius.  Nothing in that definition guarantees that the ring contains only
background: on multi-target phantoms it can contain other real targets.  This
script audits what the ring actually contains and re-runs the control on
de-contaminated backgrounds.

What is measured, per in-house dataset (all on the archived 2-D images, pure
post-processing, no MATLAB re-run):
  1. annulus content -- max / median / p95 of the coherent baseline C inside
     the ring, and the fraction of ring pixels above 5/20/50% of the C peak;
  2. a peak inventory -- local maxima of C outside the lesion disk, with their
     distance from the ROI centre and their zone (gap / ring / outside);
  3. two de-contamination variants of the background, both defined on C and
     therefore arm-neutral (they cannot favour E or M^2):
        V1 "peak-excluded"  : ring minus disks of radius r_lesion around every
                              secondary peak above 20% of the C peak;
        V2 "clean sectors"  : ring restricted to 10-degree sectors whose own
                              maximum stays below 20% of the C peak
                              (sensitivity at 10% and 40%);
  4. the Plan-B endpoints (gCNR, 65 bins; W1, 257 bins, each arm normalised by
     its own variant-background median) under the original ring and under V1/V2,
     in particular the paired differences d_gCNR(E_EI - M^2) and d_W1.

Pre-specified before looking at the numbers:
  * secondary-peak level 20% of the C peak -- in the clean single-target
    dataset W1 the ring maximum is 3.5%, so 20% separates "skirt" from
    "another target" by more than a factor of five;
  * minimum background sample 500 pixels, below which a variant is recorded NA
    for that dataset instead of being estimated from too few samples.

Self-checks (assertions on real properties, not smoke tests):
  A. the original-ring gCNR/W1 values reproduce the archived Plan-B table
     (results/registry/planB_common_domain_2d.csv) to < 5e-4 -- a positive
     control that this audit uses exactly the Plan-B ROI and metric code;
  B. W2 is known to contain a second tungsten wire: the inventory must find at
     least one peak >= 50% of the C peak inside the ring;
  C. W1 is the clean control: no ring pixel may exceed 5% of the C peak.

Direction convention (v0.31 correction, review item 1): W1(x,x) = 0, so a
SMALLER W1 means the two distributions are CLOSER, i.e. LESS separable.
d_W1 < 0 therefore reads "E less separable than M^2", never "E more separable".

Input : results/wire/<Wn>/*_results.mat, results/registry/planB_common_domain_2d.csv
Output: results/registry/planB_roi_audit.csv and .log

用法: python pipeline/study/pa_planB_roi_audit.py
版本: v1  2026-10-17
"""
import csv
import glob
import io
import math
import os
import sys

import h5py
import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))

from pa_planB_common_domain_2d import gcnr, w1, make_roi  # noqa: E402

WIRE = os.path.join(ROOT, "results", "wire")
PLANB_CSV = os.path.join(ROOT, "results", "registry", "planB_common_domain_2d.csv")
OUT_CSV = os.path.join(ROOT, "results", "registry", "planB_roi_audit.csv")
OUT_LOG = os.path.join(ROOT, "results", "registry", "planB_roi_audit.log")

PEAK_FRAC = 0.20        # pre-specified secondary-peak level (fraction of C peak)
SECTOR_FRACS = (0.10, 0.20, 0.40)   # sensitivity sweep for the clean-sector rule
N_SECTOR = 36           # 10-degree sectors
MIN_BG_PX = 500         # pre-specified minimum background sample
EXCL_R_FRAC = 1.0       # peak-exclusion disk radius, in units of r_lesion


# ------------------------------------------------------------------ helpers
def zones(d, r_l):
    """Zone label of a distance from the ROI centre."""
    if d <= r_l:
        return "disk"
    if d < 3.0 * r_l:
        return "gap"
    if d <= 6.0 * r_l:
        return "ring"
    return "outside"


def peak_inventory(coh, in_mask, roi, dx, frac=PEAK_FRAC):
    """Local maxima of C outside the lesion disk, strongest first.

    A pixel counts as a peak when it is the maximum of its 3x3 neighbourhood
    and at least `frac` of the global maximum; peaks closer than half the
    lesion radius are merged (kept strongest).
    """
    n = coh.shape[0]
    q = (np.arange(n) - n // 2) * dx
    thr = frac * float(coh.max())
    cand = np.argwhere(coh >= thr)
    raw = []
    for (i, j) in cand:
        i0, i1 = max(i - 1, 0), min(i + 2, n)
        j0, j1 = max(j - 1, 0), min(j + 2, n)
        if coh[i, j] < coh[i0:i1, j0:j1].max():
            continue
        if in_mask[i, j]:
            continue
        raw.append((float(coh[i, j]), int(i), int(j)))
    raw.sort(reverse=True)
    min_sep = max(3.0, 0.5 * roi["r_lesion_mm"] / dx)
    kept = []
    for v, i, j in raw:
        if all((i - i2) ** 2 + (j - j2) ** 2 >= min_sep ** 2 for _, i2, j2 in kept):
            kept.append((v, i, j))
    out = []
    for v, i, j in kept:
        d = math.hypot(q[j] - roi["cx"], q[i] - roi["cy"])
        out.append(dict(val=v, i=i, j=j, x_mm=q[j] * 1e3, y_mm=q[i] * 1e3,
                        dist_mm=d * 1e3, zone=zones(d, roi["r_lesion_mm"])))
    return out


def sector_masks(roi, dx, n, n_sector=N_SECTOR):
    """Angular-sector decomposition of the annulus (list of boolean masks)."""
    q = (np.arange(n) - n // 2) * dx
    X, Y = np.meshgrid(q, q)
    ang = np.arctan2(Y - roi["cy"], X - roi["cx"])          # (-pi, pi]
    d = np.hypot(X - roi["cx"], Y - roi["cy"])
    r_l = roi["r_lesion_mm"]
    ring = (d >= 3.0 * r_l) & (d <= 6.0 * r_l) & (np.hypot(X, Y) <= (n * dx) / 2.0)
    edges = np.linspace(-np.pi, np.pi, n_sector + 1)
    idx = np.clip(np.digitize(ang, edges) - 1, 0, n_sector - 1)
    return [ring & (idx == s) for s in range(n_sector)]


def clean_sector_mask(coh, roi, dx, frac):
    """Annulus restricted to sectors whose own maximum < frac * C peak."""
    n = coh.shape[0]
    thr = frac * float(coh.max())
    m = np.zeros((n, n), dtype=bool)
    for sm in sector_masks(roi, dx, n):
        if sm.any() and coh[sm].max() < thr:
            m |= sm
    return m


def peak_excluded_mask(coh, out_mask, in_mask, roi, dx, peaks):
    """Annulus minus disks of radius r_lesion around every secondary peak."""
    n = coh.shape[0]
    q = (np.arange(n) - n // 2) * dx
    X, Y = np.meshgrid(q, q)
    m = out_mask.copy()
    r_ex = EXCL_R_FRAC * roi["r_lesion_mm"]
    for pk in peaks:
        if pk["zone"] not in ("ring", "gap"):
            continue
        d = np.hypot(X - (pk["x_mm"] * 1e-3), Y - (pk["y_mm"] * 1e-3))
        m &= ~(d <= r_ex)
    return m


def endpoints(img, in_mask, bg_mask):
    """gCNR and W1 (background-median normalised) for one arm / one background."""
    if bg_mask.sum() < MIN_BG_PX or in_mask.sum() < 10:
        return float("nan"), float("nan")
    g = gcnr(img[in_mask], img[bg_mask])
    med = float(np.median(img[bg_mask]))
    img_n = img / (med if med > 0 else 1.0)
    return g, w1(img_n[in_mask], img_n[bg_mask])


# ------------------------------------------------------------------ main
def main():
    matfiles = sorted(glob.glob(os.path.join(WIRE, "W*", "*_results.mat")))
    if not matfiles:
        raise SystemExit("no *_results.mat under results/wire")

    # archived Plan-B values for the positive control (assertion A)
    planb = {}
    with io.open(PLANB_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            planb[r["id"]] = r

    log = []
    log.append("Plan-B background-annulus audit (review round 8, item 4)")
    log.append("all ROI/metric code imported from pa_planB_common_domain_2d.py")
    log.append("pre-specified: secondary-peak level %.0f%% of the C peak; "
               "minimum background sample %d px" % (PEAK_FRAC * 100, MIN_BG_PX))
    log.append("direction convention: W1(x,x)=0 -> smaller W1 = LESS separable; "
               "d_W1<0 means E is closer to its background than M^2")
    log.append("")

    rows = []
    for p in matfiles:
        wid = os.path.basename(os.path.dirname(p))
        with h5py.File(p, "r") as f:
            coh = np.array(f["IM/coh"])
            m_img = np.array(f["IM/env"])
            e_ei = np.array(f["IM/sqlaw"])
            e_se = np.array(f["IM/env2"])
            dx = float(np.array(f["cfg/dx"]).item())
        n = coh.shape[0]

        in_mask, out_mask, roi = make_roi(coh, dx)
        arms = {"E_EI": e_ei, "E_SE": e_se, "M_sq": m_img ** 2, "C_sq": coh ** 2}

        # ---- 1. annulus content
        a = coh[out_mask]
        cmax = float(coh.max())
        content = dict(
            ring_max=float(a.max()), ring_med=float(np.median(a)),
            ring_p95=float(np.percentile(a, 95)),
            frac_gt5=float((a >= 0.05 * cmax).mean()),
            frac_gt20=float((a >= 0.20 * cmax).mean()),
            frac_gt50=float((a >= 0.50 * cmax).mean()))

        # ---- 2. peak inventory
        peaks = peak_inventory(coh, in_mask, roi, dx)
        in_ring = [pk for pk in peaks if pk["zone"] == "ring"]
        in_gap = [pk for pk in peaks if pk["zone"] == "gap"]

        # ---- 3. background variants
        v1 = peak_excluded_mask(coh, out_mask, in_mask, roi, dx, peaks)
        variants = [("ring", out_mask), ("V1_peakexcl", v1)]
        for fr in SECTOR_FRACS:
            variants.append(("V2_clean%.0f" % (fr * 100),
                             clean_sector_mask(coh, roi, dx, fr)))

        rec = {"id": wid, "r_lesion_mm": "%.4f" % (roi["r_lesion_mm"] * 1e3),
               "ring_n_in": int(in_mask.sum()), "ring_n_out": int(out_mask.sum()),
               "ring_max_fracC": "%.4f" % (content["ring_max"] / cmax),
               "ring_med_fracC": "%.5f" % (content["ring_med"] / cmax),
               "ring_p95_fracC": "%.4f" % (content["ring_p95"] / cmax),
               "ring_frac_gt5pct": "%.4f" % content["frac_gt5"],
               "ring_frac_gt20pct": "%.4f" % content["frac_gt20"],
               "ring_frac_gt50pct": "%.4f" % content["frac_gt50"],
               "n_peaks_above20_in_ring": len(in_ring),
               "n_peaks_above20_in_gap": len(in_gap),
               "strongest_ring_peak_fracC":
                   ("%.4f" % (max(pk["val"] for pk in in_ring) / cmax)) if in_ring else "none",
               "strongest_ring_peak_mm":
                   ("%.3f" % max(in_ring, key=lambda pk: pk["val"])["dist_mm"]) if in_ring else "NA"}

        for vname, bg in variants:
            rec["n_bg_%s" % vname] = int(bg.sum())
            vals = {}
            for an, img in arms.items():
                g, w = endpoints(img, in_mask, bg)
                vals[an] = (g, w)
                rec["gCNR_%s_%s" % (vname, an)] = "%.4f" % g
                rec["W1_%s_%s" % (vname, an)] = "%.5f" % w
            ok = all(np.isfinite(v[0]) and np.isfinite(v[1]) for v in vals.values())
            if ok:
                rec["d_gCNR_%s" % vname] = "%+.4f" % (
                    vals["E_EI"][0] - vals["M_sq"][0])
                rec["d_W1_%s" % vname] = "%+.5f" % (
                    vals["E_EI"][1] - vals["M_sq"][1])
            else:
                rec["d_gCNR_%s" % vname] = "NA"
                rec["d_W1_%s" % vname] = "NA"
        rows.append(rec)

        # ---- assertions (run per dataset, before writing anything)
        pb = planb.get(wid)
        if pb is None:
            raise SystemExit("assertion A: %s missing from the Plan-B archive" % wid)
        got = float(rec["gCNR_ring_E_EI"])
        want = float(pb["gCNR_E_EI"])
        assert abs(got - want) < 5e-4, \
            "assertion A failed on %s: ring gCNR %.6f vs archived %.6f" % (wid, got, want)
        gotw = float(rec["W1_ring_E_EI"])
        wantw = float(pb["W1_E_EI"])
        assert abs(gotw - wantw) < 5e-4, \
            "assertion A (W1) failed on %s: %.6f vs %.6f" % (wid, gotw, wantw)
        if wid == "W2_double":
            strong = [pk for pk in in_ring if pk["val"] >= 0.5 * cmax]
            assert strong, "assertion B failed: no >=50% peak inside the W2 ring"
        if wid == "W1_single":
            assert content["ring_max"] < 0.05 * cmax, \
                "assertion C failed: W1 ring max %.4f exceeds 5%% of the peak" % \
                (content["ring_max"] / cmax)

        log.append("=== %s  (r_lesion = %.3f mm, ring = [%.3f, %.3f] mm, "
                   "n_in = %d, n_out = %d)" %
                   (wid, roi["r_lesion_mm"] * 1e3, 3 * roi["r_lesion_mm"] * 1e3,
                    6 * roi["r_lesion_mm"] * 1e3, in_mask.sum(), out_mask.sum()))
        log.append("    ring content: max = %.1f%% of C peak, median = %.2f%%, "
                   "p95 = %.1f%%; pixels above 5/20/50%% of peak: %.1f%% / %.1f%% / %.1f%%"
                   % (100 * content["ring_max"] / cmax, 100 * content["ring_med"] / cmax,
                      100 * content["ring_p95"] / cmax, 100 * content["frac_gt5"],
                      100 * content["frac_gt20"], 100 * content["frac_gt50"]))
        log.append("    peaks above 20%% of peak: %d inside the ring, %d in the gap"
                   % (len(in_ring), len(in_gap)))
        for pk in in_ring[:4]:
            log.append("        ring peak at (%.2f, %.2f) mm, dist %.3f mm, "
                       "level %.1f%% of peak" % (pk["x_mm"], pk["y_mm"], pk["dist_mm"],
                                                 100 * pk["val"] / cmax))
        for vname, bg in variants:
            if bg.sum() < MIN_BG_PX:
                log.append("    %-14s n_bg = %5d  -> NA (below the %d-px minimum)"
                           % (vname, bg.sum(), MIN_BG_PX))
            else:
                log.append("    %-14s n_bg = %5d  d_gCNR(E_EI-M^2) = %s   "
                           "d_W1(E_EI-M^2) = %s"
                           % (vname, bg.sum(), rec["d_gCNR_%s" % vname],
                              rec["d_W1_%s" % vname]))
        log.append("")

    # ---- summary: is the sign of the paired difference stable?
    def signs(key):
        return [r[key] for r in rows if r[key] != "NA"]

    log.append("summary (sign of the paired difference E_EI - M^2, by background variant)")
    for vname, _ in [("ring", None), ("V1_peakexcl", None)] + \
            [("V2_clean%.0f" % (fr * 100), None) for fr in SECTOR_FRACS]:
        sg = signs("d_gCNR_%s" % vname)
        sw = signs("d_W1_%s" % vname)
        if sg:
            log.append("  %-14s d_gCNR: %d/%d negative (range %s .. %s) | "
                       "d_W1: %d/%d negative"
                       % (vname, sum(1 for s in sg if s.startswith("-")), len(sg),
                          min(sg, key=lambda s: float(s)), max(sg, key=lambda s: float(s)),
                          sum(1 for s in sw if s.startswith("-")), len(sw)))
        else:
            log.append("  %-14s d_gCNR: no dataset above the background minimum" % vname)
    log.append("")
    log.append("reading: the ring is NOT empty background in the multi-target "
               "phantoms; the de-contaminated variants test whether the "
               "E-vs-M^2 paired difference is an artefact of that content.")

    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with io.open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    report = "\n".join(log)
    with io.open(OUT_LOG, "w", encoding="utf-8") as fh:
        fh.write(report + "\n")
    print(report)
    print("\n[out] %s\n[out] %s" % (OUT_CSV, OUT_LOG))
    return 0


if __name__ == "__main__":
    sys.exit(main())
