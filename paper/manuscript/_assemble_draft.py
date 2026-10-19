# -*- coding: utf-8 -*-
"""Assemble the paper draft with figures and tables inserted in place.

Source of truth : paper/manuscript/00_manuscript_EN.md  (text master, v0.32)
Output          : paper/manuscript/01_draft_v0.32_assembled.md
Figures         : paper/figures/*.png      (paths are relative to paper/)
Tables          : paper/tables/*.csv

Re-runnable: every insertion is keyed on a unique anchor line, so the script can be
run again after the text master changes.  Nothing is written back to the master.
"""
import io
import os
import re
import csv
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))          # paper/manuscript/
PAPER = os.path.dirname(ROOT)                               # paper/
MASTER = os.path.join(ROOT, "00_manuscript_EN.md")
OUT = os.path.join(ROOT, "01_draft_v0.32_assembled.md")
FIG = os.path.relpath(os.path.join(PAPER, "figures"), ROOT)
TAB = os.path.relpath(os.path.join(PAPER, "tables"), ROOT)

report = []


def fig_block(number, caption, files, status=None):
    """One or more panels stacked under a single Fig. N caption."""
    out = []
    for i, f in enumerate(files):
        p = os.path.join(PAPER, "figures", f)
        if not os.path.exists(p):
            report.append("MISSING FIGURE %s" % p)
            continue
        label = "%s (%s)" % (number, chr(ord("a") + i)) if len(files) > 1 else number
        rel = "../figures/" + f
        out.append("![%s — %s](%s)" % (label, caption.split(".")[0][:70], rel))
    if status:
        caption = caption + "  *[%s]*" % status
    out.append("**%s.** %s" % (number, caption))
    return "\n\n".join(out)


def tab_block(number, caption, csv_name, status=None):
    p = os.path.join(PAPER, "tables", csv_name)
    if not os.path.exists(p):
        report.append("MISSING TABLE %s" % p)
        return "**%s.** %s  *[file missing]*" % (number, caption)
    with io.open(p, "r", encoding="utf-8-sig") as fh:
        rows = [r for r in csv.reader(fh) if any(c.strip() for c in r)]
    if not rows:
        return "**%s.** %s  *[empty file]*" % (number, caption)
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    def esc(c):
        return c.replace("|", "\\|").replace("\n", " ").strip()
    lines = ["| " + " | ".join(esc(c) for c in rows[0]) + " |",
             "|" + "|".join(["---"] * ncol) + "|"]
    for r in rows[1:]:
        lines.append("| " + " | ".join(esc(c) for c in r) + " |")
    body = "\n".join(lines)
    if status:
        caption = caption + "  *[%s]*" % status
    return "**%s.** %s\n\n%s" % (number, caption, body)


def after_row(text, row_prefix, block):
    """Insert `block` immediately after the markdown table row starting with row_prefix.

    ⚠ **不要在 markdown 表格内部使用本函数**。插入 `\\n\\n` + block 会把一张表切断成
    多个片段：Word 里成为若干个独立的表，而且**后续片段的第一行数据会被当成表头加粗**。
    §4 的证据图/表因此改为整组排在 R-表之后（见 main() 中 `_ev` / `before(t, "## 5. ...")`）。
    保留本函数仅供**非表格**锚点使用。
    """
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith(row_prefix):
            return "\n".join(lines[: i + 1]) + "\n\n" + block + "\n" + "\n".join(lines[i + 1:])
    report.append("ANCHOR NOT FOUND (row): %s" % row_prefix)
    return text


def before(text, anchor, block):
    if anchor not in text:
        report.append("ANCHOR NOT FOUND: %r" % anchor[:60])
        return text
    return text.replace(anchor, block + "\n\n" + anchor, 1)


