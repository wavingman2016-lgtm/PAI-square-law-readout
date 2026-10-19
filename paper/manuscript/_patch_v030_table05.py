# -*- coding: utf-8 -*-
"""v0.30 audit-5 follow-up: Table05 CSV stale sentences.

Two cells in paper/tables/Table05_arms_and_design.csv carried numbers that were
withdrawn from the mother manuscript in audit round 4:

  L12 note : "finer grids resolve more coherent side-lobe (0.02-0.20 systematic
             offset on C)"  -- the 0.02-0.20 offset has no archived source.
  L13 note : "a single realisation of sigma_phi = 4 rad gave gCNR_C = 0.215 vs
             0.767 (spread 0.55)" -- mis-attribution.  0.2150 is the maximum-
             clutter end of the clutter axis (results/_regime.log,
             sp=0.00 cr=5.0); 0.7674 +/- 0.0507 is a six-replicate mean
             (results/_adv2.log:39, aberr4); the sigma_phi = 4 rad value in the
             regime sweep is 0.6367 (_regime.log, sp=4.00 cr=0.0).

Idempotent, one atomic edit() per item so a MISS does not block the rest.
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV = os.path.join(ROOT, 'paper', 'tables', 'Table05_arms_and_design.csv')

DONE = []
MISS = []


def edit(s, old, new, tag):
    n = s.count(old)
    if n == 0:
        # already applied?  then it is a noop, not a miss.
        if new in s:
            DONE.append('%s (noop, already applied)' % tag)
        else:
            MISS.append(tag)
        return s
    if old == new:
        DONE.append('%s (noop, already applied)' % tag)
        return s
    DONE.append('%s (%d site(s))' % (tag, n))
    return s.replace(old, new)


s = io.open(CSV, encoding='utf-8').read()

# L12 -- withdraw the unsourced grid-offset numbers.
s = edit(
    s,
    'finer grids resolve more coherent side-lobe (0.02-0.20 systematic offset on C)',
    'finer grids resolve the coherent side-lobe structure differently; no numeric offset is quoted here because none is archived',
    'L12 grid-offset withdrawn')

# L13 -- correct the attribution of the gCNR spread.
s = edit(
    s,
    'a single realisation of sigma_phi = 4 rad gave gCNR_C = 0.215 vs 0.767 (spread 0.55)',
    'the sigma_phi = 4 rad screen gave gCNR_C = 0.637 in the regime sweep and 0.7674 +/- 0.0507 over six replicates at the same setting (spread 0.13); 0.55 arises only once the clutter axis is mixed in (0.215 at maximum clutter)',
    'L13 N_rep attribution corrected')

if MISS:
    print('MISS:')
    for m in MISS:
        print('  - ' + m)
    raise SystemExit(1)

io.open(CSV, 'w', encoding='utf-8', newline='').write(s)
print('DONE:')
for d in DONE:
    print('  + ' + d)