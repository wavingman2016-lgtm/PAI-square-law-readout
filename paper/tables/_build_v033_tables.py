#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the v0.33 paper tables from results/fivechain/*.csv.

Single source of truth: results/fivechain/fivechain_data.csv (S1) and
results/fivechain/fivechain_sim.csv (S2).  Every table cell in the manuscript
must be reproducible by re-running this script.

Outputs (paper/tables/):
  TL_literature.csv       Table 1: nearest-neighbour comparison, four binary questions,
                          evidence type and direct-precedent flag
  T1_chains.csv           Table 2: five detection chains, definitions and code mapping
  T2_datasets.csv         Table 3: six in-house acquisitions and their imaging parameters
  T3_sim_summary.csv      Table 4: S2 summary -- amplitude slope, two-point limit, a50, timing
  T4_morphology.csv       Table 5: S1 morphology -- lateral FWHM, PSLR, number of maxima
  T5_detection.csv        Table 6: S1 detection -- gCNR per chain and paired differences
  TC_claim_scope.csv      Table 7: claim-evidence-scope
  TS1_equivalence.csv     S1 detector equivalence EL vs EH (supplementary)
  TS2_sim_detail.csv      S2 detail (supplementary)
"""
import csv
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RES = os.path.join(ROOT, "results", "fivechain")
S1 = os.path.join(RES, "fivechain_data.csv")
S2 = os.path.join(RES, "fivechain_sim.csv")

ARMS = ["C", "M", "EH", "EL", "SQ"]
DS = ["W1", "W2", "W3", "W4", "W5", "W6"]


def read_long(path):
    if not os.path.exists(path):
        return []
    with io.open(path, "r", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def load_s1():
    rows = read_long(S1)
    idx = {}
    for r in rows:
        try:
            v = float(r["value"])
        except (ValueError, KeyError):
            v = float("nan")
        idx[(r["dataset"], r["arm"], r["metric"])] = v
    return idx


def load_s2():
    rows = read_long(S2)
    idx = {}
    for r in rows:
        try:
            v = float(r["value"])
        except (ValueError, KeyError):
            v = float("nan")
        idx[(r["exp"], r["arm"], r["condition"], r["metric"])] = v
    return idx


def write(name, header, rows):
    p = os.path.join(HERE, name)
    with io.open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    print("  wrote %-24s %3d rows" % (name, len(rows)))


def f(v, spec="%.3f"):
    if v != v:  # NaN
        return "NA"
    return spec % v


# ---------------------------------------------------------------- TL (Table 1)
def tl_literature():
    """Nearest-neighbour comparison, one row per method, four binary questions.

    The four question columns are the operational definition of the gap.  Two
    further columns keep the reader from reading an analogue as a precedent:
    ``evidence type`` says at what level the cited record speaks, and
    ``spatial back-projection precedent`` says whether the operation is
    performed on spatial channels inside a reconstruction.  Row L6 answers yes
    to the four questions but is a temporal detection statistic, not a spatial
    reconstruction, so the last column is ``NR`` there and only there.

    Coding rule: a cell is ``yes`` only where the cited record explicitly
    describes the operation, ``NR`` where the record does not explicitly
    report it, and ``n.a.`` where the question does not apply.  ``NR`` is a
    statement about the record, not evidence of absence: no cell asserts a
    confirmed absence.  The search that populated the table is targeted, not
    systematic (section 1.3).

    Cell values are restricted to exactly ``yes``, ``NR`` or ``n.a.``.  No cell
    carries prose: an explanatory gloss inside a coded cell ("no (temporal
    analogue only)") reads as a sixth differently-aligned field once the table
    is rendered, and a reader cannot tell which column the parenthesis belongs
    to.  All qualification lives in the caption.
    """
    header = ["id", "method family", "representative work", "evidence type",
              "squared per channel", "non-linearity per channel",
              "low-passed squared envelope", "incoherent sum of non-negatives",
              "spatial back-projection precedent", "ref."]
    rows = [
        ["L1", "Coherent back-projection (unfiltered DAS; UBP with ramp filter)",
         "Xu & Wang 2005; Kruger et al. 1995", "photoacoustic, direct",
         "NR", "NR", "NR", "NR", "yes", "[3,4]"],
        ["L2", "Back-projection followed by envelope detection (standard display chain)",
         "Gholampour et al. 2025", "photoacoustic, direct",
         "NR", "NR", "NR", "NR", "yes", "[14]"],
        ["L3", "Incoherent compounding of envelope images over apertures or frames",
         "Gholampour et al. 2025; Jespersen et al. 1998", "photoacoustic and ultrasound",
         "NR", "NR", "NR", "yes", "yes", "[14,15]"],
        ["L4", "Delay-multiply-and-sum (DMAS, FDMAS)",
         "Matrone et al. 2015", "ultrasound analogue",
         "NR", "yes", "NR", "NR", "yes", "[16]"],
        ["L5", "p-th-root delay-and-sum (pDAS)",
         "Polichetti et al. 2018", "ultrasound analogue",
         "NR", "yes", "NR", "NR", "yes", "[17]"],
        ["L6", "Square-law detection with non-coherent integration",
         "McDonough & Whalen 1995", "detection theory, temporal",
         "yes", "n.a.", "yes", "yes", "NR", "[13]"],
        ["L7", "Image-domain squaring (display control only)",
         "this work, section 2.3", "this work",
         "NR", "NR", "NR", "NR", "n.a.", "-"],
        ["L8", "Square-and-low-pass (EL, main method)",
         "this work, section 2.1", "this work",
         "yes", "yes", "yes", "yes", "yes", "-"],
        ["L9", "Bare square (SQ, ablation)",
         "this work, section 2.1", "this work",
         "yes", "yes", "NR", "yes", "yes", "-"],
    ]
    write("TL_literature.csv", header, rows)


# ---------------------------------------------------------------- TC (Table 7)
def tc_claim_scope():
    """Claim-evidence-scope table: every headline claim with its support and
    the statement it does not license.  Scope strings must match the wording
    used in sections 4 and 6; they are not free prose."""
    header = ["claim", "evidence", "scope in which it holds", "what is not claimed"]
    rows = [
        ["EL and EH are two realizations of the same narrow-band, band-limited squared-envelope target "
         "under the conditions of section 2.2",
         "section 4.1; Table S5; Fig. 2",
         "six acquisitions; β = 0.80, f_s/f_0 = 8–286; cutoff at band centre; largest pixel difference "
         "1.17% of the EH peak",
         "an exact identity for arbitrary signals, or validity as β approaches 1 or as f_s approaches 2 f_0"],
        ["Retaining the square narrows the apparent profile by 8–63% relative to envelope stacking and "
         "lowers the PSLR in 5/6",
         "section 4.2; Table 5; Fig. 2, Fig. S1",
         "six in-house phantoms, profile through the target centre",
         "a resolution gain, or a narrower response in the imaging sense"],
        ["On the two-point criterion the width ordering does not carry over: at 4:1, M meets the 5% valley "
         "criterion at 1.00 mm and EL and EH at 1.50 mm, although EL and EH have the narrower profile",
         "section 4.3; Table 4; Fig. 3",
         "one simulated geometry, six realisations, separations 0.40–2.00 mm, amplitude ratios 1:1, 2:1 and "
         "4:1 only, dip criteria of 5% and 20%; C met the criterion at the first separation tested, 0.40 mm",
         "a continuous resolution limit, C's limiting separation (not measured), a quantitative resolution "
         "difference between 0.40 and 0.50 mm, or that the reversal persists at ratios between 2:1 and 4:1, "
         "which were not sampled"],
        ["On gCNR, EL exceeds C in 5/6 datasets and shows no resolved separability advantage over M in any "
         "testable dataset",
         "section 4.4; Table 6; Table S2",
         "six in-house bright-target datasets; EL − C positive in 5/6, W5 saturating and disclosed in "
         "section 6; EL − M testable in three datasets and negative in all three, the other three "
         "saturating; the sign of EL − M is unchanged under g_m^2, g_m and no geometric compensation",
         "a general superiority over coherent back-projection, inter-channel phase error as the dominant "
         "cause of the EL − C gap (not measured), or equivalence to M, which would require a pre-specified "
         "margin"],
        ["At the common empirical 5% false-alarm design target C needs 2.4 times less amplitude than any "
         "incoherent chain (ratio interval 1.96 to 3.12)",
         "section 4.4; Fig. 4",
         "one simulated geometry, 128-element semicircle; 40 dark draws for the threshold and 20 detection "
         "trials per amplitude; 5% is a design target, and the ratio interval resamples the detection trials "
         "only",
         "a certified false-alarm rate, an interval that includes threshold-estimation error, or an operating "
         "point transferable to another array, bandwidth or noise model"],
        ["End-to-end cost does not resolve EL from M; the detection stage is 2.25 times cheaper but 1.3% of "
         "the total",
         "section 4.5; Fig. 5b",
         "one machine, ten measured passes after three warm-up passes",
         "a portable benchmark, or a cost ranking between EL and C that is due to squaring"],
        ["The per-channel operator is classical; the contribution is its placement between channel and sum",
         "section 1.3; Table 1; Note S1",
         "a targeted search of Crossref metadata and scholarly web records to 18 October 2026, coded yes "
         "only where the record states the operation",
         "priority, exhaustiveness, or the absence of unpublished and non-indexed precedents"],
    ]
    write("TC_claim_scope.csv", header, rows)


def ts5_weight_sensitivity():
    """Table S2: EL recomputed under three geometric weights.

    Source: results/fivechain/fivechain_weight_sensitivity.csv, produced by
    pipeline/study/pa_study_weight_sensitivity.m.  The g_m^2 arm must reproduce
    the EL values of Table 6; that is asserted here so the sensitivity table
    cannot drift away from the frozen analysis.
    """
    src = os.path.join(ROOT, "results", "fivechain", "fivechain_weight_sensitivity.csv")
    if not os.path.exists(src):
        print("  [skip] %s not found -- Table S2 not built" % src)
        return
    val = {}
    with io.open(src, "r", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            val[(r["dataset"], r["arm"], r["metric"])] = float(r["value"])

    # The g_m^2 arm must reproduce the frozen EL analysis, otherwise the
    # sensitivity table would be describing a different reconstruction.
    s1 = load_s1()
    for ds in ["W1", "W2", "W3", "W4", "W5", "W6"]:
        a = val[(ds, "EL2", "gcnr2d")]
        b = s1[(ds, "EL", "gcnr2d")]
        if abs(a - b) > 5e-5:
            raise SystemExit("Table S2: g_m^2 arm does not reproduce Table 6 (%s: %.6f vs %.6f)"
                             % (ds, a, b))

    header = ["dataset", "arm", "geometric weight", "gCNR", "FWHM lat (mm)",
              "FWHM axi (mm)", "PSLR lat (dB)", "EL-to-M width ratio"]
    rows = []
    label = {"C": "g = d/R", "M": "g = d/R", "EL2": "g^2 (main)", "EL1": "g", "EL0": "none"}
    for ds in ["W1", "W2", "W3", "W4", "W5", "W6"]:
        wm = val[(ds, "M", "fwhm_lat")]
        for a in ["C", "M", "EL2", "EL1", "EL0"]:
            ratio = val[(ds, a, "fwhm_lat")] / wm if a.startswith("EL") else None
            rows.append([ds, a, label[a],
                         "%.4f" % val[(ds, a, "gcnr2d")],
                         "%.3f" % val[(ds, a, "fwhm_lat")],
                         "%.3f" % val[(ds, a, "fwhm_axi")],
                         "%.1f" % val[(ds, a, "pslr_lat")],
                         "%.3f" % ratio if ratio is not None else "-"])
    write("TS5_weight_sensitivity.csv", header, rows)


def ts6_contrast_isolation():
    """Table S1: what each pairwise contrast varies and what it can attribute.

    Static: it is a statement about the design, not a measurement.
    """
    header = ["contrast", "what changes", "what is held fixed",
              "what the contrast can attribute", "what it cannot attribute"]
    rows = [
        ["EH vs EL",
         "the realization of one definition: Hilbert modulus, or square followed by the low-pass",
         "records, band-pass, weight g^2, grid, kernel, incoherent summing rule",
         "whether omitting the Hilbert transform changes the image beyond the filter residual",
         "anything about squaring, which both chains perform"],
        ["EL vs SQ",
         "the low-pass after squaring",
         "records, band-pass, weight g^2, grid, kernel, incoherent summing rule",
         "the role of the filter, including the doubled-carrier texture it removes",
         "a property of squaring alone, since both chains square"],
        ["M vs EL",
         "the per-channel functional (envelope or its square), the weight (g or g^2), and hence the distribution and the dynamic range",
         "records, band-pass, grid, kernel, real-valued back-projection, incoherent summing rule",
         "whether the squared-amplitude read-out as implemented differs on an endpoint",
         "a decomposition between the functional and the weight; Table S2 bounds that decomposition"],
        ["C vs M",
         "coherence of the sum (complex field against non-negative magnitudes) and the output data type; the weight is g in both",
         "records, band-pass, grid, kernel",
         "the effect of coherent against incoherent aggregation",
         "any effect of the per-channel functional, which is the same modulus"],
        ["C vs EL",
         "the whole read-out family: analytic signal and complex summation against squared, low-passed, non-negative summation with g^2",
         "records, band-pass, grid, kernel",
         "how two complete read-out families rank on an endpoint",
         "attribution to any single factor: phase, functional, weight or data type"],
    ]
    write("TS6_contrast_isolation.csv", header, rows)


# ---------------------------------------------------------------- T1
def t1_chains():
    header = ["chain", "definition", "per-channel quantity", "geometric weight",
              "read-out domain", "code path"]
    rows = [
        ["C", "coherent back-projection", "|sum g z|, z = analytic signal",
         "g = d/R", "amplitude", "hilbert then pa_backproject_coherent (Comp=r)"],
        ["M", "envelope stacking", "sum g A, A = |z|",
         "g = d/R", "amplitude", "D.env then pa_backproject (Comp=r)"],
        ["EH", "Hilbert squared envelope", "sum g^2 A^2",
         "g^2", "power", "D.env2 then pa_backproject (Comp=r2)"],
        ["EL", "square and low-pass (main)", "sum g^2 q, q = 2 LPF{x^2}",
         "g^2", "power", "D.sqlaw then pa_backproject (Comp=r2)"],
        ["SQ", "bare square (ablation)", "sum g^2 x^2",
         "g^2", "power", "D.sq then pa_backproject (Comp=r2)"],
    ]
    write("T1_chains.csv", header, rows)


# ---------------------------------------------------------------- T2
def t2_datasets():
    header = ["id", "object", "array / scan", "R (mm)", "Nx", "FOV (mm)",
              "$f_s$ (MHz)", "$f_0$ (MHz)", "band (MHz)", "LPF (MHz)"]
    spec = {
        "W1": ("single wire, cross-section", "semicircle 128", "55.0", "601", "40", "40", "5.00", "3.00-7.00", "5.00"),
        "W2": ("two parallel wires", "semicircle 128", "55.0", "601", "40", "40", "5.00", "3.00-7.00", "5.00"),
        "W3": ("two crossing wires", "semicircle 128", "55.0", "1501", "60", "40", "5.00", "3.00-7.00", "5.00"),
        "W4": ("two wires at different depths", "rotational 1440 x 32", "54.28", "601", "18", "100", "1.16", "0.70-1.62", "1.16"),
        "W5": ("ring / tubular phantom", "static 1440 x 32", "17.49", "601", "18", "100", "0.35", "0.21-0.49", "0.35"),
        "W6": ("rotational scan, 200 steps", "rotational 200", "16.02", "601", "18", "100", "2.00", "1.20-2.80", "2.00"),
    }
    rows = [[k] + list(spec[k]) for k in DS]
    write("T2_datasets.csv", header, rows)


# ---------------------------------------------------------------- T3
def t3_morphology(s1):
    header = ["dataset", "metric"] + ARMS + ["EL/M"]
    rows = []
    for m, lab, sp in [("fwhm_lat", "lateral FWHM (mm)", "%.3f"),
                       ("fwhm_axi", "axial FWHM (mm)", "%.3f"),
                       ("pslr_lat", "lateral PSLR (dB)", "%.1f"),
                       ("n_peaks", "lateral maxima (count)", "%.0f")]:
        for d in DS:
            vals = [s1.get((d, a, m), float("nan")) for a in ARMS]
            ratio = "NA"
            if vals[3] == vals[3] and vals[1] == vals[1] and vals[1] > 0:
                ratio = "%.2f" % (vals[3] / vals[1])
            rows.append([d, lab] + [f(v, sp) for v in vals] + [ratio])
    write("T4_morphology.csv", header, rows)


# ---------------------------------------------------------------- T4
def t4_detection(s1):
    header = ["dataset"] + ["gCNR " + a for a in ARMS] + [
        "EL-C", "EL-M", "EL-SQ", "testable"]
    rows = []

    def pair(diff, va, vb):
        # 两端都饱和到 1.0000 时，差值没有可分辨含义：记 NA，不写 +0.0000。
        # 单元格内带上 (sat.)，因为只有表注解释时读者仍会把 NA 读成 "未测" 或 "0"。
        if abs(va - 1.0) < 1e-6 and abs(vb - 1.0) < 1e-6:
            return "NA (sat.)"
        return "%+.4f" % diff

    for d in DS:
        vals = [s1.get((d, a, "gcnr2d"), float("nan")) for a in ARMS]
        d_c = vals[3] - vals[0]
        d_m = vals[3] - vals[1]
        d_s = vals[3] - vals[4]
        testable = "yes"
        if abs(vals[1] - 1.0) < 1e-6 and abs(vals[3] - 1.0) < 1e-6:
            testable = "NA (both saturate)"
        rows.append([d] + [f(v, "%.4f") for v in vals] + [
            pair(d_c, vals[3], vals[0]),
            pair(d_m, vals[3], vals[1]),
            pair(d_s, vals[3], vals[4]),
            testable])
    write("T5_detection.csv", header, rows)


# ---------------------------------------------------------------- TS1
def ts1_equivalence(s1):
    header = ["dataset", "Pearson", "max |EL-EH| / max EH", "RMS |EL-EH| / RMS EH"]
    rows = []
    for d in DS:
        rows.append([d,
                     f(s1.get((d, "EL_vs_EH", "pearson"), float("nan")), "%.6f"),
                     f(s1.get((d, "EL_vs_EH", "relmax"), float("nan")), "%.4f"),
                     f(s1.get((d, "EL_vs_EH", "relrms"), float("nan")), "%.4f")])
    write("TS1_equivalence.csv", header, rows)


# ---------------------------------------------------------------- T5
def t5_sim_summary(s2):
    header = ["quantity", "C", "M", "EH", "EL", "SQ", "unit"]
    rows = []

    def row(label, metric, cond="amp_ladder", unit="", sp="%.3f"):
        vals = [s2.get(("A", a, cond, metric), float("nan")) for a in ARMS]
        if all(v != v for v in vals):
            return
        rows.append([label] + [f(v, sp) for v in vals] + [unit])

    row("amplitude-law slope (A)", "slope", "amp_ladder", "1", "%.3f")
    row("slope SD (A)", "slope_sd", "amp_ladder", "1", "%.3f")

    # 峰值/背景比：A 段现在按幅度逐行写（v0.33 修过"传向量导致格式串错位"的 bug）。
    # 取参考幅度 a=1.00，并断言它在各幅度之间的极差 < 0.5 dB —— 线性链的这个比值
    # 不应随目标幅度变。断言一旦失败说明 A 段又坏了，绝不能让一个"平均过的数"悄悄进表。
    amps = sorted({k[2] for k in s2 if k[0] == "A" and k[3] == "dr_dB"},
                  key=lambda s: float(s.split("=")[1]))
    if amps:
        vals, spreads = [], []
        for arm in ARMS:
            vv = [s2.get(("A", arm, c, "dr_dB"), float("nan")) for c in amps]
            vv = [v for v in vv if v == v]
            if not vv:
                vals.append(float("nan"))
                spreads.append(float("nan"))
                continue
            vals.append(s2.get(("A", arm, "a=1.00", "dr_dB"), vv[len(vv) // 2]))
            spreads.append(max(vv) - min(vv))
        ss = [x for x in spreads if x == x]
        assert not ss or max(ss) < 0.5, \
            "A 段 dr_dB 随幅度变化 %.2f dB，与线性链预期不符" % max(ss)
        rows.append(["peak-to-background at a=1.00 (A)"]
                    + [f(v, "%.1f") for v in vals] + ["dB"])

    # two-point limits
    for r in ("1:1", "2:1", "4:1"):
        vals5 = [s2.get(("B", a, "r=%s" % r, "d_min_mm_dip5"), float("nan")) for a in ARMS]
        vals20 = [s2.get(("B", a, "r=%s" % r, "d_min_mm_dip20"), float("nan")) for a in ARMS]
        if all(v != v for v in vals5):
            continue
        # 行标签用 "criterion crossing" 而非 "limit"：值是首个满足判据的采样间隔，
        # 且 0.40 mm 是扫描下界，叫 limit 会让读者把它当成拟合出的极限。
        rows.append(["criterion crossing, 5%% dip, %s" % r] + [f(v, "%.2f") for v in vals5] + ["mm"])
        rows.append(["criterion crossing, 20%% dip, %s" % r] + [f(v, "%.2f") for v in vals20] + ["mm"])

    # a50 from C。若某链的 a50 卡在最弱档（搜索下界），该值不含信息量，必须标出来：
    # 首跑五链 a50 全等于 0.05（地板效应）而表里看不出来，正是要避免的情形。
    vals = [s2.get(("C", arm, "all", "a50"), float("nan")) for arm in ARMS]
    if not all(v != v for v in vals):
        labels = []
        for arm, v in zip(ARMS, vals):
            atfloor = s2.get(("C", arm, "all", "a50_at_floor"), 0.0)
            # 以 1e-3 为单位、两位小数：EL 0.004455 与 M/EH 0.004545 在任何 4 位
            # 小数的写法下都会并成同一个数，而这正是要分辨的差别；换成 4.45 对 4.55
            # 就分开了，且不再显得过度精确。
            labels.append(f(v * 1e3, "%.2f") + ("*" if atfloor == 1 else ""))
        rows.append(["a50 at 5% false-alarm design target (C), x1e-3"] + labels + ["rel."])

    # end-to-end timing (SQ is not timed: it is an ablation, not a candidate chain)
    vals = [s2.get(("E", arm, "timing", "e2e_mean"), float("nan"))
            for arm in ["C", "M", "EH", "EL"]]
    if not all(v != v for v in vals):
        rows.append(["end-to-end time (E)"] + [f(v, "%.3f") for v in vals]
                    + ["not timed", "s"])

    # 算力账必须分两层写：端到端比值被反投影主导（实值 BP 占 e2e 的 96%），
    # 真正可归因到检波步骤的是 env-stage 比值。只报端到端会得出"五链同价"的错觉，
    # 只报检波级又会夸大收益，两行都进表。
    # 这些是标量比值，不是逐链数值：放在 EL 列（它们都以 EL 为分子），其余列留空，
    # 免得读者把 0.984 当成"C 的端到端时间"。
    def scalar(label, v, sp="%.3f"):
        if v != v:
            return
        cells = ["", "", "", f(v, sp), ""]
        rows.append([label] + cells + ["1"])

    scalar("  EL/M, end-to-end (E)", s2.get(("E", "EL", "timing", "ratio_EL_over_M"), float("nan")))
    scalar("  EL/M, detection stage only (E)",
           s2.get(("E", "EL", "timing", "env_stage_ratio_EL_over_M"), float("nan")))
    scalar("  back-projection share of EL total (E)",
           s2.get(("E", "EL", "timing", "bp_share_of_e2e"), float("nan")))
    r = s2.get(("E", "EL", "timing", "bp_ratio_EL_over_C"), float("nan"))
    if r == r and r > 0:
        # 报"复值/实值"而不是"实值/复值"：读者关心的是复值反投影贵多少倍。
        scalar("  complex / real back-projection cost (E)", 1.0 / r, "%.2f")

    write("T3_sim_summary.csv", header, rows)


# ---------------------------------------------------------------- TS2
def t5b_sim_detail(s2):
    header = ["experiment", "condition", "quantity", "value", "unit"]
    rows = []

    def add(exp, cond, qty, val, unit=""):
        rows.append([exp, cond, qty, val, unit])

    # B: dip curves。间距网格同样从数据枚举（只抽 1:1 与 4:1 两个代表比值，这是版面取舍）。
    ddB = sorted({k[2].split(",d=")[1].replace("mm", "") for k in s2
                  if k[0] == "B" and k[3] == "dip" and k[2].startswith("r=1:1,d=")},
                 key=float)
    for ratio in ("1:1", "4:1"):
        for dd in ddB:
            cond = "r=%s,d=%smm" % (ratio, dd)
            for a in ARMS:
                v = s2.get(("B", a, cond, "dip"), float("nan"))
                sd = s2.get(("B", a, cond, "dip_sd"), float("nan"))
                if v != v:
                    continue
                add("B", cond, "dip depth, %s" % a, f(v, "%.3f"), "1")
                if sd == sd:
                    add("B", cond, "dip SD, %s" % a, f(sd, "%.3f"), "1")
    # B: two-point limits
    for ratio in ("1:1", "2:1", "4:1"):
        for a in ARMS:
            for m, lab in (("d_min_mm_dip5", "d_min, 5% dip"),
                           ("d_min_mm_dip20", "d_min, 20% dip")):
                v = s2.get(("B", a, "r=%s" % ratio, m), float("nan"))
                if v != v:
                    continue
                add("B", "r=%s" % ratio, "%s, %s" % (lab, a), f(v, "%.2f"), "mm")
    # C: detection curve。幅度档位从数据里枚举，不写死列表——首跑写死 4 档，
    # 后来向下补了 3 档，写死的列表会把新增档位静默漏掉。
    ampC = sorted({k[2] for k in s2 if k[0] == "C" and k[3] == "Pd_fpr5"},
                  key=lambda s: float(s.split("=")[1]))
    # 只保留有信息量的低幅度档：a >= 0.02 时五链一律 Pd=1.00（已核），
    # 把它们逐行印出来只是把表拖长，不增加信息。集中成一行说明。
    ampKeep = [c for c in ampC if float(c.split("=")[1]) <= 0.0101]
    for cond in ampKeep:
        for a in ARMS:
            v = s2.get(("C", a, cond, "Pd_fpr5"), float("nan"))
            sd = s2.get(("C", a, cond, "Pd_sd"), float("nan"))
            if v != v:
                continue
            add("C", cond, "Pd at 5%% false-alarm design target, %s" % a, f(v, "%.2f"), "1")
            if sd == sd:
                add("C", cond, "Pd SD, %s" % a, f(sd, "%.3f"), "1")
    for a in ARMS:
        v = s2.get(("C", a, "all", "a50"), float("nan"))
        if v == v:
            # 与 T3 同一口径（x1e-3、两位小数）：4 位小数会把 EL 0.004455 与
            # M/EH 0.004545 并成同一个数。
            add("C", "all", "a50 x1e-3, %s" % a, f(v * 1e3, "%.2f"), "1")
    # 对未逐行印出的高幅度档给出显式说明，免得读者以为漏了数据。
    hi = [c for c in ampC if float(c.split("=")[1]) > 0.0101]
    if hi:
        add("C", ">= " + hi[0].split("=")[1],
            "Pd at 5%% false-alarm design target, all five chains at every amplitude a = %s to %s"
            % (hi[0].split("=")[1], hi[-1].split("=")[1]), "1.00", "1")
    # D: window rules (simulated)
    for rule in ["fixed", "percentile", "dual"]:
        for arm in ["M", "EH", "EL"]:
            cond = "r=4:1,d=1.0mm,%s" % rule
            for m, lab in (("weak_display_contrast", "weak display contrast"),
                           ("saturated_frac", "saturated fraction"),
                           ("black_frac", "black-clipped fraction")):
                v = s2.get(("D", arm, cond, m), float("nan"))
                if v != v:
                    continue
                # 显示对比度给 4 位小数：正文引用了 0.3697 与 0.2566，
                # 3 位会写成都 0.370/0.257，读者无法把正文数字对回表。
                sp = "%.4f" if m == "weak_display_contrast" else "%.3f"
                add("D", "%s,%s" % (arm, rule), lab, f(v, sp), "1")
                if m == "weak_display_contrast":
                    sd = s2.get(("D", arm, cond, "weak_display_contrast_sd"), float("nan"))
                    if sd == sd:
                        add("D", "%s,%s" % (arm, rule), lab + " SD", f(sd, "%.4f"), "1")
    # D2: real images
    conds = ["W2,fixed", "W2,percentile", "W2,dual",
             "W4,fixed", "W4,percentile", "W4,dual"]
    for arm in ["M", "EH", "EL"]:
        for c in conds:
            for m, lab in (("saturated_frac", "saturated fraction"),
                           ("black_frac", "black-clipped fraction")):
                v = s2.get(("D2", arm, c, m), float("nan"))
                if v != v:
                    continue
                add("D2", "%s,%s" % (arm, c), lab, f(v, "%.3f"), "1")
    # E: timing
    for m, lab in [("tPre", "pre-processing"), ("tHilbert", "Hilbert transform"),
                   ("tEnv", "envelope"), ("tEnv2", "squaring of envelope"),
                   ("tSquare", "square"), ("tLPF", "low-pass"),
                   ("tBP_real", "back-projection, real"),
                   ("tBP_complex", "back-projection, complex")]:
        v = s2.get(("E", "all", "timing", m), float("nan"))
        sd = s2.get(("E", "all", "timing", m + "_sd"), float("nan"))
        if v != v:
            continue
        add("E", "stage", "%s, mean" % lab, f(v, "%.4f"), "s")
        if sd == sd:
            add("E", "stage", "%s, SD" % lab, f(sd, "%.4f"), "s")
    for arm in ["C", "M", "EH", "EL"]:
        v = s2.get(("E", arm, "timing", "e2e_mean"), float("nan"))
        if v == v:
            add("E", "chain", "end-to-end, %s" % arm, f(v, "%.4f"), "s")
    write("TS2_sim_detail.csv", header, rows)


def ts3_thresholds(s2):
    """Dark-field statistics, a50 brackets and raw success counts (Table S3).

    The point of this table is to keep the detection comparison auditable: the
    threshold rule, the level it sits above the dark median, the two amplitudes
    that bracket a50, and the integer number of successes out of 20 that the
    interpolation runs between.  Without the integers a reader cannot check the
    interpolation, and without the dark median the "the filter suppresses the
    noise" reading cannot be checked either.

    Only experiment C is used.  Experiment A carries peak and noise-floor
    values on a different normalisation; the two are not on a common scale and
    are deliberately not divided here.
    """
    header = ["chain", "dark median", "dark SD",
              "threshold p95", "thr / median",
              "median of maxima", "a50 (x1e-3)",
              "a50 / a50(C)",
              "lower bracket (x1e-3)", "successes lower / 20",
              "upper bracket (x1e-3)", "successes upper / 20"]
    val = {}
    for r in read_long(S2):
        if r.get("exp") != "C":
            continue
        try:
            val[(r["metric"], r["arm"])] = float(r["value"])
        except (ValueError, KeyError):
            pass
    pd = {}
    for r in read_long(S2):
        if r.get("exp") == "C" and r.get("metric") == "Pd_fpr5":
            pd.setdefault(r["arm"], []).append(
                (float(r["condition"].split("=")[1]), float(r["value"])))
    a50c = val.get(("a50", "C"))
    rows = []
    for a in ARMS:
        if ("a50", a) not in val:
            continue
        a50 = val[("a50", a)]
        pts = sorted(pd.get(a, []))
        lo = hi = None
        for (x1, p1), (x2, p2) in zip(pts, pts[1:]):
            if p1 < 0.5 <= p2:
                lo, hi = (x1, p1), (x2, p2)
                break
        thr = val[("thr_p95", a)]
        bg = val[("bg_median", a)]
        rows.append([a, "%.4f" % bg, "%.5f" % val[("bg_sd", a)], "%.4f" % thr,
                     "%.3f" % (thr / bg),
                     "%.4f" % val[("max_median", a)],
                     "%.3f" % (a50 * 1e3),
                     "%.3f" % (a50 / a50c) if a50c else "-",
                     "%.2f" % (lo[0] * 1e3) if lo else "-",
                     "%d" % round(lo[1] * 20) if lo else "-",
                     "%.2f" % (hi[0] * 1e3) if hi else "-",
                     "%d" % round(hi[1] * 20) if hi else "-"])
    write("TS3_detection_thresholds.csv", header, rows)


def main():
    s1 = load_s1()
    s2 = load_s2()
    print("sources: S1=%d keys, S2=%d keys" % (len(s1), len(s2)))
    tl_literature()
    t1_chains()
    t2_datasets()
    t3_morphology(s1)
    t4_detection(s1)
    tc_claim_scope()
    ts1_equivalence(s1)
    ts5_weight_sensitivity()
    ts6_contrast_isolation()
    if s2:
        t5_sim_summary(s2)
        t5b_sim_detail(s2)
        ts3_thresholds(s2)
    else:
        print("  [skip] %s not found -- S2 tables not built" % S2)


if __name__ == "__main__":
    main()
