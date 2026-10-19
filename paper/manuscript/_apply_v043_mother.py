# -*- coding: utf-8 -*-
"""v0.43 = response to the seventh external review (v0.42 manuscript).

Scope: abstract, body text, tables and figure captions.  Declarations are NOT
touched (see the round notes).  Reference markers are written here as
placeholders ({GAMMELL} ...) and resolved by _renumber_refs_v043.py, so that the
final numbering follows first appearance automatically.

Every replacement is exact and asserted; the script aborts rather than guessing.
"""
import io
import re
import sys

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.abspath(os.path.join(_HERE, '00_manuscript_EN.md')).replace(os.sep, '/')

s = io.open(P, encoding="utf-8").read()

REPS = []


def rep(old, new, tag=""):
    REPS.append((old, new, tag))


# =====================================================================
# 0. Front-matter header (stripped on assembly, but must not misstate the version)
# =====================================================================
OLD_HEAD = s[:s.find("---\n\n## Title")]
NEW_HEAD = """> **Status**: draft **v0.43** (2026-10-18). Supersedes v0.42.
> Target journal: **Photoacoustics** (Elsevier). Format `elsarticle.cls`, abstract <=500 words, <=7 keywords.
>
> **v0.43 = response to the seventh external review of v0.42.** Scope: abstract, body text,
> tables and reader-facing captions only. The equivalence of EH and EL is restated as
> conditional on six collected assumptions rather than as an unqualified identity; the
> geometric weight is restated as a model-consistent choice, and a new sensitivity analysis
> (Table S5) recomputes EL under g_m^2, g_m and no compensation and shows the reported
> directions are unchanged; a contrast-isolation table (Table S6) states what each pairwise
> comparison can and cannot attribute; the detection section no longer says "the same
> false-alarm rate"; the in-vivo case is demoted to an illustrative case; nine references
> are added and the whole list is renumbered by first appearance; the Abstract is shortened
> and the Discussion is relieved of duplicated paragraphs. **Declarations, author list,
> funding, CRediT, ethics and consent statements are unchanged** and remain open; this file
> is therefore not yet submission-ready, and no statement in it should be read as final
> metadata.

"""
rep(OLD_HEAD, NEW_HEAD, "H0 header")

# =====================================================================
# 1. R1 — the EH/EL equivalence is conditional (six collected assumptions)
# =====================================================================
rep(
    "Three qualifications are part of the statement, not footnotes to it. (i) The cutoff must lie "
    "**inside** $(B,2f_{\\mathrm{low}})$; taking an endpoint either retains part of the $2f_0$ band "
    "or removes signal band. (ii) The identity is asymptotic in $\\beta$: the residual grows as the "
    "fractional bandwidth approaches unity, and $\\beta\\ge1$ makes the interval empty. (iii) The "
    "pre-square band-pass is a finite-order zero-phase Butterworth filter, so out-of-band energy is "
    "attenuated rather than removed, and squaring doubles every frequency — residual content above "
    "$f_s/4$ folds back into the base band. What the identity therefore licenses is an "
    "*implementation* statement: within the stated band and sampling conditions, a Hilbert transform "
    "can be omitted without changing the image beyond a constant. It does not license the claim that "
    "the two routes are independent estimators, and §4.1 reports the residual accordingly.",

    "Six conditions are part of the statement rather than footnotes to it, and they are collected "
    "here once so that later sections can refer to them without restating them.\n\n"
    "(i) $x(t)$ is real, zero-mean and narrow-band, so that $A(t)$ varies slowly on the scale of "
    "$1/f_0$.\n"
    "(ii) $\\beta=B/f_0<1$. The identity is asymptotic in $\\beta$: the residual grows as the "
    "fractional bandwidth approaches unity, and $\\beta\\ge1$ makes the interval empty.\n"
    "(iii) The cutoff lies **inside** $(B,2f_{\\mathrm{low}})$. Taking an endpoint either retains "
    "part of the $2f_0$ band or removes signal band.\n"
    "(iv) Sampling is adequate for the **squared** spectrum. Squaring doubles every frequency, so "
    "content above $f_s/4$ folds back into the base band, and the identity is then being evaluated "
    "on aliased data.\n"
    "(v) The pre-square band-pass and the post-square low-pass are finite-order zero-phase "
    "Butterworth filters, so out-of-band energy is attenuated rather than removed; the identity is "
    "asymptotic in filter order as well as in $\\beta$.\n"
    "(vi) The record is finite, the filters handle their edges, and the reconstruction interpolates; "
    "each contributes a realization residual that no choice of filter removes.\n\n"
    "What the identity licenses is accordingly an *implementation* statement bounded by (i)–(vi): a "
    "Hilbert transform can be omitted and the image changes only by the factor of two and by the "
    "residual of §4.1. It does not license the claim that the two routes are independent estimators, "
    "and it does not make them interchangeable outside those conditions. §2.3 and Table 2 use \"one "
    "definition, two realizations\" in exactly this conditional sense, and Table 7 records the limit.",
    "R1 assumptions")