def _write_table_s1_readable():
    """Extract the readable subset of Table S1: audit columns + decision basis.

    The source CSV carries 33 columns (audit + the full ablation set).  Only the
    audit and the configuration-decision columns belong in the manuscript's Table S1;
    the ablation values are reported in Table 4.  Nothing is recomputed here — the
    values are copied through verbatim.
    """
    src = os.path.join(PAPER, "tables", "TableS1_config_audit.csv")
    dst = os.path.join(PAPER, "tables", "TableS1_audit_readable.csv")
    keep = ["id", "cfg_used", "f0_spec_MHz", "f0_eff_MHz", "f0_meas_MHz",
            "Q8_ratio", "D2p_exact", "pearson_sqlaw", "softFail",
            "decision_basis", "perf_metric_used_in_choice"]
    with io.open(src, "r", encoding="utf-8-sig") as fh:
        rows = [r for r in csv.reader(fh) if any(c.strip() for c in r)]
    idx = [rows[0].index(k) for k in keep if k in rows[0]]
    keys = [k for k in keep if k in rows[0]]
    missing = [k for k in keep if k not in rows[0]]
    if missing:
        report.append("TABLE S1 missing columns: %s" % ", ".join(missing))
    with io.open(dst, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(keys)
        for r in rows[1:]:
            w.writerow([(r[i] if i < len(r) else "") for i in idx])
    return dst


def main():
    with io.open(MASTER, "r", encoding="utf-8") as fh:
        t = fh.read()

    # ---------------- front matter ----------------
    t = t.replace(
        "> revision (body + figures/tables + abstract/highlights only): `paper/notes/CHANGELOG_v0.32.md`.",
        "> revision (body + figures/tables + abstract/highlights only): `paper/notes/CHANGELOG_v0.32.md`.\n"
        "> **v0.32 assembled draft** (2026-10-18): `01_draft_v0.32_assembled.md` — the same text with\n"
        "> every available figure and table inserted at its in-text position.  Generated by\n"
        "> `paper/manuscript/_assemble_draft.py`; do not hand-edit the assembled file.", 1)

    # ---------------- §1 : Fig. 1 ----------------
    t = before(t, "---\n\n## 2. Theory", fig_block(
        "Fig. 1",
        "Schematic and three-arm workflow. (a) Raw channels share one pre-processing chain; the two "
        "mandatory pre-conditions for squaring — per-channel DC removal and band-limiting, "
        "$\\beta=B/f_0<1$ — are bracketed together, and the three arms rest on one shared "
        "reconstruction grid, field of view, pixel pitch and kernel, differing only in the detection "
        "operator and its matched geometric compensation. (b) Why a single geometric rule "
        "$g_m=d_m/R$ suffices for every arm: the $1/r$ decay restored by $g_m$ is inherited "
        "automatically by the squared (energy) quantity, illustrated alongside by the detector "
        "geometry (radius $R$, element-to-point distance $d_m$, spherical spreading $p\\propto 1/d_m$) "
        "and by the spectrum after squaring, where the baseband $[0,B]$ is separated from the "
        "double-frequency band $[2f_1,2f_2]$ by the low-pass cut-off. (c) One estimator, two "
        "realizations, and the bare square that is not one of them: the **EI** envelope route (production "
        "default, Hilbert then square) and the **LP** square-and-low-pass route (Hilbert-free) target the "
        "same continuous squared-envelope quantity, related by $\\mathrm{LPF}\\{x^2\\}=\\tfrac12\\lvert z\\rvert^2$ "
        "under the ideal spectral separation of §2.2, and agree to the reported accuracy of §2.7; the bare square omits the "
        "mandatory band-limiting and retains the $2f_0$ term, splitting the point response and leaving "
        "spurious dark bands at the zero crossings, and is carried only as a counter-example. The "
        "operator-path table of §2.1 gives the corresponding operation-by-operation mapping.",
        ["Fig01_schematic.png"]))

    # ---------------- §1 : Table 1 (was Table 5) ----------------
    t = before(t, "---\n\n## 2. Theory", tab_block(
        "Table 1",
        "Positioning against related reconstruction strategies, grouped by *what each method does to a "
        "channel before aggregation* (the axis of §2.1). Columns: per-channel operation, whether an "
        "analytic signal is required, geometric compensation, output domain, and the metrics that work "
        "reports. **No numerical ranking across papers is attempted** — truth definitions, normalisation, "
        "grids and noise models differ, which is the cross-domain rule (F4, §5.6) applied at the "
        "literature level. Row T1-05/T1-06 (pDAS, DMAS) is the precedent for per-channel nonlinearity that "
        "narrows the claim made in §1.2.",
        "Table01_literature_comparison.csv"))

    # ---------------- §2.3 : Fig. 2 ----------------
    t = before(t, "### 2.4 Geometric compensation is a single rule",
               fig_block(
                   "Fig. 2",
                   "Channel-wise squaring is not image-domain squaring. All four fields are "
                   "sampled from **one** back-projection, with the single geometric weight "
                   "$g_m=d_m/R$: "
                   "(a) $I_C=|\\sum_m a_m|$ (Arm C, amplitude domain); "
                   "(b) $I_{BS}=I_C^2$ (the image-domain square; the control quantity of §2.1); "
                   "(c) $I_E=\\sum_m|a_m|^2$ (Arm E, energy domain); "
                   "(d) the cross term $X=I_{BS}-I_E=\\sum_{m\\neq n}a_m a_n^{*}$, i.e. the "
                   "entire coherent part that channel-wise squaring discards; "
                   "(e) the measurable coherence field $\\mu(r)$ on a log colour scale "
                   "(median 0.0060 against the uniform-phase expectation $1/M=0.0078$, "
                   "with pronounced maxima where the channels add coherently); "
                   "(f) the per-pixel residual $|I_{BS}-M\\mu I_E|/I_{BS}$, which sits at "
                   "$2.2\\times10^{-16}$ (double-precision round-off) because the identity is "
                   "enforced by the common sampling, not fitted. This panel is an algebra check on "
                   "**one and the same channel vector**; it is not evidence that the two headline "
                   "routes of §2.1 are numerically equivalent, which is carried by Fig. S1. Semi-circle array, $M=128$, "
                   "$R=55$ mm, three point absorbers, Nx=601, four realisations, "
                   "analysis band [3,7] MHz ($\\beta=0.80<1$, so the narrow-band condition "
                   "holds). $\\mu$ is a diagnostic that requires the coherent numerator, "
                   "not a free by-product of $I_E$; the panels here are estimator/mu maps "
                   "and must not be read as the parameter sweep of Fig. 4.",
                   ["Fig02_identity_crossterm.png"]))

    # ---------------- §2.4 : Fig. S1 -> moved to the Supplementary material ----------------
    # Figure S1 is an S-numbered figure and therefore lives with the other S-numbered items
    # in the Supplementary block below, not inline in §2.4 (the text cites it as
    # "Supplement Fig. S1").  Keeping it in §2.4 made it collide with the supplement's
    # former "Fig. S1 (equivalence table)".

    # ---------------- §3 : Tables 4, 5, S1 ----------------
    t = before(t, "**Pre-processing.**",
               tab_block("Table 4",
                         "Datasets. In-house: six acquisitions (128-element semicircular array ×3; "
                         "rotational 200 steps, rotational 1440 steps and a static 1440-repeat "
                         "acquisition ×3) with array geometry, sampling and "
                         "verified analysis band. External in-vivo: PATATO (mouse, raw time series), "
                         "RSOM (human skin, raw A-lines), 3D-PACT (rat brain, human breast; "
                         "reconstructed volumes only).",
                         "Table04_datasets.csv"))
    t = before(t, "**Configuration integrity (Q8).**",
               tab_block("Table 5",
                         "The three comparison arms $C/M/E$, the image-domain-square control "
                         "$I_{BS}$ and the bare-square counter-example $SQ$ (definitions and domains), "
                         "the four fairness "
                         "constraints F1–F4, the cross-domain rule (a native-domain metric is a "
                         "description of one arm, not a cross-arm comparison; a superiority claim "
                         "needs a common-domain or common-task interpretation; a native-domain "
                         "difference is not evidence of a physical gain), and the replication design "
                         "($N_\\mathrm{rep}$ per axis, grid per "
                         "quantity).",
                         "Table05_arms_and_design.csv"))

    # Table S1 原文件有 33 列（含全部消融指标），直接插入会不可读。
    # 抽出「配置审计 + 决策依据」的可读子集，性能列留在源 CSV 里。
    _write_table_s1_readable()
    # S 编号的表/图统一放文末 Supplementary（不留在正文）——见下方 supp 组装。
    _TAB_S1 = tab_block("Table S1",
                         "Configuration audit and the performance-blind configuration firewall. "
                         "$f_0^{\\mathrm{spec}}$: datasheet nominal; $f_0^{\\mathrm{eff}}$: analysis "
                         "centre actually used; $f_0^{\\mathrm{meas}}$: measured band centre; "
                         "`Q8_ratio` $=f_0^{\\mathrm{meas}}/f_0^{\\mathrm{eff}}$ is the Q8 audit, whose "
                         "nominal-baseline counterpart $f_0^{\\mathrm{meas}}/f_0^{\\mathrm{spec}}$ is "
                         "the one that flags three datasets before re-configuration (§3). "
                         "`D2p_exact` is the **band-plan legality flag**: it is 1 where the legal "
                         "low-pass interval $(B,\\,2f_1)$ is non-empty, i.e. where the Hilbert-free "
                         "low-pass shortcut is admissible in principle. It is a statement about the "
                         "band plan and **not** about numerical accuracy; the numerical quality is "
                         "carried by `pearson_sqlaw`, the envelope correlation between the two routes. "
                         "`softFail` carries the "
                         "advisory audit flags raised by the quality diagnostics (Q4 field of view, Q8 "
                         "band centre) — advisory, never admission criteria; no dataset raised a hard "
                         "failure. `decision_basis` states what fixed each configuration, and "
                         "`perf_metric_used_in_choice` is `no` for every row except W5, which is "
                         "`not verifiable (source unrecoverable)` — no performance "
                         "quantity entered any configuration decision (§3), and W5's unrecoverable "
                         "source cannot be certified as performance-blind. Q8 is an "
                         "audit flag, never an admission criterion; the performance columns of the "
                         "same source file are the ablation values reported in Table 2.",
                         "TableS1_audit_readable.csv")

    # ---------------- §4 : evidence plates, one group per subsection ----------------
    # §4 已由「R1–R8b 追踪表」重构为**双轨散文**（对象阶梯 + 估计量性质），图表因此
    # 改为**就近插入**到各小节末尾（锚点 = 下一节标题），而不是整组堆在 §4 尾部。
    #
    # ⚠ 历史教训：早先 `after_row(t, "| R1 |", ...)` 往 R-表**内部**插图，把一张
    #   markdown 表切成 6 个片段 —— Word 里成为 6 张独立的表，且**后续片段的第一行
    #   数据被当成表头加粗**（首行分别是 R1b / R3 / R4 / R5b / R7）。R-表取消后该
    #   风险消失，但**任何**插图都不得落在 markdown 表块内部；`_build_docx.py` 的
    #   断表守卫会拦截这类碎片。图表出现顺序 = 编号顺序（Elsevier 要求按引用顺序编号）。
    _g41 = [                                             # §4.1 estimator under control
        fig_block("Fig. 3",
                  "Resolution adjudication: the width gap is a reading-level artefact, not a "
                  "resolution gain. (a) single-point PSF with each arm normalised in its own domain: "
                  "$\\mathrm{FWHM}(g^2)=W_{-3\\,\\mathrm{dB}}(g)$, so squaring only moves the reading "
                  "level from −6 dB to −3 dB; (b) E1 apparent width across arms with the cross-arm "
                  "metric $\\Delta$gCNR (the primary admissible cross-arm comparison), which is "
                  "$+0.493$ against $I_C$ and $+0.000$ against $I_M$; (c) E2 two-point criterion — the "
                  "minimum resolved separation is **≤0.30 mm for $I_C$** (the smallest separation tested, "
                  "so the value is search-limited) and **0.50 mm for $I_M$/$I_E$** (mean ± SD over "
                  "$N_{\\rm rep}=4$ independent noise realisations), where a separation is resolved when the "
                  "inter-peak dip $(p_{\\min}-p_{\\mathrm{valley}})/p_{\\min}$ exceeds **0.05** on the normalised "
                  "profile, searched over a non-uniform sweep of 12 separations "
                  "**0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.3, 1.6, 2.0, 2.5, 3.0, 4.0 mm** at the **array centre (0 mm depth)** with "
                  "point targets (Gabor pulse, −6 dB relative bandwidth 0.60) and additive white noise at "
                  "**40 dB** channel SNR; the criterion, pitch, depth, target and noise level are part of the "
                  "caption so that the number is reproducible rather than merely "
                  "quoted; "
                  "(d) E3 contrast ladder: the energy arm read-out ratio follows $A_{\\rm true}^2$ "
                  "(fidelity 1.00–1.97) while the amplitude arms follow $A_{\\rm true}$; (e) "
                  "single-point image, arm $E$ (one realisation, same grid/kernel/window as $C$ and "
                  "$M$); (f) verdict summary, including the identity check: the gap between the "
                  "amplitude-domain width $\\mathrm{FWHM}(\\sqrt{I_E})$ and that of $I_M$ is 30.9 % "
                  "(0.9625 against 0.7354 mm), which is what a reading-level difference produces. "
                  "Widths are measured on Nx = 801; gCNR on "
                  "Nx = 601; arm $E$ is the square-and-low-pass realization $I_E^{\\mathrm{LP}}$ "
                  "throughout.",
                  ["Fig03_resolution_sixpanel.png"]),
        fig_block("Fig. 4",
                  "Four-axis regime behaviour of the Hilbert-free energy-related estimator (a "
                  "perturbation-axis phase diagram — **not** a pixel map of $\\mu$). (a) axis 1, "
                  "wavefront aberration $(\\sigma_\\varphi)$: absolute gCNR; $I_C$ degrades to "
                  "$\\sigma_\\varphi=2$ rad and then plateaus, while $I_M$ and $I_E$ stay at the "
                  "ceiling; (b) axis 2, channel SNR: the largest $\\Delta$gCNR(E−C) margin is "
                  "$+0.582$ at 0 dB; (c) axis 3, random element loss (solid, saturated): gCNR "
                  "saturates for $M$ and $E$ as soon as 12.5 % of elements are lost — so the growing "
                  "E−C margin on this axis reflects $I_C$ degrading, not $I_E$ improving; the dashed "
                  "trace is the non-saturating structural read-out (SSIM vs $I_C$ truth). (d) axis 4, "
                  "coherent clutter: the single exception, where the energy arm degrades first; "
                  "(d′) the clutter profile at $\\sigma_\\varphi=0$. (e) how to read the figure, "
                  "including the cross-arm rules (gCNR only; PSR/width/CNR are within-domain). All "
                  "four axes share the same pre-processing, kernel, grid, field of view and pixel "
                  "layout; the only difference is the detection operator. Arm $E$ is the "
                  "square-and-low-pass realization $I_E^{\\mathrm{LP}}$.",
                  ["Fig04_regime_fourpanel.png"]),
        tab_block("Table 2",
                  "Pre-processing-chain ablation over four definitions (D1 linear envelope; D1² "
                  "channel-wise squared envelope, Hilbert path; D2′ channel-wise squared envelope, "
                  "Hilbert-free path — the method of this paper; D2 bare square). Presented "
                  "**transposed** — one row per quantity, one column per dataset — because the "
                  "quantities outnumber the datasets. Rows report the apparent width (aFWHM) and "
                  "gCNR for each definition, plus the two differences that carry the reading. CNR "
                  "is not tabulated here: it is a domain-dependent quantity, and the four "
                  "definitions do not all live in one domain, so a cross-definition CNR column "
                  "would breach the cross-domain rule F4. The table carries no verdict columns "
                  "(inclusion/exclusion is Table 3 / Table S1). Two readings: ΔgCNR(D2′−D1²) = 0 "
                  "to the reported precision — the Hilbert-free equivalence, whose per-route "
                  "residual is reported in Fig. S1 rather than assumed away — and ΔgCNR(D2′−D2) > 0 "
                  "(band-limiting is necessary). aFWHM is an apparent width and is not a resolution "
                  "claim (§2.5).",
                  "Table02_ablation_readable.csv"),
    ]
    _g42 = [                                             # §4.2 priced against two arms
        fig_block("Fig. 5",
                  "Per-scenario $\\Delta$gCNR (E−C) from the **replicated paired audit** — the 13 "
                  "computational scenarios of the specified stochastic acquisition model, 6 replicates "
                  "each, a pre-fixed seed shared across arms within a replicate. Every bar is "
                  "recomputed from the released audit table (`study_audit.csv`), so the figure carries "
                  "no un-archived exploratory row. The paired mean is **+0.1742** (13/13 positive, "
                  "11/13 significant, still 11/13 after Bonferroni). Arm $E$ is the square-and-low-pass "
                  "realization $I_E^{\\mathrm{LP}}$; the same audit gives $\\Delta$gCNR (E−M) "
                  "−0.0979 — negative in the two coherent-clutter scenarios, zero (gCNR saturated, "
                  "recorded NA) in the other ten, and marginally positive at 0 dB SNR. A non-result and "
                  "**not** a demonstrated equivalence (the margin test E5 is not performed).",
                  ["Fig05_paired_audit.png"]),
        tab_block("Table 6",
                  "Cost and concentration: per-frame wall-clock for $C/M/E$ on a common grid and "
                  "kernel (0.50× for the **instrumented square-and-low-pass realization**, canonical "
                  "timing with warm-up, repetition and SD; **not transferred** to the production EI "
                  "route, since E6 is not run), and the **native-domain** dynamic-range difference "
                  "of $E$ over $M$ (**+2.4 … +16.0 dB**, registry `DR_gain_dB`) together with the "
                  "in-ROI energy-concentration ratio (**1.17–2.60×**, registry `conc_ratio_E_M`), "
                  "both recomputed by `pa_registry_build.py`; these are descriptive cross-domain "
                  "numbers, **not** an imaging gain — the common-domain control "
                  "`pa_common_domain_control.py` gives "
                  "$DR_{\\mathrm{power}}(E)-DR_{\\mathrm{power}}(M^2)=-9.2\\ldots+1.3$ dB and "
                  "$\\mathrm{Conc}(E)/\\mathrm{Conc}(M^2)=0.76\\ldots1.26$; the sidelobe-*purity* "
                  "factor $1.75\\times$ stays withdrawn, and the traceable purity figure is "
                  "$\\mathrm{PSR}(E)/\\mathrm{PSR}(M)=1.38\\times$.",
                  "Table06_cost_and_concentration.csv"),
    ]
    _g43 = [                                             # §4.3 the object ladder
        fig_block("Fig. 6",
                  "The object ladder. In-house datasets ordered by target difficulty — a single thin "
                  "tungsten wire (point absorber, W1), two parallel wires (W2), X-shaped crossed wires "
                  "(W3), V-shaped wires at different depths (W4), the ring/tube phantom (W5) and the "
                  "rotational scan (W6) — all **6/6 KEEP** under their per-dataset verified "
                  "configurations.",
                  ["Fig06_own6_registry.png"]),
        tab_block("Table 3",
                  "Datasets under their per-dataset verified configuration, with contrast gains "
                  "($\\Delta$CNR, $\\Delta$gCNR), the native-domain dynamic-range difference and QC outcome. Admission "
                  "follows the quality gates only (preconditions and consistency, §3); the contrast "
                  "gains are reported metrics, not gates. The internal QC quantities "
                  "(per-dataset valid-channel fraction, edge-energy fraction, baseline CNR, "
                  "$\\rho c^2$-independent envelope and energy dynamic ranges) and the per-dataset "
                  "result paths accompany the released artifacts and are not reproduced here.",
                  "Table03_registry_readable.csv"),
    ]
    _g44 = [                                             # §4.4 in vivo and its boundary
        fig_block("Fig. 7",
                  "In-vivo tissue, with the panels grouped by **what each can support**. (a) "
                  "**algorithm test** on raw channel data — mouse through the unified pipeline: the "
                  "coherent baseline $C$, the envelope baseline $M$, the energy arm $E$ shown both "
                  "through the Hilbert path (D1²) and Hilbert-free (D2′, this work), the image-domain "
                  "square $I_{BS}=I_C^2$, and the provider's official reconstruction, side by side — "
                  "the Hilbert-free path "
                  "reproduces the Hilbert envelope (Pearson 0.9992, amplitude ratio 0.4954) and the "
                  "geometric gate passes against the official map (corr = +0.8434); this is the "
                  "flagged boundary case $\\Delta$gCNR(E−M) = "
                  "−0.298, $\\Delta$gCNR(E−C) = +0.293; (b) **algebraic/implementation check** on "
                  "human skin: the image-domain identity "
                  "$I_{BS}=I_C^2$ holds ($\\Delta$gCNR = −0.0004) — being a strict re-scaling, it "
                  "carries no information about the channel-wise estimator. The rat brain and human "
                  "breast maximum-intensity projections supplied by 3D-PACT are reconstructed "
                  "volumes with no raw channel data, so they cannot validate this method; they are "
                  "retained only as a qualitative display example and are shown in **Fig. S5**, not "
                  "on the main ladder. One animal and one wavelength "
                  "(700 nm) are shown, averaged over 76 frames; the ten wavelengths and the averaged "
                  "frames are repeated observations of one subject under one geometry and are **not "
                  "independent objects**, so the in-vivo material supports implementation consistency "
                  "and bounded feasibility — not cross-organ or cross-subject generalisation.",
                  ["Fig07b_patato_three_arms.png", "Fig07c_rsom_check.png"]),
    ]
    _g45 = [                                             # §4.5 display window
        fig_block("Fig. 8",
                  "Windowing: five settings side by side with black-clipping fractions annotated; "
                  "affine windows leave gCNR/CNR strictly invariant. $WL$ is the window centre and "
                  "$WW$ its full width, so the displayed range is $[WL-WW/2,\\,WL+WW/2]$; the "
                  "quantile-adaptive setting shown is $WL=(p_{50}+p_{99.9})/2$, $WW=p_{99.9}-p_{50}$.",
                  ["Fig08_windowing.png"]),
    ]
    # 锚点 = **下一节标题**；最后一组落在 §5 之前。
    for _anchor, _blk in [("### 4.2 ", _g41), ("### 4.3 ", _g42), ("### 4.4 ", _g43),
                          ("### 4.5 ", _g44), ("## 5. Discussion", _g45)]:
        t = before(t, _anchor, "\n\n".join(_blk))

    # ---------------- §5.3 : windowing table -> Supplementary (as Table S3) ----------------
    _TAB_S3 = tab_block("Table S3",
                         "Window settings side by side with black-clipping fractions annotated "
                         "(quantile-adaptive vs legacy). $WL$ is the window **centre** and $WW$ its "
                         "**full width**, so the displayed range is "
                         "$[WL-WW/2,\\,WL+WW/2]$; the recommended quantile-adaptive setting is "
                         "$WL=(p_{50}+p_{99.9})/2$ with $WW=p_{99.9}-p_{50}$, i.e. exactly "
                         "$[p_{50},p_{99.9}]$ of $I_E$. The legacy cropped window collapses gCNR "
                         "from 1.0000 to 0.8333 while inflating CNR to ≈10¹⁵; the quantile-adaptive "
                         "window keeps 100% structural completeness at 1.88×–6.38× ROI grey-code "
                         "utilisation — a **display-range** gain, not an increase in hardware bit "
                         "depth.",
                         "FigS2_windowing_table.csv")

    # ---------------- §4.2 : common-domain control -> Supplementary (as Table S4) ----------------
    _TAB_S4 = tab_block("Table S4",
                         "Common-domain control, per dataset: the dynamic-range and concentration "
                         "metrics applied to $E$ (the **sample-wise squared-envelope** image "
                         "$BP(|z|^2)=I_E^{SE}$, coded `env2`: channel-wise $\\lvert z\\rvert^2$ formed at the "
                         "sample points, **then** interpolated) and to $M^2$ (the squared "
                         "envelope-stacking image $[BP(|z|)]^2$) in one power domain, so the two arms "
                         "are compared without a domain mismatch. $E$ here is the $I_E^{SE}$ "
                         "realization of §2.7, **not** the production-default envelope route "
                         "$I_E^{EI}$, which squares each interpolated channel *before* the cross-channel "
                         "sum, whereas $M^2$ squares the summed envelope image. This control is computed "
                         "for the SE realization and is therefore **supporting** evidence only; the "
                         "load-bearing control on the production realization with a two-dimensional ROI is in "
                         "§4.2. Inputs are the "
                         "**one-dimensional cross-sections through each reconstructed peak** archived "
                         "with the per-dataset results — $DR$ from the row profile, `Conc` from the "
                         "column profile — with $\\mathrm{Conc}=\\sum_{ROI}I/\\sum_{FOV}I$, ROI = peak "
                         "± `max(2, round(0.05·N))`, the peak located independently per arm, and "
                         "$DR_{\\mathrm{power}}=10\\log_{10}(\\mathrm{peak}/\\mathrm{median})$ on the squared "
                         "image (equivalently $20\\log_{10}$ on the amplitude image). Computed by "
                         "`pa_common_domain_control.py` from the archived `profCol/env2` and "
                         "`profRow/env2` profiles (no re-run); the same source is the released "
                         "`common_domain_control.csv`. These are **profile-based** comparisons; they "
                         "support, but do not replace, the two-dimensional ROI analysis of §4.2.",
                         "TableS4_common_domain_control.csv")

    # ---------------- Table S5 : validation roadmap (moved out of the main text) ----------
    _TAB_S5 = tab_block("Table S5",
                         "Validation roadmap and untested boundaries. The full experiment list E1-E10, "
                         "including partial designs, moved out of the main text; the main-text "
                         "**Table 9** now carries only the claim-validation status. `done` marks an "
                         "experiment actually executed in this work; `partial` marks a design executed "
                         "only in part, with the executed part named; `not done` marks an experiment "
                         "that was **not** performed, and on which no claim in the paper rests. E4c "
                         "(resampling sensitivity check: the record is genuinely resampled "
                         "onto a $k$-times finer grid) was performed and is reported **per "
                         "configuration** against a pre-specified 10% threshold of the scale-corrected "
                         "relative $L_2$ error against the analytic envelope: 6 configurations "
                         "(3 centre frequencies x 2 fractional bandwidths) x 5 replicates = 30 paired "
                         "draws. Three of the six configurations exceed the threshold (f0 = 3 MHz, "
                         "beta = 0.4: -0.0218; f0 = 3 MHz, beta = 0.8: -0.0131; f0 = 10 MHz, "
                         "beta = 0.8: +0.0632) and the sign reverses across the centre frequency among "
                         "the three that exceed it, so the 30 draws are **not** a valid pooled summary "
                         "and none is offered. The "
                         "check does **not** separate the squared-folding error from the interpolation "
                         "and filter implementation effects, so it is **not** an independent folding "
                         "validation and provides **no** folding error bound; it is not transferred to "
                         "$f_s\\le4f_2$ or to the acquired "
                         "datasets' measured out-of-band content.",
                         "TableS5_validation_roadmap.csv")

    # ---------------- Table S6 / S7 / Fig. S4 : Plan-B sensitivity + background-ring audit ----
    # v0.31 (review round 8): the common-domain 2-D control of §4.2 gains an estimator/ROI
    # sensitivity table, a background-annulus audit table and an overlay figure.  All three are
    # exported from the archived registry by pipeline/study/pa_export_tables_s6s7.py and
    # paper/figures/_plot_figS4_roi_audit.py -- no hand-edited numbers.
    _TAB_S6 = tab_block("Table S6",
                        "Estimator and ROI sensitivity of the common-domain 2-D control (Plan B, §4.2). "
                        "Paired $\\Delta\\mathrm{gCNR}(I_E^{EI}-M^2)$ per dataset under (a) histogram bin "
                        "count 33/65/129/257/513 edges, (b) bin-origin shift 0/0.25/0.50/0.75 of a bin "
                        "width at fixed bin count, (c) a complementary distribution-difference metric "
                        "(two-sample "
                        "Kolmogorov-Smirnov, $d_{\\rm KS}$ — a different statistic from gCNR, reported "
                        "alongside it rather than as its binning-free recomputation), and (d) ROI radius "
                        "0.5/1/1.5/2/3x the "
                        "pre-specified radius. The pre-specified setting is 65 edges (64 bins) and "
                        "$k=1$; $k=1$ reproduces the Plan B result of §4.2 to the reported "
                        "precision. Rows with a zero entry are "
                        "the datasets on which both arms saturate gCNR at 1.0000: the paired difference "
                        "is defined and equals 0 (both arms at the metric ceiling), the paired $t$ "
                        "statistic is not computed because the variance is zero, and the metric provides "
                        "no further discrimination — saturation does not make the computed difference "
                        "undefined. The gCNR sign is stable under (a)-(b) for W2/W3/W4/W5, and the KS "
                        "distance moves in the same direction; the only "
                        "knob that flips a sign is the ROI radius, at half the pre-specified radius "
                        "(W3, W4).",
                        "TableS6_estimator_sensitivity.csv")
    _TAB_S7 = tab_block("Table S7",
                        "Background-annulus audit and de-contamination for the same control. The annulus "
                        "content is measured against the coherent baseline $C$: maximum and "
                        "95th-percentile intensity as a fraction of $C$'s peak, the fraction of pixels "
                        "above 5% of it, the number of discrete peaks above 20% of it and the position "
                        "of the strongest one. The number of background pixels $n_{\\rm bg}$ and the "
                        "paired $\\Delta\\mathrm{gCNR}(I_E^{EI}-M^2)$ are given for the pre-registered "
                        "annulus (3-6$r$) and four de-contamination variants: exclusion of discrete "
                        "peaks above 20% of the $C$ peak, and retention of sectors that are clean at "
                        "the 10, 20 and 40 degree levels. `NA` marks a variant whose background sample "
                        "fell below the pre-specified 500-pixel minimum; a zero entry marks saturation "
                        "(both arms at gCNR 1.0000).",
                        "TableS7_ring_audit.csv")
    _FIG_S4 = fig_block("Fig. S4",
                        "Overlay check for the common-domain 2-D control of §4.2: the ROI disk (solid), "
                        "the 3-6$r$ background annulus (dashed) and the target structure drawn on the "
                        "coherent baseline $C$ for all six in-house datasets, with every local maximum "
                        "of $C$ above 20% of the peak that lies inside the annulus marked, and a "
                        "sector dial (green = clean, red = contaminated ten-degree sector under a 20% "
                        "rule) just outside the outer ring. Rows 1-2 show the six datasets; row 3 "
                        "shows the paired $\\Delta\\mathrm{gCNR}(I_E^{EI}-M^2)$ under the original "
                        "annulus and the de-contaminated backgrounds. A reader can see directly which "
                        "annuli contain real secondary structure (W2/W3/W4: a further wire; W5: the "
                        "ring phantom filling the whole annulus) and which do not (W1).",
                        ["FigS4_roi_audit.png"])
    _FIG_S5 = fig_block("Fig. S5",
                        "3D-PACT rat brain (180 x 250 x 120) and human left/right breast "
                        "(800 x 800 x 305) as maximum-intensity projections with explicit quantile "
                        "windows. **Qualitative display only**: the released archives contain "
                        "reconstructed volumes supplied by the authors but no raw channel data, so no "
                        "three-arm comparison and no gCNR, width or PSR is computed or claimed for "
                        "them; the panels establish only that the signal morphology this work "
                        "addresses occurs in clinical in-vivo targets. One animal and one wavelength "
                        "(700 nm) are shown, averaged over 76 frames.",
                        ["Fig07d_3dpact_qualitative.png"])

    # ---------------- Supplement ----------------
    supp = "\n\n---\n\n## Supplementary material\n\n" + fig_block(
        "Fig. S0",
        "Sinogram spot-check for the rotational datasets (data-quality disclosure).",
        ["FigS0_data_sinograms.png"]) + "\n\n" + fig_block(
        "Fig. S1",
        "Agreement of the two realizations of $I_E$: **EI** (envelope route, production default; "
        "coded `consist`) and **LP** (square-and-low-pass, Hilbert-free; coded `direct`). "
        "Four panels per dataset; worst-case max-relative residual "
        "≤0.53 % and relative $L_2$ error ≤0.62 %.",
        ["FigS1_equiv_W1.png", "FigS1_equiv_W2.png", "FigS1_equiv_W3.png"]) + "\n\n" + tab_block(
        "Table S2",
        "EI↔LP agreement on the three fixed-array datasets "
        "(W1–W3): worst-case relative residual, relative $L_2$ error and Pearson correlation "
        "between the two realizations of $I_E$.",
        "FigS1_equiv_readable.csv") + "\n\n" + fig_block(
        "Fig. S2",
        "Speckle statistics and the limits of the reference model. The channel vector is evaluated "
        "at one fixed image location over the stated ensemble. (a) the premises on "
        "$a_m=g_mz_m(\\tau_m)$, with targets $CV_{\\rm meas}=1$, $R_{\\rm meas}=0$ and the Kuiper "
        "statistic $V$ ($0.09$–$0.20$ against $0.016$ expected for a uniform phase distribution); "
        "the panel documents the *input* to the model check and does not by itself establish joint "
        "Gaussianity. (b) ensemble at the centre pixel over $N_{\\rm ens}=120$ realisations: "
        "$CV(I_E)=0.1116$ against the closed form $1/\\sqrt M=0.0884$, and $CV(I_{BS})=1.4315$ "
        "against 1. Under jointly zero-mean *proper* complex-Gaussian channels the coherent "
        "intensity satisfies $CV(I_{BS})\\equiv1$ **whatever** the covariance, so a departure of "
        "$1.4315$ from 1 is **not** explained by inter-channel correlation — correlation changes "
        "the variance $v=\\mathbf 1^{\\mathsf H}R\\mathbf 1$, not this coefficient. (c) theory "
        "self-consistency: a synthetic i.i.d. control hits both closed forms (ratios 0.989 and "
        "0.993), which establishes that the formulas and the implementation are consistent with "
        "the reference model — and **not** that the excess has been located. (d) "
        "$N_{\\rm eff,E}=(\\operatorname{tr}R)^2/\\operatorname{tr}(R^2)\\approx80.3$ for $I_E$, "
        "obtained by moment matching and therefore a *description* of the excess rather than "
        "independent evidence about it; **no effective-channel number is defined for $I_{BS}$** "
        "(the coherent reference is a Gamma shape of 1, not of $M$). (e) speckle maps of one realisation (main panel $I_E$, "
        "inset $I_{BS}$) over the ±4 mm analysis window; the $1/e$ autocorrelation width is "
        "0.33 mm for $I_E$ and 0.13 mm for $I_{BS}$, i.e. of the order of $\\lambda/2=0.15$ mm — a "
        "*spatial* correlation length, not a resolution claim. (f) the full-envelope CV per ring "
        "radius is smooth within a single realisation. The measured excess is reported as an "
        "**empirical finding whose origin is unresolved**: under the stated model it indicates a "
        "departure from stationarity, zero-mean proper complex Gaussianity or "
        "realisation-independence, or a finite-ensemble fluctuation. The candidate mechanisms — "
        "non-Gaussianity, impropriety and variance mixing across realisations — require the "
        "correlated and interval controls of experiment **E8**, which are **not performed**; the "
        "i.i.d. control checks the implementation only. The "
        "finite-ensemble uncertainty is **not quantified**, since the $1/\\sqrt{2N_{\\rm ens}}$ "
        "normal-sample approximation does not apply to the coefficient of variation of an "
        "exponential-type quantity. See §2.3 for the prediction and the random model it assumes.",
        ["FigS3_speckle_cv.png"]) + "\n\n" + _FIG_S4 + "\n\n" + _FIG_S5 + "\n\n" + _TAB_S1 + "\n\n" + _TAB_S3 + "\n\n" + _TAB_S4 + "\n\n" + _TAB_S5 + "\n\n" + _TAB_S6 + "\n\n" + _TAB_S7
    # ---------------- 排除内部脚手架（交付稿不携带）----------------
    # 两类作者端内容不进装配稿：① 图注/表注草稿附录（caption 已随文走）；
    # ② `## Open items before submission` 进度清单（含 🟢🟡 与内部文件名
    # `notes/执行序.md`）。判据一句话：**谁消费它？** 答：只有作者、且只在写作期
    # ⇒ 投稿版里出现它即缺陷。
    #
    # ⚠ **顺序紧要 —— 三次踩坑换来的**：**先剥图注附录，再删 Open items**。
    # 附录的右界锚点正是 `## Open items`；若先删 Open items，那条 lookahead 永远
    # 失配 ⇒ 附录**静默残留**（实测：装配稿尾部仍带 Figure/Table captions 两节，
    # 且随 DOCX 交付）。同理 `supp` 必须插在 Open-items 删除**之后**，否则
    # `.*?(?=\n## References)` 会把整个 Supplement 一起吞掉
    # （曾实测：表数 12→11，Fig. S1 等价表凭空消失）。
    # ⚠ 剥离后**不留任何提示行**：早期版本在这里写入一行
    #   「> Captions travel with their figure or table in place …」，它在 `## Title`
    #   之后 ⇒ 会随 DOCX 一起交付 —— 属作者端脚手架泄漏（检查器 C7c 的模式表不含
    #   该措辞，故未拦截）。现改为删除到空，装配稿与 DOCX 均不再携带。
    t = re.sub(
        r"\n## Figure captions \(draft\)\n\n.*?(?=\n## Open items before submission)",
        "\n", t, flags=re.S)
    t = re.sub(r"\n## Open items before submission.*?(?=\n## References)", "", t, flags=re.S)

    t = t.replace("\n## References", supp + "\n\n---\n\n## References", 1)

    # ---------------- header note ----------------
    t = t.replace(
        "> cells marked `[TODO]` or `[deferred]` are still open.",
        "> cells marked `[TODO]` or `[deferred]` are still open.\n"
        "> **Figures/tables inserted in this assembled draft**: Fig. 1–8, Tables 1–11 and "
        "Fig. S0–S4, Tables S1–S7 — **all in place**; no figure or table is left deferred.", 1)

    with io.open(OUT, "w", encoding="utf-8") as fh:
        fh.write(t)

    print("written:", OUT)
    print("chars  :", len(t))
    if report:
        print("ISSUES:")
        for r in report:
            print("  -", r)
        sys.exit(1)
    print("all anchors and files resolved")


if __name__ == "__main__":
    main()
