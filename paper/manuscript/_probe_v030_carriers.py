# -*- coding: utf-8 -*-
"""v0.30 carrier-consistency probe.

Round5 lesson: the manuscript body and the table CSVs areTWO independent
carriers of the same numbers.  Rounds 1-4 audited only the mother manuscript,
so withdrawn / re-attributed numbers survived in CSV note cells.  This probe
closes that class of blind spot by scanning every CSV under paper/tables/ for
the stale strings that were fixed in the body.

Design notes (per the project's probe iron rules):
  * every residual check has a POSITIVE CONTROL, so a "0 hits" result can be
    distinguished from a broken detector;
  * the file list is globbed, never hard-coded, so a new CSV is covered
    automatically;
  * a CSV that is legitimately allowed to contain a string must declare it in
    ALLOWED so the exception is explicit rather than silent.

Exit code 0 = PASS.  Any residual hit or dead positive control = FAIL.
"""
import glob
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TAB = os.path.join(ROOT, 'paper', 'tables')

files = sorted(glob.glob(os.path.join(TAB, '*.csv')))
if not files:
    print('FATAL: no CSV found under %s' % TAB)
    sys.exit(2)

# (label, stale string, positive-control string, ALLOWED relative paths)
CHECKS = [
    ('withdrawn 0.02-0.20 grid offset', u'0.02-0.20', u'finer grids resolve', []),
    ('withdrawn 0.70 MHz band centre', u'0.70 MHz', u'MHz', []),
    ('old 0.19 MHz spectral peak', u'0.19 MHz', u'0.188', []),
    ('old gCNR 0.763 rounding', u'gCNR_C = 0.767 (', u'0.7674', []),
    ('old DR 9.64 / 7.06', u'+9.64', u'+9.65', []),
    ('old DR 7.06', u'+7.06', u'+7.05', []),
    ('old E/C 0.5028', u'0.5028', u'0.5041', []),
    ('old width 1.5229', u'1.5229', u'1.52265382548273', []),
    ('old ratio 0.4954-0.5000', u'0.4954-0.5000', u'1.17 to 2.60', []),
    ('old audit count 4594.8', u'4594.8', u'KEEP', []),
    ('old detection 0.0440+0.0289=0.0729', u'0.0729', u'0.0734', []),
    ('stale Table S-prefix refs', u'S2.7', u'2.7', []),
    ('stale S4.2 vs Table S4', u'S4.2', u'4.2', []),
    ('CT-style windowing', u'CT-style', u'displays use a stated window', []),
    ('unhyphenated energy related', u'energy related', u'energy-related', []),
    ('energy-density image', u'energy-density', u'energy density', []),
    ('refs.bib literal path', u'refs.bib', u'results/', []),
    ('px-residual claim 0.012-0.032', u'0.012-0.032', u'0.0', []),
    ('PATATO 0.4% width claim', u'0.4% apart', u'%', []),
    ('Fig.3(f) 30.5-31.0 %', u'30.5-31.0', u'Protocol W', []),
]

print('carrier probe: %d CSV files under paper/tables/\n' % len(files))

resid = 0
ctrl_dead = 0
for label, stale, ctrl, allowed in CHECKS:
    hits = []
    ctrl_files = []
    for f in files:
        rel = os.path.relpath(f, ROOT).replace(os.sep, '/')
        try:
            s = io.open(f, encoding='utf-8-sig').read()
        except UnicodeDecodeError:
            print('  [SKIP non-utf8] %s' % rel)
            continue
        if stale in s and rel not in allowed:
            for m in [i for i in range(len(s)) if s.startswith(stale, i)]:
                ln = s[:m].count('\n') + 1
                hits.append('%s:%d' % (rel, ln))
        if ctrl in s:
            ctrl_files.append(rel)
    status = 'OK'
    if hits:
        status = 'FAIL'
        resid += len(hits)
    if not ctrl_files:
        status = 'FAIL(dead control)'
        ctrl_dead += 1
    print('  %-38s %-6s residual=%d  control=%d file(s)'
          % (label, status, len(hits), len(ctrl_files)))
    for h in hits:
        print('        -> %s' % h)

# positive control on the probe itself: a string we know exists somewhere
print('\n=== probe self-test (positive control) ===')
probe_ok = False
for f in files:
    s = io.open(f, encoding='utf-8-sig').read()
    if u'design' in s and u'gCNR' in s:
        probe_ok = True
        print('  detector fires on known content: %s'
              % os.path.relpath(f, ROOT).replace(os.sep, '/'))
        break
if not probe_ok:
    print('  FAIL: detector could not find known-present content')
    ctrl_dead += 1

print('\nresidual hits = %d ; dead controls = %d' % (resid, ctrl_dead))
if resid == 0 and ctrl_dead == 0:
    print('=== VERDICT: PASS ===')
    sys.exit(0)
print('=== VERDICT: FAIL ===')
sys.exit(1)