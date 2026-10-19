# -*- coding: utf-8 -*-
"""v0.30 audit-4 dispositions. Idempotent per edit; MISS does not abort.

Every item below was independently re-verified against the archives before being
accepted; the two agent-1 P0 items were confirmed from results/_regime.log,
results/_adv2.log and results/study_patato/patato_check.mat. The agent-2 P0
(Open-items path leak) was REJECTED: _assemble_draft.py:540 strips that whole
section and the assembled draft has 0 hits.
"""
import io, sys

MS = 'paper/manuscript/00_manuscript_EN.md'
AD = 'paper/manuscript/_assemble_draft.py'
T6 = 'paper/tables/Table06_cost_and_concentration.csv'

DONE, MISS = [], []

def edit(path, old, new, tag):
    s = io.open(path, encoding='utf-8').read()
    n = s.count(old)
    if n == 0:
        MISS.append(tag); return
    if old == new:
        DONE.append(tag + ' (already applied)'); return
    io.open(path, 'w', encoding='utf-8').write(s.replace(old, new))
    DONE.append('%s (%d)' % (tag, n))

# ===== P0-1  N_rep policy: 0.215 / 0.767 were mis-attributed =====
# _regime.log  gives gCNR C = 0.2150 at sp=0.00 cr=5.0 (a CLUTTER setting, not sigma_phi=4)
# _regime.log  gives gCNR C = 0.6367 at sp=4.00 cr=0.0 (the sigma_phi=4 setting)
# _adv2.log    gives 0.7674 +/- 0.0507 as a SIX-REPLICATE mean at sigma_phi=4, not one draw
edit(MS,
     u'> random realisation of the $\\sigma_\\phi=4$ rad screen gave gCNR$_C$ = 0.215 in\n'
     u'> another \u2014 a spread of 0.55.',
     u'> run of the $\\sigma_\\phi=4$ rad screen gave gCNR$_C$ = 0.637,\n'
     u'> while a six-replicate ramp study at the same setting gives 0.7674 \u00b1 0.0507 \u2014 a spread of\n'
     u'> 0.13 within one setting, and 0.55 if the clutter axis is mixed in (0.215 at maximum clutter).',
     'P0-1 N_rep policy attribution')
edit(MS,
     u'> random realisation of the $\\sigma_\\phi=4$ rad screen gave gCNR$_C$ = 0.215 in one script and 0.767 in',
     u'> run of the $\\sigma_\\phi=4$ rad screen gave gCNR$_C$ = 0.637 in the regime sweep and 0.7674 \u00b1 0.0507 in',
     'P0-1 N_rep policy first half')

# ===== P0-2  PATATO width claim has no archive behind it =====
edit(MS,
     u'there $I_E$ and $I_M^2$ share their transverse width (0.4% apart), so the broadening belongs to $L_2$ aggregation, not the compensation.',
     u'',
     'P0-2 PATATO 0.4% width claim removed')

# ===== P1-3  0.012-0.032 px / 0.01 px residuals have no archive =====
edit(MS,
     u'The apparent-width identity of §2.5 reproduces the measured change in full-width-at-half-maximum \u2014\n'
     u'Gaussian \u221229.3%, with a residual of **0.012\u20130.032 px** over four groups \u2014 and holds on a two-peak profile\n'
     u'to **0.01 px** (W2).',
     u'The apparent-width identity of §2.5 predicts the \u221229.3% Gaussian change in full-width-at-half-maximum\n'
     u'analytically; the archived single-point widths test the identity where they can, and give\n'
     u'$|\\mathrm{FWHM}(I_E)-w_{-3\\,\\mathrm{dB}}|/w_{-3\\,\\mathrm{dB}}=7.8\\,\\%$ and\n'
     u'$|\\mathrm{FWHM}(\\sqrt{I_E})-\\mathrm{FWHM}(I_M)|/\\mathrm{FWHM}(I_M)=30.9\\,\\%$.',
     'P1-3 px residuals replaced by the archived width checks')

# ===== P1-4  W5 band-centre numbers =====
# Table S1 decision_basis: "unfiltered peak sits at 0.188 MHz"; f0_meas_MHz = 1.25
edit(MS,
     u'the **measured band centre** of the raw record, $0.35\\times2=0.70$ MHz for W5\u2019s half-power band (the 0.35 MHz quoted for W5 is the *verified analysis centre* $f_0$ that was actually used for imaging, not a second estimate of the band centre); and the **Q8 effective centre** $1.25$ MHz, obtained by the audit estimator from the raw spectrum.',
     u'the **raw unfiltered spectral peak**, $0.188$ MHz for W5; the **verified analysis centre** $f_0=0.35$ MHz that was actually used for imaging (not a second estimate of the band centre); and the **Q8 effective centre** $1.25$ MHz, obtained by the audit estimator from the raw spectrum (Table S1).',
     'P1-4 W5 three frequencies restated from Table S1')
edit(MS,
     u'W5 is low-frequency-dominant and broadband (raw spectral peak 0.19 MHz, energy spread beyond 5 MHz)',
     u'W5 is low-frequency-dominant and broadband (raw spectral peak 0.188 MHz)',
     'P1-4 W5 raw peak 0.19 -> 0.188')

# ===== P1-5  amplitude ratio upper bound =====
edit(MS, u'amplitude ratio 0.4954\u20130.5000', u'amplitude ratio 0.4954\u20130.5005',
     'P1-5 amplitude ratio upper bound')

