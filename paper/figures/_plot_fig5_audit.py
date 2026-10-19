# -*- coding: utf-8 -*-
"""Figure 5 — per-scenario E-C separability margin from the replicated paired audit.

Re-plotted for v0.32 (review round 9, item 8a): the previous figure drew a broad
15-scenario cross-grid sweep of which 7 rows were carried literals from an
exploratory run whose per-row seeds were not archived.  Those 7 rows are removed;
the figure now shows the 13 computational scenarios of the replicated paired
audit, every bar recomputed from the released audit table, so the figure carries
no un-archived row.

Input : results/study_audit/study_audit.csv  (axis=1 rows, delta_gCNR_E_minus_C)
Output: paper/figures/Fig05_paired_audit.png

The script asserts, before writing, that the 13 bars are all positive and that
their mean is +0.1742 (the manuscript's §4.2 figure), so any drift in the archive
or in the text fails loudly.
"""
import csv
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..')).replace(os.sep, '/')

CSV = os.path.join(ROOT, 'results', 'study_audit', 'study_audit.csv')
OUT = os.path.join(ROOT, 'paper', 'figures', 'Fig05_paired_audit.png')

plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 9.0

# perturbation family per scenario (label prefix -> family + colour)
FAMILY = [
    ('semicircle128/noise', 'Ideal (white noise)', '#7fa8d8'),
    ('ring256/noise', 'Ideal (white noise)', '#7fa8d8'),
    ('semicircle128/clutter', 'Coherent clutter', '#e8a05a'),
    ('ring256/clutter', 'Coherent clutter', '#e8a05a'),
    ('aberr', 'Aberration', '#c9a0dc'),
    ('SNR=', 'Low SNR', '#e8837a'),
    ('random loss', 'Element loss', '#f0d060'),
]
FAMILY_COL = {f[0]: f[2] for f in FAMILY}


def family_of(cond):
    for prefix, name, col in FAMILY:
        if cond.startswith(prefix):
            return name, col
    return 'other', '#999999'


def read_audit():
    rows = []
    with open(CSV, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            if r['axis'] != '1' or r['quantity'] != 'delta_gCNR_E_minus_C':
                continue
            rows.append((r['condition'], float(r['value'])))
    return rows


def main():
    rows = read_audit()
    assert len(rows) == 13, 'expected 13 paired-audit scenarios, got %d' % len(rows)
    vals = [v for _, v in rows]
    mean = sum(vals) / len(vals)
    # --- consistency assertions against §4.2 ---
    assert all(v > 0 for v in vals), 'all 13 margins must be positive'
    assert abs(mean - 0.1742) < 5e-4, 'mean must be +0.1742 (got %.4f)' % mean

    order = sorted(range(len(vals)), key=lambda i: vals[i])  # ascending
    labels = [rows[i][0] for i in order]
    values = [vals[i] for i in order]
    colors = [family_of(rows[i][0])[1] for i in order]
    ypos = list(range(len(values)))

    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    ax.barh(ypos, values, color=colors, edgecolor='0.25', linewidth=0.6, height=0.72)
    for y, v in zip(ypos, values):
        ax.text(v + 0.008, y, '%+.3f' % v, va='center', ha='left', fontsize=8.2)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=8.4)
    ax.set_xlim(0, 0.66)
    ax.set_xlabel(r'$\Delta$gCNR  (Arm E $-$ Arm C; paired over 6 replicates)',
                  fontsize=9.2)
    ax.axvline(mean, color='0.35', ls='--', lw=1.0, zorder=0)
    ax.text(mean + 0.004, len(values) - 0.35, 'mean %+.3f' % mean, color='0.30',
            fontsize=8.2, va='center')
    ax.grid(axis='x', color='0.9', lw=0.6)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)

    uniq = {}
    for _, name, col in FAMILY:
        uniq.setdefault(name, col)
    handles = [Patch(facecolor=c, edgecolor='0.25', label=n) for n, c in uniq.items()]
    ax.legend(handles=handles, title='perturbation family', loc='lower right',
              fontsize=7.6, title_fontsize=7.8, framealpha=0.95)

    fig.suptitle('Separability margin over coherent back-projection, 13/13 '
                 'paired-audit scenarios\n(mean $\\Delta$gCNR = %+.3f; every bar '
                 'recomputed from the released audit table)' % mean,
                 fontsize=10.2, y=0.975)
    fig.tight_layout(rect=(0, 0, 1, 0.915))
    fig.savefig(OUT, dpi=220, bbox_inches='tight', facecolor='white')
    print('saved:', OUT)
    print('n = %d  mean = %+.4f  min = %+.4f  max = %+.4f'
          % (len(values), mean, min(values), max(values)))


if __name__ == '__main__':
    main()