rep(
    "**EH and EL are one definition, two realizations.** By §2.2 they differ by a factor of two and "
    "by the filter residual, nothing else.",
    "**EH and EL are one definition, two realizations, under the conditions of §2.2.** Within "
    "(i)–(vi) they differ by a factor of two and by the filter residual, nothing else; outside them "
    "the identity is an approximation whose error this study has not characterised.",
    "R1 heading")

rep(
    "*EH* and *EL* are the **filtered power-domain chains**: one definition in two realizations, a "
    "squared amplitude per channel weighted by $g_m^2$ and, in *EL*, low-passed to remove the carrier.",
    "*EH* and *EL* are the **filtered power-domain chains**: one definition in two realizations under "
    "the conditions of §2.2, a squared amplitude per channel weighted by $g_m^2$ and, in *EL*, "
    "low-passed to remove the carrier.",
    "R1 2.3 opening")

rep(
    "EL and EH are not two methods that happen to agree; they are one definition realized two ways, "
    "related by $\\mathrm{LPF}\\{x^2\\}=\\tfrac12\\lvert z\\rvert^2$.",
    "EL and EH are not two methods that happen to agree; they are one definition realized two ways "
    "within the conditions of §2.2, related by $\\mathrm{LPF}\\{x^2\\}=\\tfrac12\\lvert z\\rvert^2$.",
    "R1 4.1")

rep(
    "EH and EL are the same definition realized two ways, SQ differs from EL by the absence of the "
    "low-pass",
    "EH and EL are the same definition realized two ways under the band and sampling conditions of "
    "§2.2, SQ differs from EL by the absence of the low-pass",
    "R1 1.5")

# =====================================================================
# 2. R2 — the geometric weight is a model-consistent choice, not a necessity
# =====================================================================
rep(
    "The rule is inherited by the square as $g_m^2$: a quantity that scales with pressure squared "
    "scales with $d_m^{-2}$, so its weight must be squared as well. Using $g_m$ for a power-domain "
    "chain would leave a residual $1/d_m$ apodization; using $g_m^2$ for an amplitude-domain chain "
    "would over-correct. This is the only geometric rule used in this work, and it is applied "
    "identically to EH, EL and SQ.",

    "The square is paired with $g_m^2$ so that the compensation stays consistent with that model: a "
    "quantity that scales with pressure squared scales with $d_m^{-2}$, so the model-consistent "
    "weight for a squared read-out is the square of the amplitude-domain weight. This is a design "
    "choice dictated by the adopted spreading model, not a physical necessity for every acquisition. "
    "Using $g_m$ for a power-domain chain would leave a residual $1/d_m$ apodization, and using "
    "$g_m^2$ for an amplitude-domain chain would over-correct. The rule is applied identically to EH, "
    "EL and SQ, and it is the only geometric rule used in this work; §3.3 and Table S5 report what "
    "changes when it is relaxed.",
    "R2 must->model-consistent")

rep(
    "C and M are compensated by $g_m$, the three power-domain chains by $g_m^2$; §2.4 explains why "
    "this is one rule and not a choice.",
    "C and M are compensated by $g_m$, the three power-domain chains by $g_m^2$; §2.4 states the "
    "spreading model under which this is one rule, and reports what relaxing it changes.",
    "R2 2.1 tail")

