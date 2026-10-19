#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Assemble the supplementary material as a separate file.

Why this exists
---------------
A 359-row parameter dump is not a main-text table.  Up to v0.33.1 both
supplementary tables were inlined into the main DOCX by
``_assemble_draft_v033.py``, so a reader of the extracted text met a wall of
``experiment | condition | quantity | value | unit`` rows between two main-text
results sections.  Elsevier expects supplementary tables in their own file, and
the main text should only *cite* them.

This script emits ``03_supplementary_v0.48.md`` from the same CSVs, then calls
``_build_docx.build()`` with its module-level paths rebound, so the
supplementary DOCX goes through exactly the same LaTeX/OMML conversion and the
same five guards as the manuscript.  No second renderer.

Outputs
-------
  03_supplementary_v0.48.md
  04_PAI_supplementary_v0.48.docx
"""
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.dirname(HERE)
TBL = os.path.join(PAPER, "tables")

MD = os.path.join(HERE, "03_supplementary_v0.48.md")
DOCX = os.path.join(HERE, "04_PAI_supplementary_v0.48.docx")

TITLE = ("**Supplementary material for: *Square-law detection before back-projection "
         "in photoacoustic imaging: squared-amplitude read-out, apparent profile narrowing and "
         "computational trade-offs***")

TABLES = [
    ("Table S1",
     "What each pairwise contrast in the five-chain design varies, and what it can therefore "
     "attribute. The comparison is controlled — every chain shares the same acquisition, propagation geometry, delay model, interpolation, reconstruction grid, valid mask and summation framework, with the geometric compensation matched to the read-out domain —"
     "but it is not an isolation of "
     "a single factor, and the four contrasts isolate different things. Only EH against EL holds the "
     "definition fixed and changes the realization; only EL against SQ holds everything but the "
     "low-pass fixed; M against EL changes the functional and the weight together, and Table S2 "
     "bounds how much of that difference the weight can carry; C against M changes the aggregation "
     "and the output data type; and C against EL changes the whole read-out family, so no single "
     "factor may be charged to it. Section 4 attributes each statement to the contrast that supports "
     "it, and Table 7 states the corresponding claim boundary. The table is a statement about the "
     "design and carries no measurements.",
     "TS6_contrast_isolation.csv"),
    ("Table S2",
     "Geometric-weight sensitivity for the square-and-low-pass chain. The same "
     "pre-processed records, band-pass, grid, kernel and low-pass were reconstructed with three "
     "weights: $g_m^2$ (the chain used in the main text), $g_m$ (the amplitude-domain weight left "
     "un-squared) and no geometric compensation. Every value is in the data domain before any "
     "display window, on the pre-fixed two-dimensional ROI defined once from the coherent peak, "
     "exactly as in Table 6; the $g_m^2$ rows reproduce the EL values of Table 6 at the four "
     "decimals in which those are reported. Read the table by contrast rather than by absolute value. The paired difference EL $-$ M "
     "is negative in the three testable datasets under all three weights, and the EL-to-M width ratio "
     "is below one in six of six under all three. What the weight changes is the size, and it changes "
     "it almost entirely on W5, the boundary case of section 6, where the gCNR difference moves from "
     "$-0.0095$ to $-0.1130$ and $-0.1624$; on the other five datasets the paired difference "
     "moves by less than $0.0022$. "
     "The weighting therefore modulates the size of the reported effects without reversing their "
     "direction, and the magnitude on W5 is not weight-independent.",
     "TS5_weight_sensitivity.csv"),
    ("Table S3",
     "The detection budget, chain by chain, for the fixed-false-alarm experiment of §4.4: the "
     "median and SD of the dark-field background over the 40 noise-only realisations, the "
     "95th-percentile threshold that the rule places on each chain, that threshold as a multiple "
     "of the chain's own dark median, the median of the per-realisation maxima, $a_{50}$, and the "
     "two amplitudes that bracket $a_{50}$ together with the integer number of successes out of 20 "
     "that the interpolation runs between. The last four columns make the interpolation auditable "
     "without re-running the simulation: each bracket carries exactly 20 realisations, so the "
     "success counts are out of 20 without exception, and the interpolation is linear in the "
     "amplitude itself. Applying the same interpolation in $\\log a$ instead moves $a_{50}$ by at "
     "most 2.5\\% (C, whose bracket spans an octave) and by 0.5 to 0.6\\% for the four incoherent "
     "chains, rewrites no ordering, and can be performed directly from these columns. Two limits "
     "are part of the table. The target peak is not "
     "stored per realisation in this experiment, so a target-to-threshold ratio is not tabulated; "
     "$a_{50}$ is the same information in the detection domain and is reported instead. And each "
     "$a_{50}$ rests on interpolation between two brackets that differ by 7 to 11 successes out of "
     "20, so the point estimate carries the resolution limit of $P_d$ itself: with 20 trials per "
     "amplitude that resolution is 0.05, which bounds how finely $a_{50}$ can be located. The "
     "interval attached to each $a_{50}$ is a bootstrap over those 20 repetitions and is given in "
     "Table S4; it inherits that limit and, because the threshold was never resampled, it is not "
     "the full uncertainty of the operating point. No entry in this table is "
     "a calibrated false-alarm rate: the threshold is the empirical 95th percentile of a finite "
     "sample, and the realised rate on fresh noise was not measured.",
     "TS3_detection_thresholds.csv"),
    ("Table S4",
     "Bootstrap interval for the detection budget of §4.4, computed from the 20 archived "
     "per-realisation outcomes at each of the fifteen target amplitudes of §3.5. $a_{50}$ is recomputed in "
     "each of 4000 percentile-bootstrap resamples: at each amplitude the 20 trial indices are drawn "
     "with replacement, and the same resampled index set is applied to all five chains, because the "
     "five chains read the same synthetic record and only their per-channel functional differs. "
     "That pairing is what makes the EL-to-C interval a paired interval rather than a ratio of two "
     "independent intervals. The ladder was run in three staged passes (four, ten and seven "
     "amplitudes, kept in three archives) whose shared amplitudes carry bit-identical $P_d$, so the "
     "union of fifteen could be merged without mixing realisation sets. Every $a_{50}$ falls at or "
     "below 0.005, every chain reaches $P_d=1.00$ at 0.006, and no replicate is censored, so the eight "
     "amplitudes above 0.005 sit at ceiling and cannot move the estimate. The interval describes trial noise only. The per-realisation dark "
     "maxima were not archived, so the 95th-percentile threshold that each trial was called against "
     "could not be resampled, and no interval on the threshold is available at all; this table must "
     "not be read as a confidence statement about a clinical false-alarm rate. Every arm reaches "
     "$P_d=0.5$ in every resample. The columns headed lower $a$ and "
     "upper $a$ give the amplitudes that bracket $a_{50}$ together with the realised $P_d$ there, "
     "and the last column is the Wilson 95\\% interval of that $P_d$ on 20 trials; it is the "
     "precision of one point, not a cross-chain test.",
     "TS4_detection_bootstrap.csv"),
    ("Table S5",
     "Detector equivalence: EL (square-and-low-pass) against EH (Hilbert squared "
     "envelope), per dataset. The Pearson column is computed on images normalised to "
     "their own maximum; the two difference columns are divided by the maximum of $EH$, "
     "which is one number per dataset and not a per-pixel normalisation, so an entry of "
     "$0.0117$ reads as $1.17\\%$ of the $EH$ peak and not as a correlation coefficient. "
     "The two are "
     "related by $\\mathrm{LPF}\\{x^2\\}=\\tfrac12\\lvert z\\rvert^2$, so they differ by a "
     "constant factor of two plus a filter residual; this table measures the residual, "
     "**not** the agreement of two independent methods. A Pearson correlation near 1 is "
     "therefore expected and is reported for completeness rather than as evidence.",
     "TS1_equivalence.csv"),
    ("Table S6",
     "Supporting detail for the controlled simulation: the full dip-versus-separation "
     "curves at 1:1 and 4:1, the detection curves at a common empirical 5% false-alarm design "
     "target, the three window rules with their saturated and black-clipped fractions, "
     "and the per-stage timing decomposition. Every entry is a mean over the stated "
     "number of realisations; SDs are reported in the text where they are used. The "
     "table is generated from the machine-readable long-format file TS2_sim_detail.csv, "
     "which is released with this material and carries the same values; an entry that "
     "sits at a metric's ceiling is a saturation and is **not** evidence of equivalence "
     "between chains.",
     "TS2_sim_detail.csv"),

]

NOTE_S1 = """**Note S1. Search protocol behind the nearest-neighbour comparison of Table 1.**

