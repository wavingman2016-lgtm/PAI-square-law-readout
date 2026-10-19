# -*- coding: utf-8 -*-
"""v0.30 自查第三轮：摘要补回 detection-step SNR 代价，并做等量压缩以守住 500 词上限。"""
import io

p = 'paper/manuscript/00_manuscript_EN.md'
s = io.open(p, encoding='utf-8').read()
n = 0


def rep(a, b):
    global s, n
    assert s.count(a) >= 1, 'MISS: ' + a[:90]
    s = s.replace(a, b, 1)
    n += 1


# (1) 补回 detection-step SNR 代价（Highlights/§6/§5.2 均有，摘要独缺）
rep(u"The trade is priced: the transverse point-spread function of $I_E$ is **30.5\u201331.0% broader** than the envelope arm's, under strongly coherent clutter it fails first.",
    u"The trade is priced: the transverse point-spread function of $I_E$ is **30.5\u201331.0% broader** than the envelope arm's, the squaring step costs 6\u20138 dB of SNR, and under strongly coherent clutter $E$ fails first.")

# (2) 等量压缩（每步均为纯冗余删除，不动任何数字与限定语）
rep(u"\u2014 a *state* variable \u2014 and applies the Hilbert transform in the analytic-signal family compared here. We instead form",
    u"\u2014 a *state* variable \u2014 with a Hilbert transform. We instead form")

rep(u"at the detector, under a locally progressive-wave, far-field, narrow-band approximation and up to an uncalibrated constant \u2014 an energy-related image, not an inversion of the source energy density (\u00a72.1, \u00a75.5). Two results follow. (i) The estimator admits two realizations, the envelope route and the square-and-low-pass route, related by",
    u"at the detector, under a local progressive-wave, far-field, narrow-band approximation and up to an uncalibrated constant \u2014 an energy-related image, not an inversion of the source energy density (\u00a72.1, \u00a75.5). (i) The estimator admits an envelope route and a square-and-low-pass route, related by")

rep(u"In a replicated paired audit over the 13 computational scenarios of the specified stochastic model (six pre-fixed-seed replicates each), the square-and-low-pass",
    u"In a replicated paired audit over the 13 computational scenarios of the specified model (six pre-fixed-seed replicates each), the square-and-low-pass")

rep(u"the paired difference against the squared envelope-stacking image is negative in **4/4** testable datasets",
    u"the paired difference against the squared envelope-stacking image is negative in **4/4** testable datasets")
rep(u"and a non-saturating auxiliary endpoint **disagrees in sign**, reported rather than resolved. That difference is scenario-dependent:",
    u"and a non-saturating auxiliary endpoint **disagrees in sign**. That difference is scenario-dependent:")

rep(u"so the Hilbert-free precondition holds and what fails here is not $\\beta$ but the $E$-versus-$M$ ordering",
    u"so the Hilbert-free precondition holds and what fails is not $\\beta$ but the $E$-versus-$M$ ordering")

rep(u"We also report the **boundary of applicability**: on broadband, limited-view in-vivo data (a 91\u00b0 array gap;",
    u"We also report the **boundary of applicability**: on limited-view broadband in-vivo data (a 91\u00b0 array gap;")

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('replacements applied:', n)