# =====================================================================
# 3. R3 — what each contrast does and does not isolate
# =====================================================================
rep(
    "— so the comparison isolates the read-out rather than the detector alone. We then answer four "
    "questions in order.",
    "— so the comparison is controlled rather than confounded by the kernel. It is not an isolation "
    "of squaring alone: C against EL changes the per-channel functional, the data type and the "
    "aggregation together, and M against EL changes the functional, the weight, and hence the "
    "distribution and the dynamic range. Table 2 and Table S6 state what each pairwise contrast does "
    "and does not isolate, and every attribution in §4 is made to the contrast that supports it. We "
    "then answer four questions in order.",
    "R3 1.4")

rep(
    "which is exactly the sense in which the comparison below isolates the read-out.",
    "which is the sense in which the comparison below is controlled. The design is a controlled "
    "comparison of read-out families, not an isolation of a single factor: only EL against SQ changes "
    "the low-pass alone, and only EH against EL changes the realization alone. Table S6 gives the "
    "full decomposition.",
    "R3 2.1")

rep(
    "The delay-and-sum weight for a circular or arc array is $g_m=d_m/R$, with $d_m$ the "
    "element-to-centre distance and $R$ the array radius; it corrects the $1/d_m$ spreading of a "
    "cylindrical or spherical wave relative to the nominal radius.",
    "The delay-and-sum weight for a circular or arc array is $g_m=d_m/R$, with $d_m$ the distance "
    "from the reconstruction point to element $m$ and $R$ the array radius; it corrects the $1/d_m$ "
    "spreading of a cylindrical or spherical wave relative to the nominal radius.",
    "R3 2.4 d_m definition")

# =====================================================================
# 4. R2 (result) + R3 (weight) — the sensitivity paragraph in Methods
# =====================================================================
rep(
    "**No chain is rescaled before a metric is computed.**",
    "**Weight sensitivity.** Because the weight is part of how each read-out is implemented, the "
    "M-versus-EL contrast changes the weight as well as the per-channel functional. To separate the "
    "two, EL was recomputed on all six acquisitions with three weights — $g_m^2$ (the main chain), "
    "$g_m$ (the amplitude-domain weight left un-squared) and no geometric compensation — holding the "
    "records, the band-pass, the grid and the low-pass fixed. The three variants read the same "
    "pre-processed records and differ only in the weight applied inside the sum, so this is a "
    "re-analysis of existing data rather than a new acquisition; the $g_m^2$ arm reproduces the EL "
    "values of Table 6 exactly, which is what licenses reading the other two as variations of it. "
    "Table S5 reports the outcome, and §4.4 uses it to bound what the M-versus-EL difference may be "
    "attributed to.\n\n"
    "**No chain is rescaled before a metric is computed.**",
    "R2 3.3 weight sensitivity method")

# =====================================================================
# 5. R2 (result) — the weight does not create the direction
# =====================================================================
rep(
    "Two qualifications keep this from being over-read. First, the negative differences are small — "
    "of order 0.01 on a metric bounded by 1 — and this study does not test a margin, so the correct "
    "statement is **no separability advantage**, not **equivalence**. Second, saturation removes half "
    "the datasets from the comparison; the count of three testable datasets is a limitation of the "
    "metric on these phantoms, not a property of the estimators.",

    "Two qualifications keep this from being over-read. First, the negative differences are small — "
    "of order 0.01 on a metric bounded by 1 — and this study does not test a margin, so the correct "
    "statement is **no separability advantage**, not **equivalence**. Second, saturation removes half "
    "the datasets from the comparison; the count of three testable datasets is a limitation of the "
    "metric on these phantoms, not a property of the estimators.\n\n"
    "**The weight does not create that direction.** The sensitivity analysis of §3.3 recomputes EL "
    "with $g_m$ and with no geometric compensation, and the paired difference stays negative in all "
    "three testable datasets under all three weights: W2 $-0.0115$, $-0.0137$ and $-0.0131$; W3 "
    "$-0.0171$, $-0.0175$ and $-0.0178$; W5 $-0.0095$, $-0.1130$ and $-0.1624$ (for $g_m^2$, $g_m$ "
    "and no compensation). The EL-to-M width ratio likewise stays below one in six of six datasets "
    "under all three. What the weight changes is the size, and on the five datasets other than W5 it "
    "changes the paired difference by at most 0.0023; on W5 the un-squared and absent weights cost EL "
    "a further 0.10 and 0.15 of gCNR, so the boundary case of §6 is also the one where the weighting "
    "rule matters most. The direction reported here is therefore a property of the read-out rather "
    "than of the weighting rule, and the magnitude on W5 is not.",
    "R2 4.4 must->model-consistent result")

