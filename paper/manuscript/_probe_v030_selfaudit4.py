# -*- coding: utf-8 -*-
"""v0.30 audit-4 probe: residuals of every fix made in self-audit rounds 3-4,
plus positive controls so that a zero count cannot be confused with a dead probe."""
import io, re, sys

MS = 'paper/manuscript/00_manuscript_EN.md'
AD = 'paper/manuscript/_assemble_draft.py'
S5 = 'paper/tables/TableS5_validation_roadmap.csv'

ms = io.open(MS, encoding='utf-8').read()
ad = io.open(AD, encoding='utf-8').read()
s5 = io.open(S5, encoding='utf-8').read()

D = u'\u2212'      # minus sign
SEC = u'\u00a7'    # section sign
SQRT = u'\u221a'

# ---------------- residuals: each MUST be 0 ----------------
RESID = [
    (u'old width interval 30.5-31.0',      u'30.5\u201331.0%', ms),
    (u'old width interval ascii hyphen',   u'30.5-31.0%', ms),
    (u'old 0.999 compensation ratio',      u'factor 0.999', ms),
    (u'old untraceable numerical floor',   u"estimator's own numerical floor", ms),
    (u'old cross-domain W1 clause',        u'0.5457 mm for the square-and-low-pass', ms),
    (u'old W2 width 1.5229',               u'1.5229', ms),
    (u'old DT-style windowing',            u'CT-style windowing', ms),
    (u'old aberration series alone',       u'1 / 2 rad.', ms),
    (u'old vague +0.581',                  u'+0.581 at 0 dB', ms),
    (u'old N_rep spread 0.763',            u'0.763 in', ms),
    (u'old DR precision 9.64/7.06/4.61',   u'+9.64', ms),
    (u'old per-dataset DR rounding',       u'W1 +9.6, W2 +7.1, W3 +16.0', ms),
    (u'old stale xref Table 9 in 2.7',     u'experiment **E1** (Table 9)', ms),
    (u'old unscoped 13 tested scenarios',  u'all 13 tested scenarios', ms),
    (u'old unscoped 13 scenarios 4.2',     u'over 13 scenarios (6 replicates', ms),
    (u'old conclusion target',             u'\u2264150 words', ms),
    (u'old bare 0.50x in non-claim list',  u'computation (0.50\u00d7 of the coherent arm, a saving', ms),
    (u'old Fig3(f) caption cross-domain',  u'width of $I_E$ and the \u22123 dB width of $I_M$ is 30.88', ad),
    (u'old Fig5 caption without provenance', u'15-scenario "\n                  "cross-grid sweep, positive in every scenario (trend mean +0.247, grids mixed); "', ad),
    (u'TableS5 S-prefix residue',          u'S2.7', s5),
    (u'TableS5 S4.2 residue',              u'S4.2', s5),
    (u'TableS5 S2.1 residue',              u'S2.1', s5),
    (u'TableS5 S2.2 residue',              u'S2.2', s5),
    (u'TableS5 S2.3 residue',              u'S2.3', s5),
    (u'broken sentence 0.3% This',         u'0.3% This is', ms),
    (u'Table1 ASCII I_M = sum_m',          u'I_M = sum_m', ms),
    (u'Table1 ASCII g_m |z_m|',            u'g_m |z_m|', ms),
]

# ---------------- positive controls: each MUST be present ----------------
sqrtI = u'amplitude-domain width $\\\\mathrm{FWHM}(\\\\sqrt{I_E})$ and that of $I_M$ is 30.9 % "'
CTRL = [
    (u'width 30.9%',                       u'30.9%', ms, 5),
    (u'compensation ratio 1.0066',          u'1.0066', ms, 1),
    (u'archived self-check 0.36-0.86',      u'0.36\u20130.86', ms, 1),
    (u'13/13 scoped phrase',                u'computational scenarios of the specified', ms, 3),
    (u'4/4 directional qualifier',          u'directional count', ms, 4),
    (u'detection-step SNR 6-8 dB',          u'6\u20138 dB', ms, 4),
    (u'two independent aberration series',  u'+0.0922 / +0.1470 / +0.2443', ms, 1),
    (u'W2 same-table 1.5227',               u'1.5254 against 1.5227 mm, both read from the same archived dataset table', ms, 1),
    (u'Fig3(f) amplitude-domain FWHM',      sqrtI, ad, 1),
    (u'Fig5 provenance disclosure',         u'carried literals from an exploratory run whose per-row seed file was not archived', ad, 1),
    (u'TableS5 section signs',              SEC + u'2.7', s5, 4),
    (u'TableS5 still says Table S5 nowhere', u'Table S5', s5, 0),
    (u'quantile-adaptive in abstract',      u'quantile-adaptive display windowing', ms, 1),
    (u'DR per-dataset registry precision',  u'W1 +9.65, W2 +7.05, W3 +15.97', ms, 1),
    (u'0.50x LP qualifier in non-claim',    u'0.50\u00d7 of the coherent arm for the instrumented square-and-low-pass realization', ms, 1),
    (u'N_rep spread 0.767',                u'0.767 in', ms, 1),
    (u'+0.5812 precision',                 u'+0.5812 at 0 dB', ms, 1),
]

fails = []
print(u'=== 残留探针（应全为 0）===')
nres = 0
for tag, pat, hay in RESID:
    c = hay.count(pat)
    nres += c
    print(u'  %-40s %d' % (tag, c))
    if c:
        fails.append(u'RESIDUAL ' + tag)
print(u'  残留总数 = %d' % nres)

print(u'\n=== 阳性对照（min 列为下限）===')
for tag, pat, hay, minimum in CTRL:
    c = hay.count(pat)
    ok = c >= minimum
    print(u'  %-40s %d (min %d) %s' % (tag, c, minimum, u'OK' if ok else u'MISS'))
    if not ok:
        fails.append(u'CONTROL-MISS ' + tag)

# ---------------- dollar pairing, counted per line, body only ----------------
body = ms[ms.index('## Title'):]
odd = 0
for l in body.split('\n'):
    n = len(l) - len(l.replace('$', '')) - 2 * l.count('$$')
    if n % 2:
        odd += 1
print(u'\n=== $ 配对（逐行，区间自 ## Title 起）===')
print(u'  奇数行 = %d' % odd)
if odd:
    fails.append(u'DOLLAR-ODD %d' % odd)

# ---------------- Highlights <= 85 chars ----------------)
print(u'\n=== Highlights 长度（上限 85）===')
hl = ms[ms.index('**Highlights**'):ms.index('**Keywords**')]
for l in hl.split('\n'):
    t = l.strip().lstrip('- ').strip()
    if not t or t.startswith('**'):
        continue
    n = len(t)
    print(u'  %3d  %s' % (n, t[:60]))
    if n > 85:
        fails.append(u'HIGHLIGHT %d chars: %s' % (n, t[:40]))

print(u'\n=== VERDICT: %s ===' % (u'FAIL' if fails else u'PASS'))
for f in fails:
    print(u'  ' + f)
sys.exit(1 if fails else 0)
