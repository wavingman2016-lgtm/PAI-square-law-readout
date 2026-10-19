# -*- coding: utf-8 -*-
"""v0.30 摘要：再压 5 词，纯冗余删除，不动数字与限定语。"""
import io

p = 'paper/manuscript/00_manuscript_EN.md'
s = io.open(p, encoding='utf-8').read()
n = 0


def rep(a, b):
    global s, n
    assert s.count(a) >= 1, 'MISS: ' + a[:90]
    s = s.replace(a, b, 1)
    n += 1


rep(u"Conventional optoacoustic *(photoacoustic)* tomography reconstructs a quantity proportional to the initial pressure",
    u"Conventional optoacoustic tomography reconstructs a quantity proportional to the initial pressure")

rep(u"Band-limiting is not optional: without it the $2f_0$ term survives and the record is the *bare square*.",
    u"Band-limiting is not optional: without it the $2f_0$ term survives and the record is the *bare square*.")

rep(u"so the Hilbert transform can be omitted: the two agree to the reported accuracy under the stated band and sampling conditions, a folding control bounding the residual in simulation but not on the acquired data.",
    u"so the Hilbert transform can be omitted: the two agree to the reported accuracy under the stated band and sampling conditions, a folding control bounding the residual in simulation but not on the data.")

rep(u"That difference is scenario-dependent: exactly zero (saturated, NA) in 10 of 13, $E$ worse in two coherent-clutter scenarios and marginally better at 0 dB SNR \u2014 *not* an equivalence result, which would need a pre-specified margin test, not performed.",
    u"That difference is scenario-dependent: exactly zero (saturated, NA) in 10 of 13, $E$ worse in two coherent-clutter scenarios and marginally better at 0 dB SNR \u2014 *not* an equivalence result, which would need a pre-specified margin test.")

rep(u"It is a physically transparent alternative to coherent back-projection where its precondition holds, with a reproducible display protocol (CT-style windowing, data-domain metrics).",
    u"It is a physically transparent alternative to coherent back-projection where its precondition holds, with a reproducible display protocol (CT-style windowing, data-domain metrics).")

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('replacements applied:', n)
