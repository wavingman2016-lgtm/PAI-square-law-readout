# -*- coding: utf-8 -*-
"""v0.31 carrier-consistency probe (review round 8).

Round-5 lesson, re-applied: the manuscript body and the table CSVs are TWO
independent carriers of the same numbers and the same terminology.  Round 8
renamed a criterion ("Rayleigh separability" -> "5% valley-depth dip
criterion", Table 4's W2 role cell was the stale carrier), re-worded a bin
count ("65-bin" -> "65-edge (64-bin)") and re-framed a count ("4/4" -> "4 of
6").  This probe scans EVERY csv under paper/tables/ for those strings and for
the other round-8 withdrawals, so a stale note cell cannot survive a body fix.

What it actually caught, and what it initially missed
-----------------------------------------------------
The W3 grid correction is the case in point.  §3 was corrected in the v0.31 body
("N_x raised 601 -> 1501" -> "raised 1000 -> 1501", on the evidence of
`pa_cfg.m` own128: FOV 40 mm, Nx = 1000, dx = 0.04 mm, and of the archived
`W3_fov40` recheck whose axis vectors are 1000 long), but the table carrier
`TableS1_config_audit.csv` kept writing the ASCII-arrow "Nx raised 601 -> 1501"
in its W3 `decision_basis` cell -- so the reader-visible Table S1 went on
shipping the withdrawn value while the prose was already right.  The probe
looked only for the Unicode arrow used in the prose and stayed silent.  Both
glyphs are now scanned, and the control strings were re-based on content that
really exists in the CSVs.

Design notes (per the project's probe iron rules):
  * every residual check has a POSITIVE CONTROL, so "0 hits" can be told apart
    from a broken detector;
  * the file list is globbed, never hard-coded, so a new CSV is covered
    automatically;
  * a CSV legitimately allowed to contain a string declares it in ALLOWED, so
    the exception is explicit rather than silent.

Exit code 0 = PASS.  Any residual hit or dead positive control = FAIL.
"""
import glob
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TAB = os.path.join(ROOT, "paper", "tables")

files = sorted(glob.glob(os.path.join(TAB, "*.csv")))
if not files:
    print("FATAL: no CSV found under %s" % TAB)
    sys.exit(2)

# (label, stale string, positive-control string, ALLOWED relative paths)
#
# CONTROL DISCIPLINE (learned the hard way, 2026-10-17): the first version of
# this table paired each stale string with the NEW prose phrasing from the
# manuscript ("agrees", "less separable", "Exploratory evidence", ...).  None of
# those strings live in a table CSV -- the wording belongs to the prose -- so 11
# of 15 controls came back dead and the probe reported FAIL on an artifact that
# was in fact clean.  A control here must be a string that EXISTS in the scanned
# haystack, otherwise it proves nothing; each one below was verified present.
CHECKS = [
    # round-8 (a): auxiliary endpoint direction
    ("old W1 claim: endpoints disagree", u"disagree in sign", u"d_KS", []),
    ("old W1 claim: more separable", u"more separable", u"W1 single wire", []),
    ("old W1 claim: further apart", u"further apart", u"d_gCNR", []),
    # round-8 (b): E4c pooling / folding bound
    ("old folding claim: bounds", u"bounds folding", u"folding-control output", []),
    ("old folding claim: error bound", u"error bound on folding", u"30 paired draws", []),
    # round-8 (d): bin wording and counts
    ("old bin wording 65-bin", u"65-bin", u"65 edges", []),
    ("old count 4/4 testable", u"4/4 testable", u"saturation", []),
    # round-8 (e): scope-limit wording
    ("old scope limit: harmless", u"harmless", u"65 edges", []),
    # round-8 (g): criterion naming
    ("stale criterion label", u"Rayleigh separability", u"valley-depth dip criterion", []),
    ("old criterion: Rayleigh dip", u"Rayleigh dip", u"valley-depth", []),
    # round-8 (h): SNR scoping and figure provenance
    ("old unscoped SNR figure", u"6\u20138 dB SNR cost at the detection", u"applicable regime", []),
    ("old Fig.5 status", u"Core evidence", u"+0.1742", []),
    # round-8 (d): W3 grid -- BOTH arrow glyphs.  The stale value survived in
    # TableS1_config_audit.csv written with an ASCII "->" while the probe only
    # looked for the Unicode "->" used in the prose: the carrier mismatch this
    # probe exists to catch, missed by its own glyph assumption.
    ("old grid 601 -> 1501 (unicode)", u"601 \u2192 1501", u"1000 -> 1501", []),
    ("old grid 601 -> 1501 (ascii)", u"601 -> 1501", u"1000 -> 1501", []),
    # carried from earlier rounds (still live)
    ("old W5 peak 0.19 MHz", u"0.19 MHz", u"0.188", []),
    ("old W5 centre 0.70 MHz", u"0.70 MHz", u"unfiltered peak sits at 0.188 MHz", []),
]

print("carrier probe: %d CSV files under paper/tables/\n" % len(files))

resid = 0
ctrl_dead = 0
for label, stale, ctrl, allowed in CHECKS:
    hits = []
    ctrl_files = []
    for f in files:
        rel = os.path.relpath(f, ROOT).replace(os.sep, "/")
        try:
            s = io.open(f, encoding="utf-8-sig").read()
        except UnicodeDecodeError:
            print("  [SKIP non-utf8] %s" % rel)
            continue
        if stale in s and rel not in allowed:
            for m in [i for i in range(len(s)) if s.startswith(stale, i)]:
                ln = s[:m].count("\n") + 1
                hits.append("%s:%d" % (rel, ln))
        if ctrl in s:
            ctrl_files.append(rel)
    status = "OK"
    if hits:
        status = "FAIL"
        resid += len(hits)
    if not ctrl_files:
        status = "FAIL(dead control)"
        ctrl_dead += 1
    print("  %-36s %-18s residual=%d  control=%d file(s)"
          % (label, status, len(hits), len(ctrl_files)))
    for h in hits:
        print("        -> %s" % h)

# positive control on the probe itself: content we know exists
print("\n=== probe self-test (positive control) ===")
probe_ok = False
for f in files:
    s = io.open(f, encoding="utf-8-sig").read()
    if u"sensitivity knob" in s and u"d_gCNR" in s:
        probe_ok = True
        print("  detector fires on known content: %s"
              % os.path.relpath(f, ROOT).replace(os.sep, "/"))
        break
if not probe_ok:
    print("  FAIL: detector could not find known-present content")
    ctrl_dead += 1

print("\nresidual hits = %d ; dead controls = %d" % (resid, ctrl_dead))
if resid == 0 and ctrl_dead == 0:
    print("=== VERDICT: PASS ===")
    sys.exit(0)
print("=== VERDICT: FAIL ===")
sys.exit(1)
