#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""v0.41 round: apply the review-driven edits to the mother manuscript."""
import io
import sys

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.abspath(os.path.join(_HERE, '00_manuscript_EN.md')).replace(os.sep, '/')

s = io.open(P, encoding="utf-8").read()
orig = s

REPS = []

# ---- Highlights 4 -------------------------------------------------------
REPS.append((
    "- No gCNR gain over envelope stacking; gCNR exceeds coherent BP in 5/6 datasets.",
    "- EL exceeds coherent BP on bright-target gCNR in 5/6, but not envelope stacking.",
))

# ---- Abstract: definition sentence in paragraph 1 -----------------------
REPS.append((
    "coherent back-projection (*C*), envelope stacking (*M*), the squared envelope (*EH*), "
    "square-and-low-pass (*EL*) and the bare square (*SQ*).",
    "coherent back-projection (*C*), envelope stacking (*M*), the squared envelope (*EH*), "
    "square-and-low-pass (*EL*) and the bare square (*SQ*). *EH* and *EL* are two realizations "
    "of one filtered definition; *SQ* is an unfiltered ablation.",
))

# ---- Abstract: paragraph 2 ---------------------------------------------
REPS.append((
    "On realization, *EL* and *EH* agree to a Pearson correlation of at least 0.99998 across six "
    "acquisitions (0.35 to 5.00 MHz analysis centre, 40 and 100 MHz sampling, 18 to 60 mm field "
    "of view); their largest pixel difference, relative to the *EH* peak, is 1.17%. The amplitude "
    "ladder gives slopes of 1 and 2, and the *EH*-to-*EL* peak ratio stays at 2.002, 0.1% above "
    "the predicted factor of two, the excess being passband loss. One definition in two "
    "realizations: an implementation residual, not independent estimators agreeing.",
    "On realization, *EL* and *EH* differ by at most 1.17% of the *EH* peak across six "
    "acquisitions (0.35 to 5.00 MHz analysis centre, 40 and 100 MHz sampling, 18 to 60 mm field "
    "of view). The amplitude ladder gives slopes of 1 and 2, and the *EH*-to-*EL* peak ratio stays "
    "at 2.002, 0.1% above the predicted factor of two, the excess being passband loss. That is an "
    "implementation residual, not two estimators agreeing.",
))

# ---- Abstract: detection sentence --------------------------------------
REPS.append((
    "At a common empirical 5% false-alarm target in the simulated weak-target experiment, *C* "
    "reached a detection probability of one half at 0.0019, 2.4 times below every incoherent "
    "chain, which did not separate (0.0039 to 0.0045); a different task from bright-target gCNR.",
    "At a common empirical 5% false-alarm design target in the simulated weak-target experiment, "
    "*C* reached a detection probability of one half at 0.0019, 2.4 times below every incoherent "
    "chain (bootstrap 95% interval 1.96 to 3.08), which did not separate (0.0039 to 0.0045); a "
    "different task from bright-target gCNR.",
))

# ---- Abstract: display sentence ----------------------------------------
REPS.append((
    "A fixed window tuned on an amplitude image black-clips 62.6% of a power-domain image against "
    "0.4% of an amplitude image.",
    "A fixed amplitude window black-clips 62.6% of a power-domain image against 0.4% of an "
    "amplitude image.",
))

# ---- Abstract: closing --------------------------------------------------
REPS.append((
    "The claim is narrower than usual for power-domain imaging, and the narrowness is the result: "
    "one read-out moves five endpoints in different directions.",
    "The claim is narrower than usual, and the narrowness is the result: one read-out moves five "
    "endpoints in different directions.",
))

# ---- 3.5 methods: design target + bootstrap ----------------------------
REPS.append((
    "**Fixed-false-alarm detection** places every chain at a common empirical 5% false-alarm "
    "target.",
    "**Fixed-false-alarm detection** places every chain at a common empirical 5% false-alarm "
    "design target.",
))
REPS.append((
    "This sampling uncertainty is reported as a caveat rather than corrected by post-hoc tuning.",
    "This sampling uncertainty is reported as a caveat rather than corrected by post-hoc tuning. "
    "Because the 20 per-realisation outcomes were archived, $a_{50}$ is also given with a "
    "nonparametric percentile bootstrap over those repetitions (4000 resamples, trials resampled "
    "with replacement within each amplitude, the same resampled trial set applied to all five "
    "chains because they read the same synthetic record); the resulting interval reflects trial "
    "noise only, because the per-realisation dark maxima were not retained and the threshold "
    "therefore cannot be resampled. The intervals are in Table S4.",
))

# ---- 4.1: 1.2% -> 1.17% ------------------------------------------------
REPS.append((
    "the Hilbert transform can be omitted without changing the image by more than 1.2%.",
    "the Hilbert transform can be omitted without changing the image by more than 1.17%.",
))

