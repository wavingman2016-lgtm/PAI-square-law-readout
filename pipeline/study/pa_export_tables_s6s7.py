#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Export Table S6 (estimator / ROI sensitivity) and Table S7 (background-ring audit)
for the v0.31 manuscript.

Single source of truth:
  results/registry/planB_sensitivity.csv   (v0.30 archive, previously uncited)
  results/registry/planB_roi_audit.csv     (v0.30 archive, previously uncited)

Outputs (readable, for paper/tables/):
  paper/tables/TableS6_estimator_sensitivity.csv
  paper/tables/TableS7_ring_audit.csv

No number is re-keyed by hand: every cell is read from the archive CSVs above.
"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SENS = os.path.join(ROOT, "results", "registry", "planB_sensitivity.csv")
AUDIT = os.path.join(ROOT, "results", "registry", "planB_roi_audit.csv")
OUT = os.path.join(ROOT, "paper", "tables")

DATASETS = ["W1_single", "W2_double", "W3_cross", "W4_depth", "W5_ring", "W6_rot200"]
LABEL = {
    "W1_single": "W1 single wire",
    "W2_double": "W2 two wires",
    "W3_cross": "W3 crossed wires",
    "W4_depth": "W4 two depths",
    "W5_ring": "W5 ring phantom",
    "W6_rot200": "W6 rotational scan",
}


def f(x):
    """format an archived value; keep NA as NA."""
    x = (x or "").strip()
    if x in ("", "NA", "nan"):
        return "NA"
    try:
        v = float(x)
    except ValueError:
        return x
    if v == 0.0:
        return "0.0000"
    return f"{v:+.4f}"


def load(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    sens = load(SENS)
    audit = {r["id"]: r for r in load(AUDIT)}

    # ---------------- Table S6 ----------------
    knobs = [
        ("histogram bin count (edges)", "BINS", ["33", "65", "129", "257", "513"]),
        ("bin-origin shift (bin widths)", "SHIFT", ["0.00", "0.25", "0.50", "0.75"]),
        ("binning-free estimator d_KS", "BINS", ["65"]),
        ("ROI radius multiple", "ROI_k", ["0.5", "1.0", "1.5", "2.0", "3.0"]),
    ]
    idx = {}
    for r in sens:
        idx[(r["knob"], r["setting"], r["id"])] = r

    rows = []
    for name, knob, settings in knobs:
        for s in settings:
            for d in DATASETS:
                r = idx.get((knob, s, d))
                if r is None:
                    continue
                metric = "d_KS" if name.startswith("binning-free") else "d_gCNR"
                note = ""
                if knob == "BINS" and s == "65" and not name.startswith("binning-free"):
                    note = "pre-specified setting (65 edges = 64 bins)"
                if knob == "ROI_k" and s == "1.0":
                    note = "pre-specified radius"
                if knob == "BINS" and s == "65" and name.startswith("binning-free"):
                    note = "binning-free two-sample KS statistic (no histogram)"
                if knob == "ROI_k" and s == "0.5":
                    note = "halved radius: disk begins to contain the lesion shoulder / second wire"
                if knob == "ROI_k" and s == "3.0":
                    note = "tripled radius: W6 leaves saturation"
                rows.append(
                    {
                        "sensitivity knob": name,
                        "setting": s,
                        "dataset": LABEL[d],
                        "d_gCNR(E_EI - M^2)" if metric == "d_gCNR" else "d_KS(E_EI - M^2)": f(r[metric]),
                        "note": note,
                    }
                )

    s6 = os.path.join(OUT, "TableS6_estimator_sensitivity.csv")
    cols = ["sensitivity knob", "setting", "dataset",
            "d_gCNR(E_EI - M^2)", "d_KS(E_EI - M^2)", "note"]
    with open(s6, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            row = {"sensitivity knob": r["sensitivity knob"], "setting": r["setting"],
                   "dataset": r["dataset"], "d_gCNR(E_EI - M^2)": "",
                   "d_KS(E_EI - M^2)": "", "note": r["note"]}
            if "d_gCNR(E_EI - M^2)" in r:
                row["d_gCNR(E_EI - M^2)"] = r["d_gCNR(E_EI - M^2)"]
            if "d_KS(E_EI - M^2)" in r:
                row["d_KS(E_EI - M^2)"] = r["d_KS(E_EI - M^2)"]
            w.writerow(row)

    # ---------------- Table S7 ----------------
    variants = [
        ("pre-registered annulus (3-6 r)", "ring"),
        ("peak exclusion (>20% of C peak)", "V1_peakexcl"),
        ("clean sectors, 10 deg rule", "V2_clean10"),
        ("clean sectors, 20 deg rule", "V2_clean20"),
        ("clean sectors, 40 deg rule", "V2_clean40"),
    ]
    s7 = os.path.join(OUT, "TableS7_ring_audit.csv")
    cols7 = ["dataset", "quantity", "value"]
    with open(s7, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols7)
        w.writeheader()
        for d in DATASETS:
            a = audit[d]
            w.writerow({"dataset": LABEL[d], "quantity": "annulus max / C peak",
                        "value": f"{float(a['ring_max_fracC']):.4f}"})
            w.writerow({"dataset": LABEL[d], "quantity": "annulus p95 / C peak",
                        "value": f"{float(a['ring_p95_fracC']):.4f}"})
            w.writerow({"dataset": LABEL[d], "quantity": "fraction of annulus pixels > 5% of C peak",
                        "value": f"{float(a['ring_frac_gt5pct']):.4f}"})
            w.writerow({"dataset": LABEL[d], "quantity": "discrete peaks > 20% of C peak in annulus",
                        "value": a["n_peaks_above20_in_ring"]})
            w.writerow({"dataset": LABEL[d], "quantity": "strongest annulus peak position (mm)",
                        "value": a["strongest_ring_peak_mm"]})
            w.writerow({"dataset": LABEL[d], "quantity": "background pixels n_bg",
                        "value": a["n_bg_ring"]})
            for name, key in variants:
                dg = a.get("d_gCNR_" + key, "NA")
                nb = a.get("n_bg_" + key, "")
                w.writerow({"dataset": LABEL[d],
                            "quantity": f"d_gCNR(E_EI - M^2), {name}",
                            "value": f(dg)})
                if nb:
                    w.writerow({"dataset": LABEL[d],
                                "quantity": f"n_bg, {name}", "value": nb})

    print("wrote", s6)
    print("wrote", s7)
    print("S6 rows:", len(rows), " S7 rows: 6 datasets x 11 fields")


if __name__ == "__main__":
    main()
