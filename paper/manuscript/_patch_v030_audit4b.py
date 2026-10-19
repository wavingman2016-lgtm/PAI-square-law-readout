# -*- coding: utf-8 -*-
"""v0.30 audit-4 leftovers: the three MISS items, matched against the current text."""
import io, sys
MS = 'paper/manuscript/00_manuscript_EN.md'
DONE, MISS = [], []

def edit(old, new, tag):
    s = io.open(MS, encoding='utf-8').read()
    n = s.count(old)
    if n == 0:
        MISS.append(tag); return
    io.open(MS, 'w', encoding='utf-8').write(s.replace(old, new))
    DONE.append('%s (%d)' % (tag, n))

edit(u'> another \u2014 a spread of 0.55. All such points therefore carry',
     u'> a six-replicate ramp study at the same setting \u2014 a spread of 0.13 within one setting, and 0.55\n'
     u'> once the clutter axis is mixed in (0.215 at maximum clutter). All such points therefore carry',
     'P0-1 N_rep policy spread restated')

edit(u'the **measured band centre** of the raw record, $0.35\\times2=0.70$ MHz for W5\u2019s half-power band '
     u'(the 0.35 MHz quoted for W5 is the *verified analysis centre* $f_0$ that was actually used for '
     u'imaging, not a second estimate of the band centre); and the **Q8 effective centre** $1.25$ MHz, '
     u'obtained by the audit estimator from the raw spectrum.',
     u'the **raw unfiltered spectral peak**, $0.188$ MHz for W5; the **verified analysis centre** '
     u'$f_0=0.35$ MHz that was actually used for imaging (not a second estimate of the band centre); '
     u'and the **Q8 effective centre** $1.25$ MHz, obtained by the audit estimator from the raw '
     u'spectrum (Table S1).',
     'P1-4 W5 three frequencies restated')

edit(u'only trends, because a finer grid resolves more coherent side-lobe (0.02\u20130.20\n'
     u'> systematic offset on $C$).',
     u'only trends, because the two grids resolve the coherent side-lobe structure differently.',
     'P1-6 unarchived grid offset removed')

print('=== APPLIED ==='); [print('  OK  ', d) for d in DONE]
print('=== MISS ==='); [print('  MISS', m) for m in MISS]
print('applied=%d miss=%d' % (len(DONE), len(MISS)))
sys.exit(0)