# ---- 4.4: design target -----------------------------------------------
REPS.append((
    "so that every chain is calibrated to the same empirical 5% false-alarm target.",
    "so that every chain is calibrated to the same empirical 5% false-alarm design target.",
))
REPS.append((
    "With each chain thresholded at its own 5% target,",
    "With each chain thresholded at its own 5% design target,",
))

# ---- 4.4: bootstrap sentence ------------------------------------------
REPS.append((
    "The four incoherent chains are therefore not separated from one another anywhere on the "
    "curve, whereas C requires about 2.4 times less amplitude — 7.6 dB — than EL for the same "
    "detection probability.",
    "The four incoherent chains are therefore not separated from one another anywhere on the "
    "curve, whereas C requires about 2.4 times less amplitude — 7.6 dB — than EL for the same "
    "detection probability. Resampling the 20 repetitions (Table S4) puts the EL-to-C ratio at "
    "1.96 to 3.08 and the whole bootstrap interval of C, 0.0014 to 0.0022, below every incoherent "
    "interval (0.0034 to 0.0049); the four incoherent intervals overlap one another throughout, "
    "which is the interval-level form of the same non-separation.",
))

# ---- 4.5: design target in the endpoint summary ------------------------
# (handled in 5.1/5.5 below)

# ---- 4.6: limited-view downgrades -------------------------------------
REPS.append((
    "a channel-wise incoherent sum amplifies that imbalance rather than correcting it, because "
    "each channel contributes non-negatively and no phase relation can suppress a channel whose "
    "sensitivity lobe points into the gap.",
    "a channel-wise incoherent sum does not restore phase information missing from an incomplete "
    "aperture, and whether that worsens a given endpoint depends on the object, the aperture and "
    "the background.",
))
REPS.append((
    "That is the expected direction for a limited-view acquisition and it is retained as a "
    "boundary rather than averaged away.",
    "That direction is consistent with the hypothesis that missing-angle structure can be "
    "unfavourable to non-negative incoherent aggregation, but one limited-view dataset does not "
    "establish a general limited-view effect; the case is retained as a boundary rather than "
    "averaged away.",
))

# ---- 5.1: design target ------------------------------------------------
REPS.append((
    "The coherent chain was ahead on weak-target detection at a common false-alarm target, and no "
    "chain was ahead end to end on cost.",
    "The coherent chain was ahead on weak-target detection at a common 5% design false-alarm "
    "target, and no chain was ahead end to end on cost.",
))
REPS.append((
    "Weak-target detection at a common empirical false-alarm target puts the coherent arm below "
    "every incoherent chain.",
    "Weak-target detection at a common empirical 5% false-alarm design target puts the coherent "
    "arm below every incoherent chain.",
))

# ---- 5.5: 1.2% -> 1.17%, design target --------------------------------
REPS.append((
    "and it reproduces the squared envelope to within 1.2%.",
    "and it reproduces the squared envelope to within 1.17%.",
))
REPS.append((
    "- **Detection of the weakest target at a fixed false-alarm target.**",
    "- **Detection of the weakest target at a fixed 5% design false-alarm target.**",
))

# ---- 6: design target + bootstrap limitation --------------------------
REPS.append((
    "and the 5% figure should be read as the target of the threshold rule.",
    "and the 5% figure should be read as the design target of the threshold rule. The interval "
    "reported for $a_{50}$ resamples the 20 detection trials only. The threshold those trials were "
    "called against is not resampled, because the individual dark maxima were not archived, so that "
    "interval understates the total uncertainty of the operating point and is not a confidence "
    "statement about a clinical false-alarm rate.",
))

# ---- 7: 1.2% -> 1.17%, closing sentence -------------------------------
REPS.append((
    "The square-and-low-pass route reproduces the squared envelope to within 1.2% across six "
    "acquisitions spanning 0.35–5.00 MHz,",
    "The square-and-low-pass route reproduces the squared envelope to within 1.17% across six "
    "acquisitions spanning 0.35–5.00 MHz,",
))
REPS.append((
    "The conclusion is therefore not that squaring improves or degrades imaging in general, but "
    "that apparent sharpening has to be separated from task-specific resolution, detectability and "
    "cost, and that the separation rather than the operator is what this study supplies.",
    "Channel-wise square-law detection is therefore a power-domain read-out choice, not a "
    "task-independent improvement in image quality: in the tested data it moved apparent "
    "morphology, bright-target separability, valley separation for unequal pairs, weak-target "
    "detection and cost in different directions, and the appropriate choice depends on the task, "
    "the operating point and the acquisition conditions. What this study supplies is that "
    "separation, not a verdict on the operator.",
))

missing = []
for a, b in REPS:
    if a not in s:
        missing.append(a[:70])
        continue
    if s.count(a) > 1:
        missing.append("AMBIGUOUS(%d): %s" % (s.count(a), a[:60]))
        continue
    s = s.replace(a, b, 1)

if missing:
    print("MISSING / AMBIGUOUS anchors:")
    for m in missing:
        print("  -", m)
    sys.exit(1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("applied %d edits" % len(REPS))
