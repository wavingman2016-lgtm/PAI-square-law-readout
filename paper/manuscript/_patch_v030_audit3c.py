# -*- coding: utf-8 -*-
"""v0.30 audit-3 remaining items. Idempotent: each edit independent, MISS does not abort."""
import io, sys

MS = 'paper/manuscript/00_manuscript_EN.md'
AD = 'paper/manuscript/_assemble_draft.py'
S5 = 'paper/tables/TableS5_validation_roadmap.csv'

DONE, MISS = [], []

def edit(path, old, new, tag):
    s = io.open(path, encoding='utf-8').read()
    n = s.count(old)
    if n == 0:
        MISS.append(tag); return
    if old == new:
        DONE.append(tag + ' (noop, already applied)'); return
    s = s.replace(old, new)
    io.open(path, 'w', encoding='utf-8').write(s)
    DONE.append('%s (%d site(s))' % (tag, n))

# ---------- P0-2  Fig. 3(f) caption: cross-domain width comparison ----------
edit(AD,
     '"\u22123 dB width of $I_E$ and the \u22123 dB width of $I_M$ is 30.88 %, which is what a "\n'
     '                  "reading-level difference produces. Widths are measured on Nx = 801; gCNR on "',
     '"amplitude-domain width $\\\\mathrm{FWHM}(\\\\sqrt{I_E})$ and that of $I_M$ is 30.9 % "\n'
     '                  "(0.9625 against 0.7354 mm), which is what a reading-level difference produces. "\n'
     '                  "Widths are measured on Nx = 801; gCNR on "',
     'P0-2 Fig3(f) caption cross-domain')

# ---------- P0-3  Table S5 CSV: section signs restored ----------
_s5 = io.open(S5, encoding='utf-8').read()
for a, b in (('S2.7', '\u00a72.7'), ('S2.1', '\u00a72.1'), ('S2.2', '\u00a72.2'),
             ('S2.3', '\u00a72.3'), ('S4.2', '\u00a74.2')):
    if a in _s5:
        c = _s5.count(a)
        _s5 = _s5.replace(a, b)
        DONE.append('P0-3 TableS5 %s -> %s (%d)' % (a, b, c))
    else:
        MISS.append('P0-3 TableS5 %s' % a)
io.open(S5, 'w', encoding='utf-8').write(_s5)

# ---------- P0-4  W2 width 1.5229 -> 1.5227 (same archived dataset table) ----------
edit(MS,
     '(0.3% apart; W2: 1.5254 against 1.5229 mm)',
     '(0.3% apart; W2: 1.5254 against 1.5227 mm, both read from the same archived dataset table)',
     'P0-4 W2 1.5229 -> 1.5227')

# ---------- P0-5  broken sentence in 5.2 ----------
edit(MS,
     'within the energy domain $I_E$ and $M^2$ agree to 0.3% This is **not** an artefact of the compensation:',
     'within the energy domain $I_E$ and $M^2$ agree to 0.3%.\nThis is **not** an artefact of the compensation:',
     'P0-5 broken sentence in 5.2')

# ---------- P0-6  two aberration series declared as two independent runs ----------
edit(MS,
     'the aberration series gives +0.0978 / +0.1200 / +0.1810 at 0.5 / 1 / 2 rad.',
     'the aberration series gives +0.0978 / +0.1200 / +0.1810 at 0.5 / 1 / 2 rad (the separate '
     'phase-screen sweep of Fig. 4a, run on its own seed axis, gives +0.0922 / +0.1470 / +0.2443 '
     'on the same three settings; the two series are independent runs and are not combined).',
     'P0-6 two aberration series declared')

# ---------- P1-6  13/13 scoping in 4.2 ----------
edit(MS,
     'In a replicated run over 13 scenarios (6 replicates each,',
     'In a replicated run over the 13 computational scenarios of the specified model (6 replicates each,',
     'P1-6 4.2 scoping of 13 scenarios')

# ---------- P1-7  5.2 "4 of the 4" needs the directional-count qualifier ----------
edit(MS,
     'in **4 of the 4** testable datasets ($\\Delta\\mathrm{gCNR}=-0.0385\\ldots-0.0009$; W1 and W6 saturate and are recorded NA)',
     'in **4 of the 4** testable datasets ($\\Delta\\mathrm{gCNR}=-0.0385\\ldots-0.0009$; a directional '
     'count, $n=4$, with no interval or $p$ value; W1 and W6 saturate and are recorded NA)',
     'P1-7 5.2 4-of-4 qualifier')

# ---------- P1-8  Highlights within 85 characters ----------
edit(MS,
     '- The estimator admits a Hilbert-free realization, $\\mathrm{LPF}\\{x^2\\}=\\lvert z\\rvert^2/2$.',
     '- Hilbert-free: $\\mathrm{LPF}\\{x^2\\}=\\lvert z\\rvert^2/2$.',
     'P1-8 Highlight 2 compress')
