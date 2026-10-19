#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Assemble the v0.48 draft: mother manuscript -> reader-facing draft.

Design (deliberately simpler than the v0.32 assembler)
------------------------------------------------------
The mother manuscript carries explicit anchors ``[[T1]]`` ... ``[[T5]]``,
``[[TS1]]``, ``[[TS2]]``, ``[[F1]]`` ... ``[[F5]]``, ``[[FS1]]``.  This script
replaces each anchor with the corresponding table or figure block.  Captions
live **here** (hard-coded), not in the mother manuscript, because the mother
manuscript's caption appendix is stripped during assembly and would therefore
never reach a reader.

Anything between ``## Title`` and ``## Figure captions (draft)`` is the
delivered body; the appendix itself is dropped with an explicit assertion so a
silent strip cannot happen again.

Input : paper/manuscript/00_manuscript_EN.md
Output: paper/manuscript/01_draft_v0.48_assembled.md
"""
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.dirname(HERE)
MS = os.path.join(HERE, "00_manuscript_EN.md")
OUT = os.path.join(HERE, "01_draft_v0.48_assembled.md")
VERSION = "v0.48"
DATE = "2026-10-19"

report = []


def fig_block(number, caption, files, status=None):
    out = []
    for i, f in enumerate(files):
        p = os.path.join(PAPER, "figures", f)
        if not os.path.exists(p):
            report.append("MISSING FIGURE %s" % p)
            continue
        label = "%s (%s)" % (number, chr(ord("a") + i)) if len(files) > 1 else number
        rel = "../figures/" + f
        out.append("![%s](%s)" % (label, rel))
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
    # reader-facing marker: W5 carries an unresolved spectral centre (§6), so it is
    # flagged wherever a table labels it.  The CSVs keep the bare label so that the
    # probes can still join on it.
    if csv_name[:2] in ("T2", "T4", "T5"):
        body = body.replace("| W5 |", "| W5† |")
    if status:
        caption = caption + "  *[%s]*" % status
    return "**%s.** %s\n\n%s" % (number, caption, body)


# ------------------------------------------------------------------ figures
FIG = {
    "F1": ("Fig. 1",
           "Five detection chains applied to the *same* raw recordings. Each column is one chain "
           "(C coherent back-projection; M envelope stacking; EH Hilbert squared envelope; EL "
           "square-and-low-pass; SQ bare square); each row is one dataset (W1 single wire; W2 two "
           "parallel wires). Every panel is windowed independently between its 1st and 99.5th "
           "percentile, so panel brightness is **not** a quantitative comparison; all metrics in "
           "the text are computed in the float domain before any window. Read across a row: C "
           "retains clutter arcs on W1 and is dominated by clutter on W2, where the target region is "
           "barely visible; M, EH and EL retain it inside a bright skirt, and the second wire shows "
           "up in their profiles as a weaker lobe about 1.8 mm from the first (Fig. 2) rather than "
           "as a clean separation in the image; SQ retains a fine radial texture "
           "whose scale is set by $2f_0$. EH and EL are visually indistinguishable, as expected "
           "from the identity of §2.2. Read down a column to see that the squared-amplitude chains "
           "fill the background with a skirt that is broad for M and narrower for EL.",
           ["Fig1_fivechain_panels.png"]),
    "F2": ("Fig. 2",
           "Lateral profiles through the geometric centre of the target, normalised to each "
           "profile's own maximum, for W1 (left) and W2 (right). The abscissa is the offset from "
           "the peak of the coherent image, shared by all five chains. Three features are read "
           "from these curves and quantified in Table 5. (i) Envelope stacking (M) carries a broad "
           "skirt: on W2 it still stands at 36-44% of its own maximum at $\\pm3$ mm, where C has "
           "returned to 3%, which is why its apparent width is the largest of the five. (ii) EL "
           "and EH have visibly lower skirts "
           "and narrower main lobes than M, while remaining far wider than C. (iii) On both "
           "datasets C is the narrowest but shows oscillatory side lobes, and SQ lies between EL "
           "and C in width while retaining the doubled-carrier texture of the bare square. These "
           "profiles are **not** a resolution measurement: the resolution endpoint is the valley "
           "depth of §4.3, which orders the chains differently.",
           ["Fig2_fivechain_profiles.png"]),
    "F3": ("Fig. 3",
           "Controlled simulation: amplitude law and two-point separation. (a) Peak value against "
           "input amplitude $a\\in\\{0.25,0.5,1,2,4\\}$ on logarithmic axes, six noise realisations "
           "per point (mean $\\pm$ SD smaller than the marker). C and M follow a slope of 1, EH, EL "
           "and SQ a slope of 2, and the EH/EL ratio is 2.002 at every amplitude. "
           "(b) Dip depth between two targets as a function of their separation, at an amplitude "
           "ratio of 1:1; (c) the same at 4:1. The dotted and dashed lines mark the 5% and 20% "
           "criteria. At 1:1, C and SQ first meet the 5% criterion at 0.40 mm - the search bound - "
           "while M, EH and EL need 0.50 mm. At 4:1 the ordering changes against the squared "
           "read-out: C still meets it at 0.40 mm and SQ at 0.60 mm, M at 1.00 mm, and EH and EL "
           "only at 1.50 mm. Panel (c) is the key counterexample of the study: narrowing of the one-target "
           "profile does not imply an earlier, stable valley between unequal targets, and the two "
           "quantities are measured on different objects - a single main lobe and a two-lobe valley. "
           "The curves plot the mean dip, whereas the limits quoted in Table 4 "
           "require the criterion to hold in at least half of the six realisations *and* the two "
           "peaks to sit within $\\max(0.15,0.3d)$ mm of their true positions, so a mean dip can "
           "exceed 5% at a separation that does not yet meet the joint criterion. The dip is a "
           "morphological endpoint and is reported as a curve rather than as a single threshold, "
           "because at separations below the main-lobe width the value is decided by side-lobe "
           "structure.",
           ["Fig3_sim_amplitude_twopoint.png"]),
    "F4": ("Fig. 4",
           "Detection at a fixed false-alarm design target. The threshold of each chain is the 95th "
           "percentile of the maximum over 40 noise-only realisations, an order statistic that is "
           "interpolated between the upper two draws; it places every chain at a common nominal 5% "
           "false-alarm design target rather than at a measured rate, and §3.5 states what that "
           "leaves unverified. Detection probability is then measured on 20 "
           "independent realisations at fifteen target amplitudes spanning 0.0002 to 0.40, with "
           "$a_{50}$ by linear interpolation between the bracketing amplitudes. (a) $P_d$ against "
           "amplitude, with the amplitude at which $P_d=0.5$ marked; every chain reaches $P_d=1.00$ "
           "at $a\\geq0.02$, so the axis is cut at 0.026 and the plateau is annotated rather than "
           "padded out. (b) the same data as the difference from the coherent baseline, which "
           "reaches its minimum at $a=0.003$, where the difference is $-0.85$ (M), $-0.90$ (EL), "
           "$-0.95$ (EH) and $-0.80$ (SQ). The coherent chain crosses $P_d=0.5$ at "
           "$a_{50}=0.0019$, the bare square at 0.0039, and the three envelope chains together at "
           "about 0.0045 (0.00455, 0.00455 and 0.00445 for M, EH and EL); the four incoherent "
           "chains are therefore not separated from one another, and all of them need about 2.4 "
           "times the coherent amplitude. A lower $a_{50}$ "
           "is not by itself a contrast gain: the read-out is quadratic, so a weaker target is "
           "expanded on a logarithmic scale, and the endpoint answers whether that expansion "
           "survives the noise at a common empirical 5% false-alarm design target, not whether the signal-to-noise ratio "
           "has improved.",
           ["Fig4_sim_detection.png"]),
    "F5": ("Fig. 5",
           "Display and cost. (a) Weak-target display contrast under three window rules (fixed "
           "CT-style WL 0.15 / WW 0.70; percentile 1-99%; dual median-split) for the three "
           "incoherent chains, with the saturated and black-clipped fractions summarised in the panel note rather than on the bars. A single "
           "fixed window saturates all three chains at a 4:1 amplitude ratio and leaves the weak "
           "target with zero displayed contrast; on real data it clips a large fraction of a "
           "squared-amplitude image while sparing the amplitude image, which is a display artefact and "
           "not a property of the estimator. The adaptive rules restore usability without "
           "reversing the order: the envelope image still shows the weak target more clearly "
           "(0.3697 against 0.2566 under the percentile rule). (b) "
           "End-to-end time decomposed into pre-processing, Hilbert transform, detection and "
           "back-projection ($N=10$ after three warm-up passes; bar heights are means and the pass-to-pass SD is quoted in §4.5 rather than drawn). The only "
           "attributable comparison is M against EL, because both use the same real-valued "
           "back-projection, and it amounts to 1.6% end to end - less than the scatter of the "
           "back-projection itself; the detection stage alone is 2.25 times cheaper for EL but is "
           "1.3% of the total. The C-against-EL difference is a whole-chain difference, it is "
           "1.88-fold, and it is produced by the complex-valued back-projection rather than by the "
           "Hilbert transform.",
           ["Fig5_sim_display_cost.png"]),
    "FS1": ("Fig. S1",
            "Supplementary panels: the five chains on W3-W6, each panel windowed between its own "
            "1st and 99.5th percentile. W3 (crossing wires) shows the doubled-carrier texture of "
            "SQ most clearly. W4 (two wires at different depths) shows the strong clutter of C "
            "and the radial texture of SQ against the smooth squared-amplitude images. W5 (ring "
            "phantom) is the boundary case: its 18 mm field of view covers only one arc of a "
            "17.49 mm-radius ring, so the image is a single-sided bulge, and the skirt of "
            "M, EH and EL fills the field (median 0.905, 0.832 and 0.832 of the maximum "
            "respectively, against 0.363 for C) - a direct illustration of the skirt quantified "
            "in Table 5, not a display artefact. W6 (rotational scan) shows two targets with "
            "radial streaks in SQ.",
            ["FigS1_fivechain_panels_extra.png"]),
}

# ------------------------------------------------------------------- tables
TAB = {
    "TL": ("Table 1",
           "Nearest-neighbour comparison of operation placement and aggregation, one column each: is the "
           "quantity squared **per channel**; is a non-linearity applied **per channel before summation**, "
           "that is before back-projection; is the result **low-passed to a squared envelope**; and are "
           "**non-negative quantities summed incoherently**. Two further columns state at what level the "
           "record speaks (**evidence type**) and whether the operation is performed on spatial channels "
           "inside a reconstruction (**spatial back-projection precedent**), so that an analogue is not read "
           "as a precedent. Every answer cell is a single token. **yes** — the cited record explicitly "
           "describes the operation. **NR** — the operation is not explicitly reported in the cited record; "
           "NR states what the record says, not what the method does, so no cell asserts a confirmed absence. "
           "**n.a.** — the question does not apply to that record, either because it has no spatial channel "
           "dimension (L6, second question) or because the operation sits after back-projection (L7, last "
           "question). Rows L1-L6 are the nearest neighbours; L7-L9 are this work. The search behind the "
           "table, the coding rule and a per-cell statement of what each cited record explicitly describes "
           "are in Note S1, and the table locates the contribution rather than claiming priority for the "
           "operator: it supports a bounded claim about the operational placement and controlled evaluation "
           "of the chain.",
           "TL_literature.csv"),
    "T1": ("Table 2",
           "The five detection chains. They differ only in the per-channel quantity that is "
           "back-projected; the back-projection kernel, grid, interpolant and region of interest "
           "are identical. C and M are amplitude-domain read-outs compensated by $g_m=d_m/R$; the "
           "three squared-amplitude chains are compensated by $g_m^2$, which is the weight the spreading "
           "model of §2.4 prescribes for a quantity that scales with pressure squared. That is a "
           "model-consistent choice and not a physical necessity: the same chains run with $g_m$ or "
           "with no compensation are reported in Table S2, where no reported direction of §4 "
           "reverses. The factor 2 in $q_m$ is "
           "chosen so that $q_m$ matches $A_m^2$; the identity of §2.2 carries a $\\tfrac12$.",
           "T1_chains.csv"),
    "T2": ("Table 3",
           "The six in-house acquisitions. All are reconstructed under one protocol; the only "
           "grid difference is W3, which needs a 60 mm field of view because 40 mm truncates the "
           "object. The low-pass cutoff equals the band centre in every case and lies strictly "
           "inside the legal interval $(B,2f_{\\mathrm{low}})$ of §2.2. † W5 carries an unresolved "
           "spectral centre (raw spectral peak 0.19 MHz, measured band centre 1.25 MHz, value used "
           "0.35 MHz); the discrepancy is disclosed, not corrected. W5 is retained for transparency "
           "but is not used as the sole basis of any directional conclusion in this paper.",
           "T2_datasets.csv"),
    "T4": ("Table 5",
           "Morphology on the six acquisitions, from profiles through the geometric centre of the "
           "target. Apparent FWHM is the half-height width of each chain's own profile and is "
           "**not** a resolution; it is reported in millimetres, and every count in the table is an "
           "integer. PSLR is the strongest side-lobe relative to the peak in dB; "
           "the final block of rows counts local maxima above 10% of the profile maximum within 60 "
           "samples of the main peak. Two readings matter. EL is narrower than M in every dataset "
           "(ratio 0.37-0.92), and its PSLR is lower in five of six. SQ is narrower than EL in "
           "every dataset but carries more local maxima in five of six and the same number in the "
           "sixth, which is the texture of the bare square rather than a sharper transfer "
           "function. No single width ordering holds across datasets: M is widest everywhere, but "
           "the narrowest chain is C on three datasets and SQ on the other three. The C entry for "
           "W3 is descriptive only: that image is fragmented into 13 local maxima (§4.2), so it has "
           "no connected main lobe and no half-height width that can be compared across chains; the "
           "entry is excluded from the EL-to-C ratio of §4.2, which is computed on the other five "
           "datasets, and no ratio in this table uses it. Both orderings "
           "survive removal of the boundary case of §6: excluding W5, EL is still narrower than M "
           "in five of five datasets and its PSLR is still lower in four of five, W2 the exception. "
           "† W5 carries the unresolved spectral centre described in §6; it is retained for "
           "transparency but is not used as the sole basis of any directional conclusion.",
           "T4_morphology.csv"),
    "T5": ("Table 6",
           "Separability on the six acquisitions: gCNR on a pre-fixed two-dimensional ROI (disk of "
           "radius 0.5 mm defined by the coherent peak; annulus 3-6 mm; 65 linear edges = 64 "
           "bins), and the paired differences. EL exceeds C in five of six datasets; the "
           "exception is W5, where C saturates at 1.0000. Against M the difference is testable in "
           "three datasets and negative in all three; the other three saturate and the cell reads "
           "NA (sat.), which is not the same as zero and is excluded from the count of testable "
           "datasets rather than counted as a tie. Against SQ the difference is positive in three "
           "datasets, not testable in two where both saturate, and negative in one. gCNR is invariant to "
           "monotone rescaling, which is why it cannot see the "
           "morphological change of Table 5 and why the two tables are reported together. † W5 carries the "
           "unresolved spectral centre of §6 and is also the dataset in which the coherent baseline "
           "saturates; it is retained for transparency but is not used as the sole basis of any "
           "directional conclusion. Excluding it, EL $-$ C is positive in five of five, EL $-$ M is "
           "negative in two of two evaluable datasets and EL $-$ SQ positive in two of three, so no "
           "direction in this table depends on W5.",
           "T5_detection.csv"),
    "T3": ("Table 4",
           "Controlled simulation: the five chains side by side. Amplitude-law slopes are 1 for "
           "the amplitude-domain chains and 2 for the squared-amplitude chains, which is the "
           "read-out's amplitude law and says nothing about material conversion efficiency. "
           "Every entry is a *criterion crossing* and not a limit: it is the first "
           "sampled separation, in ascending order, at which the dip between the two targets "
           "reaches the stated criterion in at least half of the six realisations. It is not a "
           "continuous resolution limit, because the dip is not strictly monotone in separation "
           "below the main-lobe width, so every entry is a crossing point of a noisy curve; the "
           "continuous curves are in Table S6 for that reason. How each column may be read differs "
           "and is stated here rather than inferred from the numbers. The C column takes 0.40 mm "
           "at every amplitude ratio because the coherent chain met the criterion at the first "
           "separation tested, so its limiting separation was **not measured** and every 0.40 mm "
           "entry in that column is the bound of the sweep. The SQ column crosses earliest of all "
           "at 4:1, at 0.60 mm, and that entry is a **texture-sensitive crossing**, not a "
           "resolution result: the curve there is shallow and non-monotone and the profile that "
           "produces it is a doubled-carrier texture. The EH and EL columns are ordinary criterion "
           "crossings. No separation below 0.40 mm was tested, and no entry in the table supports "
           "a resolution claim for C below it. $a_{50}$ "
           "is the amplitude at which $P_d=0.5$ at a common empirical 5% false-alarm design target, quoted in units of "
           "$10^{-3}$ and obtained by linear interpolation between the two bracketing amplitudes "
           "of the fifteen-level amplitude ladder of §3.5; no entry sits on the search bound, and "
           "the brackets and the integer success counts they interpolate between are given in "
           "Table S3. End-to-end times "
           "include the common pre-processing term. The last four rows are ratios computed from "
           "the stage timings, placed in the EL column because EL is their reference chain; the "
           "end-to-end and detection-stage rows answer different questions and must be read "
           "together, since the detection stage is 1.3% of the total.",
           "T3_sim_summary.csv"),
    "TC": ("Table 7",
           "What each of the seven core claims establishes, and what it does not. Each row states a claim, "
           "the section and table or figure that carries it, the conditions under which the "
           "evidence was obtained, and what the claim does **not** establish. The evidence column "
           "names the section that actually reports the number, not the section that introduces "
           "the question, and each entry can be checked there. The scope column lists only "
           "conditions that were varied or measured; a mechanism appears there only where the "
           "corresponding measurement isolates it, so a mechanism that the design does not "
           "separate is placed in the last column instead. The last column is "
           "binding: it repeats the qualification given in the corresponding results section and "
           "in section 6, and a reading that drops it is not supported by this work. Where a row "
           "rests on a contrast between chains, Table S1 states what that contrast varies and what "
           "it can therefore attribute, and where it rests on the geometric weight, Table S2 ranges "
           "that weight over three settings. No row is a "
           "summary of another, and each can be checked against the section it names.",
           "TC_claim_scope.csv"),
}


def main():
    if not os.path.exists(MS):
        print("mother manuscript not found: %s" % MS)
        return 1
    t = io.open(MS, "r", encoding="utf-8").read()

    i0 = t.find("## Title")
    i1 = t.find("## Figure captions (draft)")
    if i0 < 0 or i1 < 0 or i1 <= i0:
        print("anchors not found (## Title / ## Figure captions (draft))")
        return 1
    body = t[i0:i1].rstrip() + "\n"

    # strip any residual author-side scaffolding inside the body
    body = re.sub(r"\n## Open items before submission.*", "\n", body, flags=re.S)

    n_fig = n_tab = 0
    for key, (num, cap, files) in FIG.items():
        anchor = "[[%s]]" % key
        if anchor in body:
            body = body.replace(anchor, fig_block(num, cap, files))
            n_fig += 1
        else:
            report.append("UNUSED FIGURE ANCHOR %s" % anchor)
    for key, (num, cap, csv_name) in TAB.items():
        anchor = "[[%s]]" % key
        if anchor in body:
            body = body.replace(anchor, tab_block(num, cap, csv_name))
            n_tab += 1
        else:
            report.append("UNUSED TABLE ANCHOR %s" % anchor)

    leftover = re.findall(r"\[\[[A-Z0-9]+\]\]", body)
    if leftover:
        report.append("UNREPLACED ANCHORS: %s" % ", ".join(sorted(set(leftover))))

    header = (
        "> **Status**: assembled draft **%s** (%s). Generated by `_assemble_draft_v033.py`.\n"
        "> Mother manuscript: `00_manuscript_EN.md`. Tables: `paper/tables/*.csv`. "
        "Figures: `paper/figures/`.\n"
        "> Target journal: **Photoacoustics** (Elsevier). Abstract <= 500 words, <= 7 keywords.\n"
        "> Figures inserted: %d; tables inserted: %d.\n\n---\n\n" % (VERSION, DATE, n_fig, n_tab)
    )

    io.open(OUT, "w", encoding="utf-8", newline="\n").write(header + body)

    print("assembled -> %s" % OUT)
    print("  figures: %d   tables: %d   body words: %d"
          % (n_fig, n_tab, len(re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body).split())))
    if report:
        print("\n  !! %d issue(s):" % len(report))
        for r in report:
            print("     - %s" % r)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
