# -*- coding: utf-8 -*-
"""
Figure 5 — per-scenario separability margin of the energy-related estimator.

15 controlled scenarios, horizontal bar chart of  Delta gCNR (Arm E - Arm C),
sorted by magnitude and coloured by the perturbation family.

数据来源（可核验部分）
  · SNR axis (5 points) and aberration axis (3 points) are **computed here**
    from results/study_phase/study_phase.mat  (SB/gC,SB/gE and SA/gC,SA/gE).
  · The remaining 7 points (2 coherent-clutter, 2 white-noise simulations,
    1 element-loss, 2 in-house wire acquisitions) were produced by the
    original exploratory script, which was **not archived**.  They are carried
    here as literals equal to the values already reported in the manuscript
    (Sect. 4.2: 15/15 positive, mean +0.247, range +0.047 ... +0.582) so that
    figure and text stay consistent.  The script asserts both the mean and the
    sign of every entry, so any future edit that breaks the agreement fails
    loudly instead of silently.

口径：本图是**跨臂**比较，纵轴量是 gCNR 差（gauge-invariant, F4），
      不是任何域内读数（宽度 / DR / PSR）。
"""
import os
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..')).replace(os.sep, '/')

PHASE = os.path.join(ROOT, 'results', 'study_phase', 'study_phase.mat')
OUT = os.path.join(ROOT, 'paper', 'figures', 'Fig05_delta_gCNR_15of15.png')

plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 9.0

# 体制配色（与旧图一致，仅换语言）
COL = {
    'Low SNR':      '#e8837a',
    'Coherent clutter': '#e8a05a',
    'Ideal (white noise)': '#7fa8d8',
    'Aberration':   '#c9a0dc',
    'In-house data': '#7fcf9f',
    'Element loss': '#f0d060',
}


def _arr(f, p):
    return np.asarray(f[p], dtype=float).ravel()


def computed_points():
    """从归档的 study_phase.mat 复算 8 个点（SNR 5 + 畸变 3）。"""
    with h5py.File(PHASE, 'r') as f:
        snr = _arr(f, 'SB/snr'); gC = _arr(f, 'SB/gC'); gE = _arr(f, 'SB/gE')
        sig = _arr(f, 'SA/sig'); sC = _arr(f, 'SA/gC'); sE = _arr(f, 'SA/gE')
    d_snr = dict(zip(snr.tolist(), (gE - gC).tolist()))
    d_sig = dict(zip(sig.tolist(), (sE - sC).tolist()))
    idx = {0.0: 0, 5.0: 1, 10.0: 2, 15.0: 3, 25.0: 5}
    out = {}
    for s, i in idx.items():
        out['SNR %g dB' % s] = d_snr[s]
    for s in (0.5, 1.0, 2.0):
        out['aberration %g rad' % s] = d_sig[s]
    return out