# =====================================================================
# 6. R4 — the detection operating point is a design target
# =====================================================================
rep(
    "**Fixed false-alarm rate: a different question, answered separately.**",
    "**A fixed false-alarm design target: a different question, answered separately.**",
    "R4 heading")

rep(
    "The same false-alarm rate requires very different margins above each chain's own background:",
    "The same design target requires very different margins above each chain's own background:",
    "R4 same-rate")

rep(
    "**At the operating point the coherent chain wins and the four incoherent chains tie.** With each "
    "chain thresholded at its own 5% design target, the amplitude at which $P_d=0.5$ is",
    "**Under this threshold-construction scheme the coherent chain needs the least amplitude and the "
    "four incoherent chains tie.** With each chain thresholded at its own 5% design target, the "
    "amplitude at which $P_d=0.5$ is",
    "R4 operating point")

rep(
    "For each chain the threshold is the 95th percentile of the maximum within $\\pm2$ mm of the "
    "target position over 40 independent noise-only realisations ($N_{\\mathrm{dark}}=40$); the "
    "realised rate is not re-measured on an independent noise set, so 5% is the design target of the "
    "threshold rule rather than a certified operating point, and the quantile itself carries the "
    "sampling error of 40 draws.",
    "For each chain the threshold is the 95th percentile of the maximum within $\\pm2$ mm of the "
    "target position over 40 independent noise-only realisations ($N_{\\mathrm{dark}}=40$). Two "
    "consequences are stated rather than corrected. The 95th percentile of 40 draws is interpolated "
    "between the upper two order statistics, so it is supported by two observations and carries the "
    "sampling error of 40 draws. And the realised rate is not re-measured on an independent noise "
    "set, so 5% is the design target of the threshold rule rather than a certified operating point: "
    "the rate a reader would observe on fresh noise is not known from this experiment, and the "
    "interval reported for $a_{50}$ below does not include threshold-estimation error.",
    "R4 3.5 order statistics")

# =====================================================================
# 7. R5 — the in-vivo case is illustrative, not part of the results line
# =====================================================================
rep(
    "### 4.6 Boundary-case feasibility: limited-view in-vivo data",
    "### 4.6 Illustrative limited-view case: in-vivo data",
    "R5 heading")

rep(
    "One in-vivo dataset (PATATO, mouse, 256-element arc with a 91° gap, $n=1$) is available and is "
    "reported here as a boundary case rather than as a validation.",
    "One in-vivo dataset (PATATO, mouse, 256-element arc with a 91° gap, $n=1$) is available. It is "
    "reported here as an illustrative case rather than as a validation: it is not pooled with W1–W6, "
    "it carries no group statistic, and no statement in the abstract or in the conclusion is drawn "
    "from it.",
    "R5 opening")

rep(
    "One in-vivo dataset (PATATO, mouse, 256 channels [15]) is used in §4.6 as a feasibility case with "
    "$n=1$; it is not pooled with W1–W6 and carries no group statistic.",
    "One in-vivo dataset (PATATO, mouse, 256 channels [15]) is used in §4.6 as an illustrative case "
    "with $n=1$; it is not pooled with W1–W6 and carries no group statistic.",
    "R5 3.1")