# ===== P1-6  grid side-lobe offset has no archived grid experiment =====
edit(MS,
     u'only trends, because a finer grid resolves more coherent side-lobe (0.02\u20130.20\n'
     u'systematic offset on $C$).',
     u'only trends, because the two grids resolve the coherent side-lobe structure differently.',
     'P1-6 unarchived grid offset removed')

# ===== P1-7  Table 8 / Table 10 separator rows short one column =====
edit(MS,
     u'| route | chain (as coded) | Hilbert | low-pass | what the interpolation acts on |\n'
     u'|---|---|---|---|',
     u'| route | chain (as coded) | Hilbert | low-pass | what the interpolation acts on |\n'
     u'|---|---|---|---|---|',
     'P1-7 Table 8 separator column count')
edit(MS,
     u'| arm | detection / pre-processing | Hilbert | back-projection | end-to-end |\n'
     u'|---|---|---|---|',
     u'| arm | detection / pre-processing | Hilbert | back-projection | end-to-end |\n'
     u'|---|---|---|---|---|',
     'P1-7 Table 10 separator column count')

# ===== P1-8  Highlights keep the scoping inside 85 chars =====
edit(MS,
     u'- Higher gCNR than coherent back-projection in 13/13 tested scenarios (+0.1742).',
     u'- gCNR above coherent back-projection: 13/13 specified-model scenarios.',
     'P1-8 Highlight 3 scoping restored')

# ===== P1-9  Table 11 scoping =====
edit(MS,
     u'| $E$ over $C$ | replicated paired scenarios, gauge-invariant metric (13/13, +0.1742) |',
     u'| $E$ over $C$ | replicated paired computational scenarios of the specified model, gauge-invariant metric (13/13, +0.1742) |',
     'P1-9 Table 11 row 1 scoping')
edit(MS,
     u'(4/4 testable, §4.2), while the one-dimensional profile control',
     u'(4/4 testable, §4.2; directional count, n=4, no interval or $p$ value), while the one-dimensional profile control',
     'P1-9 Table 11 row 2 scoping')

# ===== P2-10  per-dataset peak counts =====
edit(MS, u'$M$ 896.8 \u2192 336.3, $E$ 4594.8 \u2192 1722.8 (\u00d710\u00b3)',
     u'$M$ 896.8 \u2192 336.3, $E$ 4594.1 \u2192 1722.8 (\u00d710\u00b3)',
     'P2-10 4594.8 -> 4594.1')

# ===== P2-11  detection-step cost: 0.044+0.029 = 0.073, not "slightly more" =====
edit(MS,
     u'the square-and-low-pass detection step (0.073 s) costs slightly more than envelope detection plus\n'
     u'Hilbert (0.072 s).',
     u'the square-and-low-pass detection step (0.0734 s) and envelope detection plus Hilbert\n'
     u'(0.0440 + 0.0289 = 0.0729 s) are the same size to within 0.0005 s.',
     'P2-11 detection-step cost restated')

# ===== P2-12  15-scenario sweep: declare the 7 unarchived rows =====
edit(MS,
     u'Across a broad 15-scenario sweep (four perturbation axes; **Figure 5**) the energy-related estimator attains a gCNR no lower than $C$ in **every** scenario',
     u'Across a broad 15-scenario sweep (four perturbation axes; **Figure 5**) the energy-related estimator attains a gCNR no lower than $C$ in **every** scenario (7 of the 15 rows are carried literals from an exploratory run that was not archived, and are claimed as trend only)',
     'P2-12 15-scenario provenance declared in text')

# ===== P2-13  Table 06 CSV: registry precision and the E/C ratio =====
edit(T6, u'(per dataset: +9.64, +7.06, +15.97, +4.61, +3.23, +2.41)',
     u'(per dataset: +9.65, +7.05, +15.97, +4.63, +3.23, +2.41)',
     'P2-13 Table 06 per-dataset DR precision')
edit(T6, u'1.0000,0.5106,0.5028,ratio,', u'1.0000,0.5106,0.5041,ratio,',
     'P2-13 Table 06 E/C ratio 0.5028 -> 0.5041')

# ===== P2-14  terminology consistency =====
edit(MS, u'**Why squared envelopes are energy related.**', u'**Why squared envelopes are energy related.**'.replace('energy related', 'energy-related'),
     'P2-14 energy-related hyphenated')
edit(MS,
     u'The *quantitative* reading of $I_E$ as an energy-density image presumes',
     u'The *quantitative* reading of $I_E$ as an energy density image presumes',
     'P2-14 energy density unhyphenated')
edit(MS,
     u'within the energy domain $I_E$ and $M^2$ agree to 0.3%.',
     u'within the energy domain $I_E$ and $I_M^2$ agree to 0.3%.',
     'P2-14 M^2 -> I_M^2 in 5.2')

# ===== P2-15  References: no repository-internal path =====
edit(MS,
     u'Entries are reproduced from `paper/refs/refs.bib`, which remains the single source of truth;',
     u'Entries are reproduced from the accompanying BibTeX file, which remains the single source of truth;',
     'P2-15 refs.bib path removed from References')

print('=== APPLIED ===')
for d in DONE: print('  OK  ', d)
print('=== MISS ===')
for m in MISS: print('  MISS', m)
print('applied=%d miss=%d' % (len(DONE), len(MISS)))
sys.exit(0)
