# -*- coding: utf-8 -*-
"""v0.30 audit-4 probe. Also audits the FINAL DOCX, not just the master,
because the master legitimately carries a status header that never ships."""
import io, re, sys, zipfile

MS = 'paper/manuscript/00_manuscript_EN.md'
AD = 'paper/manuscript/_assemble_draft.py'
T6 = 'paper/tables/Table06_cost_and_concentration.csv'
DX = 'paper/manuscript/02_PAI_manuscript_v0.30_draft.docx'

ms = io.open(MS, encoding='utf-8').read()
ad = io.open(AD, encoding='utf-8').read()
t6 = io.open(T6, encoding='utf-8').read()
body = ms[ms.index('## Title'):]

z = zipfile.ZipFile(DX)
dx = re.sub(r'<[^>]+>', '', z.read('word/document.xml').decode('utf-8'))

SEC = u'\u00a7'
fails = []

RESID = [
    (u'PATATO width claim 0.4%',        u'0.4% apart', body),
    (u'PATATO width claim (alt form)',  u'share their transverse width', body),
    (u'px residual 0.012-0.032',        u'0.032 px', body),
    (u'px residual 0.01',               u'0.01 px', body),
    (u'W5 wrong peak 0.19 MHz',         u'0.19 MHz', body),
    (u'W5 invented centre 0.70 MHz',    u'0.70 MHz', body),
    (u'W5 invented 0.35x2',             u'0.35\\times2', body),
    (u'amplitude ratio upper 0.5000',   u'0.4954\u20130.5000', body),
    (u'unarchived grid offset',         u'0.02\u20130.20', body),
    (u'peak count 4594.8',              u'4594.8', body),
    (u'N_rep old attribution 0.215',    u'gCNR$_C$ = 0.215 in', body),
    (u'N_rep old spread 0.55 only',     u'another \u2014 a spread of 0.55', body),
    (u'Table06 old DR precision',       u'+9.64', t6),
    (u'Table06 old E/C ratio',          u'0.5028', t6),
    (u'refs.bib path',                  u'refs.bib', body),
    (u'energy-density hyphen',          u'energy-density image', body),
    (u'energy related unhyphenated',    u'are energy related', body),
    (u'old Fig3(f) cross-domain',       u'width of $I_E$ and the \u22123 dB width', ad),
    (u'old TableS5 S-prefix',           u'S2.7', io.open('paper/tables/TableS5_validation_roadmap.csv', encoding='utf-8').read()),
    (u'old 30.5-31.0',                  u'30.5\u201331.0%', body),
    (u'old 0.999 compensation',         u'factor 0.999', body),
    (u'old 1.5229',                     u'1.5229', body),
    (u'old CT-style',                   u'CT-style windowing', body),
    (u'old 1 rad-only aberration',      u'1 / 2 rad.', body),
    (u'old +0.581',                     u'+0.581 at 0 dB', body),
    (u'old 0.763',                      u'0.763 in', body),
    (u'old conclusion 150 words',       u'\u2264150 words', body),
    (u'old unscoped 13 tested',         u'all 13 tested scenarios', body),
]

CTRL = [
    (u'N_rep policy restated',      u'0.7674 \u00b1 0.0507', body, 1),
    (u'N_rep clutter figure kept',   u'0.215 at maximum clutter', body, 1),
    (u'archived width checks',       u'w_{-3\\,\\mathrm{dB}}=7.8', body, 1),
    (u'W5 three frequencies',       u'raw unfiltered spectral peak**, $0.188$ MHz', body, 1),
    (u'amplitude ratio 0.5005',      u'0.4954\u20130.5005', body, 1),
    (u'15-scenario provenance',      u'carried literals from an exploratory run', body, 1),
    (u'Table 11 row1 scoping',       u'computational scenarios of the specified model, gauge-invariant', body, 1),
    (u'Table 11 row2 scoping',       u'directional count, n=4, no interval or $p$ value), while the one-dimensional', body, 1),
    (u'detection step restated',     u'0.0440 + 0.0289 = 0.0729', body, 1),
    (u'Table06 DR precision',        u'+9.65, +7.05, +15.97, +4.63', t6, 1),
    (u'Table06 E/C ratio',           u'1.0000,0.5106,0.5041', t6, 1),
    (u'energy-related hyphen',       u'**Why squared envelopes are energy-related.**', body, 1),
    (u'energy density plain',        u'as an energy density image presumes', body, 1),
    (u'BibTeX phrasing',             u'accompanying BibTeX file', body, 1),
]

print(u'=== 残留（应全 0）===')
n = 0
for tag, pat, hay in RESID:
    c = hay.count(pat); n += c
    print(u'  %-34s %d' % (tag, c))
    if c: fails.append(u'RESIDUAL ' + tag)
print(u'  total = %d' % n)

print(u'\n=== 阳性对照 ===')
for tag, pat, hay, lo in CTRL:
    c = hay.count(pat)
    print(u'  %-34s %d (min %d) %s' % (tag, c, lo, u'OK' if c >= lo else u'MISS'))
    if c < lo: fails.append(u'CONTROL-MISS ' + tag)

print(u'\n=== 交付 DOCX（真正交付件）===')
leak = sorted(set(re.findall(r'(?:docs|notes|pipeline|results|data_ext|oadat_data)/[A-Za-z0-9_\-/\.]+', dx)))
cjk = len(re.findall(r'[\u4e00-\u9fff]', dx))
oi = 'Open items' in dx
print(u'  path leaks = %d %s' % (len(leak), leak if leak else u''))
print(u'  CJK chars  = %d' % cjk)
print(u'  Open items present = %s' % oi)
print(u'  refs.bib = %s' % ('refs.bib' in dx))
for cond, tag in ((leak, u'DOCX-LEAK'), (cjk, u'DOCX-CJK'), (oi, u'DOCX-OPENITEMS'),
                  ('refs.bib' in dx, u'DOCX-REFSBIB')):
    if cond: fails.append(tag)

print(u'\n=== $ 配对（逐行，母本交付区间）===')
odd = sum(1 for l in body.split('\n')
          if (len(l) - len(l.replace('$', '')) - 2 * l.count('$$')) % 2)
print(u'  odd lines = %d' % odd)
if odd: fails.append(u'DOLLAR-ODD')

print(u'\n=== markdown 表列数 ===')
bad = 0
for b in re.findall(r'(?:^\|.*\$\n)+', body, re.M):
    ls = [l for l in b.strip().split('\n') if l.strip()]
    cols = [len(l.split('|')) - 2 for l in ls]
    if len(set(cols)) > 1:
        bad += 1; print(u'  MISMATCH %s' % cols)
print(u'  mismatched blocks = %d' % bad)
if bad: fails.append(u'TABLE-COLS %d' % bad)

print(u'\n=== Highlights <= 85 ===')
hl = body[body.index('**Highlights**'):body.index('**Keywords**')]
for l in hl.split('\n'):
    t = l.strip().lstrip('- ').strip()
    if not t or t.startswith('**'): continue
    L = len(t); print(u'  %3d  %s' % (L, t[:58]))
    if L > 85: fails.append(u'HIGHLIGHT %d' % L)

print(u'\n=== VERDICT: %s ===' % (u'FAIL' if fails else u'PASS'))
for f in fails: print(u'  ' + f)
sys.exit(1 if fails else 0)