# =====================================================================
# 8. R8 — the priority claim is bounded by the search
# =====================================================================
rep(
    "To our knowledge, no prior photoacoustic study has explicitly isolated a channel-wise "
    "square-and-low-pass read-out before spatial back-projection, applied the power-consistent "
    "geometric weighting that read-out requires, and compared it against coherent back-projection, "
    "envelope stacking and bare squaring on task-specific endpoints.",

    "In a targeted search of Crossref-indexed metadata and general scholarly web records to 18 "
    "October 2026, we did not identify a photoacoustic study that explicitly isolated a channel-wise "
    "square-and-low-pass read-out before spatial back-projection, applied the power-consistent "
    "geometric weighting that read-out requires, and compared it against coherent back-projection, "
    "envelope stacking and bare squaring on task-specific endpoints. That is a bound on the search, "
    "not a claim of exhaustiveness, and Note S1 states what the search did not cover.",
    "R8 priority")

# =====================================================================
# 9. R9 — reference/claim mismatches
# =====================================================================
# 9a. chi^2_1 is not "fully developed speckle"; that label belongs to the squared envelope.
rep(
    "The low-pass is what converts a $\\chi^2_1$ record [14] (the bare square of a Gaussian channel, "
    "whose statistics are those of fully developed speckle) into a squared envelope;",
    "The low-pass is what converts a $\\chi^2_1$ record — the bare square of a real, zero-mean "
    "Gaussian channel — into a squared envelope, whose statistics are those of a complex Gaussian "
    "field and, in the fully developed case, exponential [14];",
    "R9a chi2 label")

# 9b. the analytic-signal route and the envelope read-out: add a direct signal-processing source
rep(
    "Delay-and-sum, back-projection and their variants estimate this quantity by coherently summing "
    "delayed channel signals [3–6], and they are what makes optical-contrast imaging possible at "
    "depths that optical microscopy cannot reach [7]. In the analytic-signal family an "
    "implementation subsequently applies a Hilbert transform — to form envelopes for incoherent "
    "summation, or analytic signals for coherent summation — and that step is usually presented as "
    "part of the chain rather than as a choice.",

    "Delay-and-sum, back-projection and their variants estimate this quantity by coherently summing "
    "delayed channel signals [3–6, {ORAEVSKY}], and they are what makes optical-contrast imaging "
    "possible at depths that optical microscopy cannot reach [7]. In the analytic-signal family an "
    "implementation subsequently applies a Hilbert transform — to form envelopes for incoherent "
    "summation, or analytic signals for coherent summation — and that step is usually presented as "
    "part of the chain rather than as a choice. Envelope detection by taking the magnitude of the "
    "analytic signal is itself classical in pulse-echo ultrasound [{GAMMELL}], where it separates the "
    "echo envelope from the carrier; what is at issue here is not the operation but where in a "
    "spatial reconstruction it is applied.",
    "R9b Gammell/Oraevsky in 1.1")

# 9c. nonlinear and coherence-based beamformers: split the load carried by [10]
rep(
    "The beamformers that place a non-linearity before summation — DMAS and its filtered variant "
    "[11], and $p$-th-root DAS [12] — multiply channel pairs or compress by a root, and both remain "
    "coherent, because neither forms a squared envelope and neither sums non-negative quantities.",
    "The beamformers that place a non-linearity before summation — DMAS and its filtered variant "
    "[11], and $p$-th-root DAS [12] — multiply channel pairs or compress by a root, and both remain "
    "coherent, because neither forms a squared envelope and neither sums non-negative quantities. "
    "Delay-multiply-and-sum has also been applied to photoacoustic data [{KIRCHNER}], with the same "
    "consequence. A separate family weights each channel by a measure of phase agreement rather than "
    "by a function of its amplitude — the coherence factor, phase-coherence imaging and short-lag "
    "spatial coherence [{CAMACHO},{DAHL}] — and these are coherent operations too: they attenuate "
    "channels that disagree in phase instead of summing non-negative quantities.",
    "R9c coherence beamforming")

# 9d. the identity's classical lineage
rep(
    "For a narrow-band record $x(t)=A(t)\\cos\\phi(t)$ with instantaneous phase $\\phi$ [13] and "
    "$\\beta=B/f_0<1$,",
    "For a narrow-band record $x(t)=A(t)\\cos\\phi(t)$ with instantaneous phase $\\phi$ [13] and "
    "$\\beta=B/f_0<1$ — the squared-envelope construction of classical pulse-echo processing "
    "[{GAMMELL}] —",
    "R9d Gammell in 2.2")