edit(MS,
     '- Higher gCNR than coherent back-projection in all 13 tested computational scenarios of the specified model (+0.1742).',
     '- Higher gCNR than coherent back-projection in 13/13 tested scenarios (+0.1742).',
     'P1-8 Highlight 3 compress')
edit(MS,
     '- Against squared envelope stacking, no advantage on a 2-D ROI (4/4 testable datasets; a directional count, n=4, no interval or $p$ value).',
     '- No advantage on squared envelope stacking: 2-D ROI, 4/4 testable, directional only.',
     'P1-8 Highlight 4 compress')
edit(MS,
     '- Trade vs envelope stacking: 30.9% broader spread, 6\u20138 dB SNR, earlier clutter failure.',
     '- Priced: 30.9% broader spread, 6\u20138 dB SNR, earlier clutter failure.',
     'P1-8 Highlight 5 compress')

# ---------- P1-9  4.4 citation placement ----------
edit(MS,
     'so the Hilbert-free precondition holds; what fails on this dataset is not $\\beta$ but the $E$-versus-$M$ ordering) [17,18] the\nchannel-wise estimator',
     'so the Hilbert-free precondition holds; what fails on this dataset is not $\\beta$ but the $E$-versus-$M$ ordering) [17,18],\nthe channel-wise estimator',
     'P1-9 4.4 citation comma')

# ---------- P1-10  per-dataset DR values at registry precision ----------
edit(MS,
     'difference **+2.41 \u2026 +15.97 dB** (registry `DR_gain_dB`; W1 +9.6, W2 +7.1, W3 +16.0 dB)',
     'difference **+2.41 \u2026 +15.97 dB** (registry `DR_gain_dB`; W1 +9.65, W2 +7.05, W3 +15.97 dB)',
     'P1-10 per-dataset DR precision')

# ---------- P1-11  5.7 non-claim list: 0.50x needs the LP qualifier ----------
edit(MS,
     'and in computation (0.50\u00d7 of the coherent arm, a saving shared by the whole envelope-domain family',
     'and in computation (0.50\u00d7 of the coherent arm for the instrumented square-and-low-pass realization, '
     'not transferred to the production EI route; a saving shared by the whole envelope-domain family',
     'P1-11 5.7 0.50x LP qualifier')

# ---------- P1-12  Fig. 5 caption discloses the provenance of its 15 rows ----------
edit(AD,
     '"Core evidence: per-scenario $\\\\Delta$gCNR (E\u2212C) from the broad 15-scenario "\n'
     '                  "cross-grid sweep, positive in every scenario (trend mean +0.247, grids mixed); "',
     '"Core evidence: per-scenario $\\\\Delta$gCNR (E\u2212C) from the broad 15-scenario "\n'
     '                  "cross-grid sweep, positive in every scenario (trend mean +0.247, grids mixed); of "\n'
     '                  "those 15 rows, 8 are recomputed from the archived phase-screen seeds and 7 are "\n'
     '                  "carried literals from an exploratory run whose per-row seed file was not archived, so "\n'
     '                  "the sweep is reported as a trend across grids and not as 15 independent draws; "',
     'P1-12 Fig5 caption provenance')

# ---------- P2-13  abstract: CT-style windowing has no payoff point in the text ----------
edit(MS,
     'a reproducible display protocol (CT-style windowing, data-domain metrics).',
     'a reproducible display protocol (quantile-adaptive display windowing, data-domain metrics).',
     'P2-13 abstract CT-style -> quantile-adaptive')

# ---------- P2-14  5.2 SNR margin at the same precision as 4.2 ----------
edit(MS, 'low SNR up to +0.581 at 0 dB', 'low SNR up to +0.5812 at 0 dB',
     'P2-14 5.2 +0.581 -> +0.5812')

# ---------- P2-15  N_rep policy spread matches Table 5 ----------
edit(MS,
     'gave gCNR$_C$ = 0.215 in one script and 0.763 in\n> another',
     'gave gCNR$_C$ = 0.215 in one script and 0.767 in\n> another',
     'P2-15 0.763 -> 0.767 (Table 5)')

# ---------- P2-17  Conclusion heading: length target vs actual ----------
edit(MS, '## 6. Conclusion  *(target \u22484%, \u2264150 words)*',
     '## 6. Conclusion  *(target \u22484%; the delivered section is longer, and is not cut to that target here)*',
     'P2-17 conclusion target note')

# ---------- P2-16  Table 1 ASCII residue (probe, expect zero) ----------
_s = io.open(MS, encoding='utf-8').read()
_bad = [t for t in ('I_M = sum_m', 'g_m |z_m|', 'g_m \\|z_m\\|') if t in _s]
if _bad:
    MISS.append('P2-16 ASCII residue still present: %r' % _bad)
else:
    DONE.append('P2-16 Table 1 ASCII residue: already clean (0 hit)')

print('=== APPLIED ===')
for d in DONE:
    print('  OK  ', d)
print('=== MISS ===')
for m in MISS:
    print('  MISS', m)
print('applied=%d miss=%d' % (len(DONE), len(MISS)))
sys.exit(0)
