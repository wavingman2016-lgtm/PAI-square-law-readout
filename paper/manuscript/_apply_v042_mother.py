# -*- coding: utf-8 -*-
"""v0.42 = novelty repositioning + a set of over-strong interpretive claims.

Every replacement is exact and asserted; the script aborts rather than
guessing.  Run once, then rebuild with _round.py.
"""
import io
import sys

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.abspath(os.path.join(_HERE, '00_manuscript_EN.md')).replace(os.sep, '/')

s = io.open(P, encoding="utf-8").read()

REPS = [
    # ---------------------------------------------------------------- M1 1.2
    # "quadratic in absorption" is a calibration claim the chain cannot make:
    # what is squared is the reconstructed pressure-related amplitude.
    ("determines the contrast law (linear versus quadratic in absorption)",
     "determines the contrast law (linear versus quadratic in the reconstructed "
     "pressure-related amplitude)"),

    # ---------------------------------------------------------------- M2 1.3
    ("The gap is operational rather than nominal, and Table 1 states it as four "
     "questions that a method either answers or does not:",
     "The gap is operational rather than nominal. Square-law processing and related "
     "non-linear operations are established in adjacent fields, but their placement "
     "within a photoacoustic spatial back-projection chain has not been isolated as a "
     "standalone read-out choice. Table 1 therefore frames the gap as four operational "
     "questions that a method either answers or does not:"),

    # ---------------------------------------------------------------- M3 1.3
    ('A cell is coded yes only where the cited record explicitly describes the '
     'operation; otherwise it is coded no, and "not reported" is not distinguished '
     'from "absent".',
     'A cell is coded **yes** only where the cited record explicitly describes the '
     'operation, **NR** where the record does not explicitly report it, and **n.a.** '
     'where the question does not apply; NR is a statement about the record, not '
     'evidence that the operation was absent.'),

    # ---------------------------------------------------------------- M4 1.3
    ("[[TL]]",
     "To our knowledge, no prior photoacoustic study has explicitly isolated a "
     "channel-wise square-and-low-pass read-out before spatial back-projection, "
     "applied the power-consistent geometric weighting that read-out requires, and "
     "compared it against coherent back-projection, envelope stacking and bare "
     "squaring on task-specific endpoints. What the prior art establishes is the "
     "ingredients separately: square-law detection with non-coherent integration in "
     "signal detection [9], envelope detection and non-coherent compounding in "
     "photoacoustic and ultrasound imaging [10], and non-linear pre-summation "
     "beamformers such as delay-multiply-and-sum and $p$-th-root DAS [11,12]. The "
     "unresolved question that this paper treats as experimentally testable is whether "
     "those ingredients, arranged as a channel-wise square-and-low-pass power-domain "
     "back-projection chain, produce improvements that hold across tasks. The claim "
     "made here therefore concerns the operational placement and the controlled "
     "evaluation of that chain; it is not a claim that square-law processing is new.\n\n"
     "[[TL]]"),

    # ---------------------------------------------------------------- M5 2.3
    ("a contrast law quadratic in absorption and a reweighted dynamic range",
     "a contrast law quadratic in the reconstructed pressure-related amplitude and a "
     "reweighted dynamic range"),

    ("which \u00a74.4 measures as a separate endpoint.",
     "which \u00a74.4 measures as a separate endpoint. The quadratic law is a statement "
     "about the reconstructed pressure-related amplitude, not a calibrated law of the "
     "optical absorption coefficient: fluence, propagation, receive response and "
     "calibration are not inverted here (\u00a72.5)."),

    # ---------------------------------------------------------------- M6 2.5
    ("Under the local progressive-wave, far-field and narrow-band approximation it "
     "stands in place of the time-averaged acoustic energy density of the *received* "
     "field at the element, but the chain does not measure that density: DC removal, "
     "the band-pass, the finite-order low-pass, the interpolation and the geometric "
     "weight all act on it, and the constant that would relate the two is "
     "uncalibrated.",
     "The squared read-out is power-like in the algebraic sense that it scales with "
     "the square of the reconstructed pressure-related amplitude; no calibrated "
     "acoustic-intensity or energy-density interpretation is assigned to it. Under the "
     "local progressive-wave, far-field and narrow-band approximation it is at most "
     "proportional to the time-averaged acoustic energy density of the *received* "
     "field at the element, and the chain does not measure that density: DC removal, "
     "the band-pass, the finite-order low-pass, the interpolation and the geometric "
     "weight all act on it, and the constant of proportionality is uncalibrated."),

    # ---------------------------------------------------------------- M7 2.6
    ("by an amount fixed by the read-out level rather than by any change in the "
     "spatial frequency content of the image.",
     "by an amount fixed by the read-out level. For an already formed single-target "
     "profile under the stated monotone-transform approximation, the half-height "
     "narrowing follows from that transform and does not by itself demonstrate new "
     "spatial-frequency information about the object."),

    # the same over-strong phrasing elsewhere: squaring is a pointwise monotone map,
    # so no new information about the object is created, but the spectrum of the image
    # does change.  Say the first, not the second.
    ("so a chain that keeps the square must cross half height at a narrower offset "
     "while its spatial frequency content is unchanged.",
     "so a chain that keeps the square must cross half height at a narrower offset "
     "without acquiring new spatial-frequency information about the object."),

    ("The half-width of the power profile is fixed by $\\mathrm{FWHM}(g^2)="
     "W_{-3\\,\\mathrm{dB}}(g)$ at unchanged spatial frequency content, so the "
     "narrowing follows from the read-out level by construction rather than from new "
     "information about the object.",
     "The half-width of the power profile is fixed by $\\mathrm{FWHM}(g^2)="
     "W_{-3\\,\\mathrm{dB}}(g)$, so the narrowing follows from the read-out level by "
     "construction rather than from new information about the object."),

    ("so its width changes at fixed spatial frequency content (\u00a72.6)",
     "so its width changes at the read-out level (\u00a72.6)"),

    # ---------------------------------------------------------------- M8 1.5
    ("Taken together, the contribution is not the operator, which is classical, but "
     "its placement between the channel and the sum, and the measurement of what that "
     "placement does to morphology, separability, cost and display.",
     "Taken together, the contribution is not the invention of the square-law "
     "operation, which is classical. It is the explicit placement of that operation "
     "before spatial back-projection, the power-consistent geometric weighting that "
     "placement requires, the separation of the low-pass from the bare square, and the "
     "controlled evaluation of the resulting read-out on task-specific endpoints rather "
     "than on morphology alone."),

    # ---------------------------------------------------------------- M9 abstract
    ("*SQ* is an unfiltered ablation.",
     "*SQ* is an unfiltered ablation. Rather than introducing square-law processing, we "
     "isolate its placement and weighting within a back-projection chain."),

    # -------------------------------------------------------------- M10 highlights
    ("- Five detection chains separate squaring, low-pass filtering and aggregation.",
     "- Five PAI read-out chains separate squaring, low-pass filtering and aggregation."),
]

missing = []
for i, (old, new) in enumerate(REPS):
    n = s.count(old)
    if n != 1:
        missing.append((i, n, old[:70]))
        continue
    s = s.replace(old, new, 1)

if missing:
    for i, n, frag in missing:
        print("FAIL rep %02d count=%d  %s" % (i, n, frag))
    sys.exit(1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("applied %d replacements" % len(REPS))