*Platforms and date.* Crossref metadata queries (REST API, bibliographic query) and a
general scholarly web search, up to 18 October 2026. No licensed indexing database
(Scopus, Web of Science, PubMed, Embase) was queried with a Boolean string, and no
search-alert or update was run after that date.

*Query strings.* Eight query families were used, each combining "photoacoustic" or
"optoacoustic" with one of: "square-law"; "squared envelope"; "power envelope";
"envelope detection"; "non-coherent compounding"; "non-coherent integration";
"delay-multiply-and-sum"; "p-th root". The same eight were also run with "ultrasound"
in place of the photoacoustic term, to populate the analogue rows L4 and L5.

*Inclusion criteria.* A record was eligible for coding if (i) it describes a
reconstruction or detection chain applied to photoacoustic, optoacoustic or ultrasound
signals; (ii) the placement of the operation relative to summation is described
explicitly enough to be coded from the record; and (iii) for the last column, the
operation is performed on spatial channels inside a reconstruction.

*Exclusion criteria.* (i) Records that exist only as reconstructed images, or as
processed data whose raw channel data could not be recovered, cannot test a channel-wise
step and were not coded. (ii) Records that describe the chain only as "non-linear",
without saying whether the non-linearity precedes summation, were not coded as **yes**,
because the placement is the question. (iii) Non-English records. (iv) Patents,
conference proceedings, theses and preprints, which were not searched at all.

