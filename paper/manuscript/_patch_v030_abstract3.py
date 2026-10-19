# -*- coding: utf-8 -*-
import io

p = 'paper/manuscript/00_manuscript_EN.md'
s = io.open(p, encoding='utf-8').read()
n = 0


def rep(a, b):
    global s, n
    if s.count(a) < 1:
        raise SystemExit('MISS: ' + a[:70])
    s = s.replace(a, b, 1)
    n += 1


D = u'Δ'

rep(u'field at the detector, under a local progressive-wave, far-field, narrow-band approximation and up to an uncalibrated constant',
    u'field at the detector, up to an uncalibrated constant under a local progressive-wave, far-field, narrow-band approximation')

rep(u'We also report the **boundary of applicability**: on limited-view broadband in-vivo data',
    u'We report the **boundary of applicability**: on limited-view broadband in-vivo data')

rep(u'the estimator *loses* contrast **against envelope stacking** (' + D + u'gCNR $=-0.298$) while',
    u'it *loses* contrast **against envelope stacking** (' + D + u'gCNR $=-0.298$) while')

rep(u'(mean **+0.1742**, significant in 11/13 by paired $t$ and still 11/13 after Bonferroni; +0.58 at 0 dB SNR)',
    u'(mean **+0.1742**, significant in 11/13 by paired $t$, still 11/13 after Bonferroni; +0.58 at 0 dB SNR)')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok', n)
