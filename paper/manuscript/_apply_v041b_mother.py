#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""v0.41 round, part B: abstract restructure (7 paragraphs -> 4) and the
Pd interval sentence in 4.4.

Part A (_apply_v041_mother.py) already landed the term-level edits.  This
script only touches two blocks, and both are replaced as wholes so a rerun is
detectable rather than cumulative.
"""
import io
import sys

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.abspath(os.path.join(_HERE, '00_manuscript_EN.md')).replace(os.sep, '/')

s = io.open(P, encoding="utf-8").read()
orig = s

# ---------------------------------------------------------------------------
# 1. Abstract: seven paragraphs -> four, and "one filtered definition"
#    -> "one filtered squared-envelope definition"
# ---------------------------------------------------------------------------
A_START = "## Abstract\n\n"
A_END = "\n\n## 1. Introduction"

i0 = s.index(A_START) + len(A_START)
i1 = s.index(A_END, i0)
old_abs = s[i0:i1]

NEW_ABS = (
"Back-projection reconstructs a pressure amplitude, and how each channel is detected before "
"summation is usually treated as an implementation detail. Here it is the design choice under "
"test. Five chains share the same raw records, band-pass, geometry, grid, interpolant and "
"region of interest, and differ only in the per-channel read-out functional and the "
"power-consistent geometric weighting it implies: coherent back-projection (*C*), envelope "
"stacking (*M*), the squared envelope (*EH*), square-and-low-pass (*EL*) and the bare square "
"(*SQ*). *EH* and *EL* are two realizations of one filtered squared-envelope definition; *SQ* "
"is an unfiltered ablation.\n"
"\n"
"On realization, *EL* and *EH* differ by at most 1.17% of the *EH* peak across six acquisitions "
"(0.35 to 5.00 MHz analysis centre, 40 and 100 MHz sampling, 18 to 60 mm field of view). The "
"amplitude ladder gives slopes of 1 and 2, and the *EH*-to-*EL* peak ratio stays at 2.002, 0.1% "
"above the predicted factor of two, the excess being passband loss. That is an implementation "
"residual, not two estimators agreeing. On morphology, retaining the square narrows the "
"apparent width by 8% to 63% relative to *M* and lowers the peak side-lobe level in 5/6 "
"datasets, while staying 1.9 to 7.3 times wider than *C*. These are read-out-level profile "
"changes, not a new transfer function or a resolution gain.\n"
"\n"
"The task-level consequence does not follow from the profile-level change. At a 4:1 amplitude "
"ratio, *M* meets a 5% valley-depth criterion at 1.00 mm while *EL* and *EH* need 1.50 mm. At "
"1:1, *C* meets it at the smallest separation sampled, 0.40 mm, so its limit is unmeasured; "
"*EL* and *EH* need 0.50 mm. For bright-target separability, *EL* exceeds *C* in gCNR in 5/6 "
"datasets, by up to 0.1881 in absolute units, W5 excepted, the disclosed spectrally uncertain "
"boundary case where the coherent baseline saturates. Against *M* it shows no separability "
"advantage in any testable dataset (paired difference \u22120.0171 to \u22120.0095); three "
"saturate. Against the bare square it is higher in three, untestable in two and lower by "
"0.0071 in one. At a common empirical 5% false-alarm design target in the simulated "
"weak-target experiment, *C* reached a detection probability of one half at 0.0019, 2.4 times "
"below every incoherent chain (bootstrap 95% interval 1.96 to 3.08), which did not separate "
"(0.0039 to 0.0045); a different task from bright-target gCNR.\n"
"\n"
"On cost and display, square-law detection is **not** cheaper than envelope stacking end to end "
"(ratio 0.984, within scatter); its detection stage is 2.25 times cheaper but 1.3% of the "
"pipeline, and the 1.88-fold advantage over *C* comes from back-projecting a real rather than a "
"complex field, which envelope stacking shares. A fixed amplitude window black-clips 62.6% of a "
"power-domain image against 0.4% of an amplitude image. The claim is narrower than usual, and "
"the narrowness is the result: one read-out moves five endpoints in different directions. The "
"appropriate read-out depends on the endpoint and the operating condition. All statements are "
"bounded by six phantoms and one limited-view in-vivo case."
)

WRITE_ABS = True
if "one filtered definition" in old_abs:
    pass  # expected on the first run
elif "one filtered squared-envelope definition" in old_abs:
    if old_abs.count("\n\n") == 3:
        print("abstract already four paragraphs and reworded; skipping block 1")
        WRITE_ABS = False
    else:
        print("FAIL: abstract reworded but paragraph count is %d, not 3 separators"
              % old_abs.count("\n\n"))
        sys.exit(1)
else:
    print("FAIL: neither abstract wording found")
    sys.exit(1)

if WRITE_ABS:
    s = s[:i0] + NEW_ABS + s[i1:]

# ---------------------------------------------------------------------------
# 2. 4.4: state the sampling error of Pd and the scope of the Wilson interval
# ---------------------------------------------------------------------------
ANCHOR = ("At $a=0.004$, just below the knee, C is at $P_d=1.00$ while the incoherent chains "
          "sit between 0.20 and 0.55.")
ADD = (
" Each $P_d$ is a binomial estimate from 20 trials and carries a standard error of up to 0.11 "
"near $P_d=0.5$; Table S4 gives the Wilson interval at the amplitude that brackets each $a_{50}$. "
"Those intervals are not a cross-chain test: the brackets sit at different amplitudes for "
"different chains and no multiplicity adjustment is applied, so they are reported to show the "
"precision of a single point and not to convert a non-separation into an equivalence.")

if ADD.strip() in s:
    print("Pd interval sentence already present; skipping block 2")
elif ANCHOR in s:
    s = s.replace(ANCHOR, ANCHOR + ADD, 1)
else:
    print("FAIL: anchor for the Pd interval sentence not found")
    sys.exit(1)

if s == orig:
    print("nothing changed")
    sys.exit(0)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("abstract paragraphs now:", NEW_ABS.count("\n\n") + 1)
print("bytes %d -> %d" % (len(orig), len(s)))