*Not done.* No database-wide protocol, screening log, dual abstraction, inter-rater
agreement statistic, citation chaining or PRISMA flow. The criteria above are stated so
that a reader can check them against the coded cells; they were not applied by two
independent coders, and no record was adjudicated by a third party. The six external
rows (L1–L6) rest on six records — [3], [4], [13], [14], [16] and [17] — which is the
whole evidence base of the comparison. Thirteen records — [9], [10], [15], [21], [23], [24], [32],
[34], [35], [37], [38], [42] and [43] — were added in this version to support statements outside the
table and are not part of the coding.

*Coding rule.* Each answer cell carries exactly one token. **yes** — the cited record explicitly
describes the operation at that position in the chain. **NR** — the record does not explicitly report
it; NR states what the record says, not what the method does, so no cell asserts a confirmed
absence. **n.a.** — the question does not apply to that record, either because it has no spatial
channel dimension (L6, second question) or because the operation sits after back-projection (L7,
last question). Qualification lives in this note and in the table caption, never in a cell.

*Source of each coding.* Each cell is coded from the record's abstract and, where the abstract
does not state the operation, from the corresponding methods statement; the row descriptions below
name what the record explicitly describes. Page-level anchors are deliberately not given: the
publisher versions were not available offline during this revision, and a page reference that a
reader cannot check is worse than none. Adding them at proof stage, against the publisher PDFs, is
the one auditability step still open in this note.

*Per-cell evidence.* Each row is coded from the statement below and from nothing else.
**L1** ([3], [4]) — both records state the delay-and-sum or universal back-projection operation and
say nothing about a per-channel square, a pre-summation non-linearity, a post-square low-pass or an
incoherent sum, hence **yes** only in the last column.
**L2** ([14]) — the record analyses how several apertures combine and describes envelope detection
applied *after* combination; the four detection questions are **NR** because no per-channel
operation is described.
**L3** ([14,15]) — [14] describes averaging envelope images over apertures in a photoacoustic
multi-aperture system and [15] describes multi-angle compounding in pulse-echo ultrasound; both are
incoherent sums of non-negative quantities at the image level, hence **yes** there and **NR** in the
three per-channel columns. The load is split between them so that no single record carries the
coding of two different rows.
**L4** ([16]) — delay-multiply-and-sum is defined by pairwise multiplication of delayed channel
signals before summation, hence **yes** for a pre-summation non-linearity; the products are signed
and no squared envelope is formed, hence **NR** in the remaining columns.
**L5** ([17]) — p-th-root compression is applied to each channel before summation, hence **yes** for
a pre-summation non-linearity, and **NR** elsewhere for the reason given for L4.
**L6** ([13]) — square-law detection followed by a post-detection video filter and non-coherent
integration, hence **yes** for the per-channel square, **yes** for the low-passed squared envelope
and **yes** for incoherent integration; the second question is **n.a.** because the integration runs
over temporal looks rather than over spatial channels, and the last column is **NR**.
**L7–L9** — this work, coded from §2.1–§2.3.

*Consequence for reading the table.* An **NR** cell records that the cited record does
not explicitly report the operation. It is not a claim that the operation is absent from
that work, and it is not a claim that no other work reports it: the search above is
targeted, not systematic, and a record outside it would not be represented here."""



NOTE_S2 = r"""**Note S2. Threshold and interpolation conventions in the detection experiment.**