# 9e. acoustic intensity for the "power-like" reading
rep(
    "Under the local progressive-wave, far-field and narrow-band approximation it is at most "
    "proportional to the time-averaged acoustic energy density of the *received* field at the "
    "element, and the chain does not measure that density:",
    "Under the local progressive-wave, far-field and narrow-band approximation it is at most "
    "proportional to the time-averaged acoustic energy density of the *received* field at the "
    "element — the quantity whose intensity for a progressive plane wave is $p^2/(2\\rho c)$ "
    "[{PIERCE}] — and the chain does not measure that density:",
    "R9e Pierce")

# 9f. the threshold rule has a name and a source
rep(
    "**Fixed-false-alarm detection** places every chain at a common empirical 5% false-alarm design "
    "target.",
    "**Fixed-false-alarm detection** follows the Neyman–Pearson construction [{VANTREES}]: the "
    "threshold is set from the noise-only distribution and the detection probability is then measured "
    "at that operating point. Every chain is placed at a common empirical 5% false-alarm design "
    "target.",
    "R9f Van Trees")

# 9g. resolution is a defined quantity, not the profile width
rep(
    "In delay-and-sum imaging the resolution is anisotropic and is set by the summation weights and "
    "the aperture, not by the profile width alone [22];",
    "In delay-and-sum imaging the resolution is anisotropic and is set by the summation weights and "
    "the aperture, not by the profile width alone [22,{NG}];",
    "R9g Ng")

# 9h. model-based inversion, recent
rep(
    "Model-based and time-domain solvers that estimate $p_0$ by minimising a data residual are a "
    "different family [23,24],",
    "Model-based and time-domain solvers that estimate $p_0$ by minimising a data residual are a "
    "different family [23,24,{PARK}],",
    "R9h Park")

# 9i. OADAT: the DOI is the arXiv version, say so
rep(
    "29. Ozdemir F, Lafci B, Deán-Ben XL, Razansky D, Pérez-Cruz F. OADAT: Experimental and Synthetic "
    "Clinical Optoacoustic Data for Standardized Image Processing. Trans Mach Learn Res. 2023. "
    "doi:10.48550/arXiv.2206.08612.",
    "29. Ozdemir F, Lafci B, Deán-Ben XL, Razansky D, Pérez-Cruz F. OADAT: Experimental and Synthetic "
    "Clinical Optoacoustic Data for Standardized Image Processing. Trans Mach Learn Res. 2023; arXiv "
    "version: arXiv:2206.08612. doi:10.48550/arXiv.2206.08612.",
    "R9i OADAT version")

# =====================================================================
# 10. R10 — Abstract: remove parenthetical detail and duplicated interval labels
# =====================================================================
rep(
    "across six acquisitions (0.35 to 5.00 MHz centre, 40 and 100 MHz sampling, 18 to 60 mm field of "
    "view).",
    "across six acquisitions (0.35 to 5.00 MHz analysis centres, 40 and 100 MHz sampling).",
    "R10 abs detail")

rep(
    "Against *M* it shows no separability advantage in any testable dataset (paired difference "
    "−0.0171 to −0.0095); three saturate.",
    "Against *M* it shows no separability advantage in any testable dataset (−0.0171 to −0.0095); "
    "three saturate.",
    "R10 abs paren")

rep(
    "At a common empirical 5% false-alarm design target in the simulated weak-target experiment, *C* "
    "reached a detection probability of one half at 0.0019, 2.4 times below every incoherent chain "
    "(bootstrap 95% interval 1.96 to 3.12), which did not separate (0.0039 to 0.0045); a different "
    "task from bright-target gCNR.",
    "At a common empirical 5% false-alarm design target, *C* reached a detection probability of one "
    "half at 0.0019, 2.4 times below every incoherent chain (95% interval 1.96 to 3.12), which did "
    "not separate (0.0039 to 0.0045); a different task from bright-target gCNR.",
    "R10 abs interval")