def main():
    c = computed_points()

    # (label, value, family) —— 值 = 手稿 §4.2 报告值；可复算者与 c[] 交叉核对
    rows = [
        ('SNR 0 dB',                       c['SNR 0 dB'],        'Low SNR'),
        ('ring-256 / coherent clutter',    0.550,                'Coherent clutter'),
        ('SNR 5 dB',                       c['SNR 5 dB'],        'Low SNR'),
        ('semicircle-128 / coherent clutter', 0.372,             'Coherent clutter'),
        ('SNR 10 dB',                      c['SNR 10 dB'],       'Low SNR'),
        ('ring-256 / white noise',         0.279,                'Ideal (white noise)'),
        ('aberration 2 rad',               c['aberration 2 rad'], 'Aberration'),
        ('in-house W2 (two wires)',        0.195,                'In-house data'),
        ('SNR 15 dB',                      c['SNR 15 dB'],       'Low SNR'),
        ('aberration 1 rad',               c['aberration 1 rad'], 'Aberration'),
        ('element loss 50%',               0.111,                'Element loss'),
        ('aberration 0.5 rad',             c['aberration 0.5 rad'], 'Aberration'),
        ('semicircle-128 / white noise',   0.082,                'Ideal (white noise)'),
        ('in-house W1 (single wire)',      0.048,                'In-house data'),
        ('SNR 25 dB',                      c['SNR 25 dB'],       'Low SNR'),
    ]

    vals = np.array([r[1] for r in rows])
    mean = vals.mean()
    # —— 一致性断言：与手稿 §4.2 完全对齐 ——
    assert vals.size == 15, 'must be 15 scenarios'
    assert (vals > 0).all(), 'all 15 margins must be positive'
    assert abs(vals.min() - 0.047) < 5e-4, 'min must be +0.047'
    assert abs(vals.max() - 0.582) < 5e-4, 'max must be +0.582'
    assert abs(mean - 0.247) < 5e-4, 'mean must be +0.247 (got %.4f)' % mean

    order = np.argsort(vals)              # 升序 → 画横条时最长在最上
    labels = [rows[i][0] for i in order]
    values = vals[order]
    colors = [COL[rows[i][2]] for i in order]
    ypos = np.arange(len(values))

    # —— 归档：把 15 个场景（含 7 个"carried literal"）连同**出处**写成 CSV ——
    # v0.22 新增：回应"Fig. 5 十五场景中 7 点无归档"。这 7 点仍非由归档脚本算出，
    # 但它们的数值、来源标记与断言结果现在**有文件可查**，不再只存在于脚本常量里。
    _csv = os.path.join(ROOT, 'results', 'study_adv_semicircle128',
                        'Fig05_scenarios.csv')
    if os.path.isdir(os.path.dirname(_csv)):
        comp = computed_points()
        with open(_csv, 'w', encoding='utf-8') as fh:
            fh.write('scenario,dgCNR_E_minus_C,family,source\n')
            for lab, val, fam in rows:
                src = 'study_phase.mat (recomputed)' if lab in comp else 'carried literal (exploratory run, not archived)'
                fh.write('%s,%.6f,%s,%s\n' % (lab, val, fam, src))
            fh.write('SUMMARY,mean=%.6f,min=%.6f,max=%.6f,asserted against Sect. 4.2\n'
                     % (mean, vals.min(), vals.max()))

    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    bars = ax.barh(ypos, values, color=colors, edgecolor='0.25', linewidth=0.6,
                   height=0.72)
    for y, v in zip(ypos, values):
        ax.text(v + 0.008, y, '%+.3f' % v, va='center', ha='left', fontsize=8.2)

    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=8.4)
    ax.set_xlim(0, 0.66)
    ax.set_xlabel(r'$\Delta$gCNR  (Arm E $-$ Arm C; energy domain $-$ coherent '
                  r'back-projection)', fontsize=9.2)
    ax.axvline(mean, color='0.35', ls='--', lw=1.0, zorder=0)
    ax.text(mean + 0.004, len(values) - 0.35, 'mean %+.3f' % mean,
            color='0.30', fontsize=8.2, va='center')
    ax.grid(axis='x', color='0.9', lw=0.6)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)

    handles = [Patch(facecolor=COL[k], edgecolor='0.25', label=k) for k in COL]
    ax.legend(handles=handles, title='perturbation family', loc='lower right',
              fontsize=7.6, title_fontsize=7.8, framealpha=0.95)

    fig.suptitle('The energy-related estimator wins on separability in 15/15 '
                 'controlled scenarios (mean $\\Delta$gCNR = %+.3f)\n'
                 'the margin widens under perturbation, from %+.3f (ideal) to '
                 '%+.3f (%s)'
                 % (mean, vals.min(), vals.max(), rows[int(np.argmax(vals))][0]),
                 fontsize=10.2, y=0.975)
    fig.tight_layout(rect=(0, 0, 1, 0.915))
    fig.savefig(OUT, dpi=220, bbox_inches='tight', facecolor='white')
    print('saved:', OUT)
    print('mean = %+.4f  min = %+.4f  max = %+.4f' % (mean, vals.min(), vals.max()))


if __name__ == '__main__':
    main()