*The threshold.* For each chain the detection threshold is the 95th percentile of the maximum of
the noise-only image within $\pm2$ mm of the target position, taken over 40 independent noise-only
realisations. Three properties follow from that construction, and none of them is corrected
anywhere in the paper. (i) The 95th percentile of 40 draws falls between the upper two order
statistics, so it is supported by two observations rather than by a modelled tail. (ii) The
realised false-alarm rate on fresh noise was never re-measured; the 5% is the design target of the
rule, not a property of the data that a reader could reproduce from a different noise draw.
(iii) The 40 dark maxima were not archived, so the threshold could not be resampled at all, and the
bootstrap of Table S4 describes trial noise only. (iv) A distribution-free 95% interval for the population
95th percentile is spanned by the 36th to 40th of the 40 draws (coverage 0.952), so the threshold rests on
the upper tail of the sample and a fresh calibration would be expected to move it within that span.

*The interpolation.* $a_{50}$ is placed by linear interpolation in the amplitude between the two
tested amplitudes that straddle $P_d=0.5$. Interpolating in $\log a$ instead moves $a_{50}$ by at
most 2.5% for C, whose bracket spans an octave, and by 0.5 to 0.6% for the four incoherent chains,
whose brackets are adjacent steps of the ladder; no ordering of the chains, and no statement that
rests on one, changes. Table S3 gives both brackets and the integer success counts, so either
convention can be applied without re-running the simulation.

*What the brackets do not contain.* Each $a_{50}$ rests on 20 trials per amplitude, so $P_d$ itself
has a resolution of 0.05 and every $a_{50}$ carries that limit. The Wilson intervals of Table S4
are the precision of one point on each curve; they are not a cross-chain test, because the brackets
sit at different amplitudes for different chains and no multiplicity adjustment is applied to them.
"""

NOTE_S3 = """**Note S3. Statistical conventions: no hypothesis test, and how saturation is recorded.**

No hypothesis test is used as the basis of any conclusion, and no $p$-value, confidence interval or
multiplicity correction is reported anywhere in the paper. The analysis pipeline computes no such
test, and none is hidden: the reason is not that a test was run and fell short of significance. With
six heterogeneous phantoms — different objects, bandwidths, sampling rates and fields of view under
one nominal protocol — half of which reach the ceiling of the primary metric, and with paired
differences of order 0.01 on a metric bounded by 1, a formal test would carry less information than
the sign pattern and the size of the difference, and would invite a reader to read one p-value as a
statement about read-outs in general.

Saturation is recorded as **NA**, never as zero. A cell reads NA (sat.) when the metric has reached
its ceiling for both chains in that dataset; that cell is excluded from the count of testable
datasets and is not counted as a tie. "Not testable" and "no difference" are therefore different
entries in every table of this paper.

No equivalence claim is made anywhere. A difference that was not resolved is reported as "no
resolved difference", and the margin that would be needed to demonstrate equivalence is not
pre-specified here; a study that wanted to claim equivalence would have to fix that margin before
the experiment, not after it.
"""



def tab_block(number, caption, csv_name):
    p = os.path.join(TBL, csv_name)
    if not os.path.exists(p):
        raise SystemExit("missing supplementary table: %s" % p)
    with io.open(p, "r", encoding="utf-8-sig") as fh:
        rows = [r for r in csv.reader(fh) if any(c.strip() for c in r)]
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]

    def esc(c):
        return c.replace("|", "\\|").replace("\n", " ").strip()

    lines = ["| " + " | ".join(esc(c) for c in rows[0]) + " |",
             "|" + "|".join(["---"] * ncol) + "|"]
    for r in rows[1:]:
        lines.append("| " + " | ".join(esc(c) for c in r) + " |")
    return "**%s.** %s\n\n%s" % (number, caption, "\n".join(lines))


def main():
    parts = ["## Title", "", TITLE, "", "---", "",
             "This file contains the six supporting tables cited in the main text as "
             "Table S1 to Table S6, and three notes: Note S1 on the search protocol behind Table 1, "
             "Note S2 on the threshold and interpolation conventions of the detection experiment, and "
             "Note S3 on the statistical conventions. Section, equation, figure and "
             "table numbers refer to the main text.", ""]
    for number, caption, csv_name in TABLES:
        parts.append(tab_block(number, caption, csv_name))
        parts.append("")
    parts.append(NOTE_S1)
    parts.append("")
    parts.append(NOTE_S2)
    parts.append("")
    parts.append(NOTE_S3)
    parts.append("")
    body = "\n".join(parts).rstrip() + "\n"

    io.open(MD, "w", encoding="utf-8", newline="\n").write(body)
    print("assembled -> %s (%d chars)" % (MD, len(body)))

    # Reuse the manuscript renderer with its paths rebound.
    sys.path.insert(0, HERE)
    import _build_docx as B
    B.MD = MD
    B.DOCX = DOCX
    rc = B.build()
    if rc != 0:
        print("supplementary DOCX build failed")
        return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