rep(
    "The claim is narrow, and the narrowness is the result: one read-out moves five endpoints in "
    "different directions. The appropriate read-out depends on the endpoint and the operating "
    "condition. All statements are bounded by six phantoms and one limited-view in-vivo case.",
    "The claim is narrow, and the narrowness is the result: one read-out moves five endpoints in "
    "different directions, so the appropriate choice depends on the endpoint and the operating "
    "condition. All statements are bounded by six phantoms and one illustrative limited-view in-vivo "
    "case.",
    "R10 abs close")

# =====================================================================
# 11. R11 — Discussion: remove paragraphs that repeat §1.3 and §4 verbatim
# =====================================================================
rep(
    "\n\n**Why the separation matters.** Without it, a gain produced by incoherent $L_2$ aggregation "
    "is attributed to squaring, and a narrowing produced by the read-out level is reported as "
    "resolution. Both misattributions are easy to make, and both are corrected only by measuring the "
    "chains side by side on the same data, which is what the frozen five-chain design does.",
    "",
    "R11 delete why-it-matters")

rep(
    "The cost is attributable only in the M-versus-EL comparison of §4.5, because the C-versus-EL "
    "difference is a whole-chain difference that cannot be charged to the Hilbert transform.",
    "The cost is attributable only in the M-versus-EL comparison of §4.5 (§5.3).",
    "R11 trim cost sentence")

rep(
    "This is also why the result should not be presented as a defeat. A morphological difference at "
    "equal separability is a reproducible property of the read-out, but it is not a task-independent "
    "performance gain. The clearest single instance is the count of local maxima, which is lower than "
    "the coherent image in five of six datasets and lower than the bare square most sharply (W2, 6 "
    "against 23) while not lower than envelope stacking, against which it is one better, one worse "
    "and four tied. What the morphology is not is a resolution gain or a contrast gain, and the same "
    "reweighting that narrows a strong target's main lobe is the one that costs separation to a weak "
    "neighbour (§4.3): one operation seen on two kinds of target, not two findings to be traded off.",

    "This is also why the result should not be presented as a defeat. A morphological difference at "
    "equal separability is a reproducible property of the read-out, not a task-independent "
    "performance gain, and the same reweighting that narrows a strong target's main lobe is the one "
    "that costs separation to a weak neighbour (§4.3): one operation seen on two kinds of target, not "
    "two findings to be traded off.",
    "R11 compress 5.3 third para")

rep(
    "The comparison object of the width claim therefore has to be stated with it. *EL* and *EH* were "
    "narrower than *M* in all six datasets, and the 8–63% range is that comparison and no other. *SQ* "
    "was narrower still in every dataset, which is a statement about its carrier texture rather than "
    "about its transfer function. *C* is the narrowest chain in three datasets and *SQ* in the other "
    "three, so the width ordering is not even stable at the top, and neither the six-of-six nor the "
    "8–63% statement extends to either of them. Apart from *M* being widest everywhere and *EH* "
    "coinciding with *EL*, no complete width ordering holds across the six datasets, which is why the "
    "width claim is stated for one pair of chains and not as a ranking.",

    "The comparison object of the width claim therefore has to be stated with it. *EL* and *EH* were "
    "narrower than *M* in all six datasets, and the 8–63% range is that comparison and no other; *SQ* "
    "was narrower still, which is a statement about its carrier texture rather than about its "
    "transfer function; and the narrowest chain is *C* in three datasets and *SQ* in the other three, "
    "so neither statement extends to them. Apart from *M* being widest everywhere and *EH* coinciding "
    "with *EL*, no complete width ordering holds, which is why the claim is stated for one pair of "
    "chains and not as a ranking.",
    "R11 compress 5.2 scope")

rep(
    " Those are separate studies, and the machinery to run them is in place even where the answer is "
    "not.",
    "",
    "R11 delete closing flourish")

# =====================================================================
# apply
# =====================================================================
bad = 0
for old, new, tag in REPS:
    n = s.count(old)
    if n != 1:
        print("!! [%s] expected 1 occurrence, found %d" % (tag, n))
        bad += 1
        continue
    s = s.replace(old, new)

if bad:
    print("\n%d replacement(s) failed; nothing written." % bad)
    sys.exit(1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("applied %d replacements -> %s" % (len(REPS), P))
