# -*- coding: utf-8 -*-
"""
Figure 6 — the object ladder: six in-house acquisitions under their per-dataset
verified configurations.

Layout: 2 rows x 3 dataset groups; each group is a 1 x 4 strip of the four
pre-processing variants that Table 4 ablates
    D1   linear envelope              |z|          (envelope-stacking reference, arm M)
    D1^2 envelope squared            (|z|)^2
    D2'  squared + low-pass          (this work, Hilbert-free, arm E)
    D2   bare square                 x^2          (control, known defect)

Data: results/{wire,recheck}/<dir>/<tag>_results.mat  field IM/{env,env2,sqlaw,sq}
      per-dataset metrics from the same folder's <tag>_sheet.csv
      geometry / config / verdict from results/registry/registry.csv

口径：面板内是**同一数据集、同一域**的四个前处理变体，属域内读数；
      组标题里的 ΔCNR / ΔgCNR 是 D2' 相对 D1（= arm E 相对 arm M）。
"""
import os
import csv
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..')).replace(os.sep, '/')

OUT = os.path.join(ROOT, 'paper', 'figures', 'Fig06_own6_registry.png')
REG = os.path.join(ROOT, 'results', 'registry', 'registry.csv')

plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 7.4

CMAP = matplotlib.colormaps['inferno']

VARIANTS = [('env',   'D1  |z|'),
            ('env2',  'D1$^2$  (|z|)$^2$'),
            ('sqlaw', "D2'  Hilbert-free"),
            ('sq',    'D2  bare $x^2$')]

# 数据集顺序 = 手稿 §4.3 的对象阶梯（rung 1..6 = W1..W6，**与 Table 4 / §4.3 逐级对齐**）；
# 目录取自 registry 的 result_dir 列。
# ⚠ 末两级过去被写反（W6 旋转扫描排在 rung 5、W5 环形仿体排 rung 6），
#   与 §4.3 的阶梯和 Table 4 的 W 编号冲突 —— 已按阶梯顺序纠正。
ROWS = [
    ('own1', 'data1', 'results/wire/W1_single', 'W1',
     'single tungsten wire (point-like absorber)',
     'semicircle-128, R = 55 mm', '$f_0$ = 5 MHz, FOV = 40 mm, $N_x$ = 601'),
    ('own2', 'data2', 'results/wire/W2_double', 'W2',
     'two parallel tungsten wires (two points)',
     'semicircle-128, R = 55 mm', '$f_0$ = 5 MHz, FOV = 40 mm, $N_x$ = 601'),
    ('own4', 'data4', 'results/recheck/W3_fov60', 'W3',
     'X-shaped crossed filaments (lines)',
     'semicircle-128, R = 55 mm', 'FOV = 60 mm, $N_x$ = 1501, dx = 0.04 mm'),
    ('own6', 'data6', 'results/recheck/W4_f0meas', 'W4',
     'crossed filament, V-shaped (rotational, 32 ch)',
     'rotational 1440, R = 54.3 mm', '$F_0$ = 1.16 MHz (measured), FOV = 18 mm'),
    ('own5', 'data5', 'results/recheck/W5_f0meas', 'W5',
     'ring / tube phantom (static, 32 ch)',
     'static 1440, R = 17.5 mm', '$F_0$ = 0.35 MHz (measured), FOV = 18 mm, $N_x$ = 601'),
    ('own3', 'data3', 'results/recheck/W6_fov18_f0meas', 'W6',
     'rotational 200 steps (no prior archive)',
     'rotational 200, R = 16.0 mm', '$F_0$ = 2.00 MHz (measured), FOV = 18 mm, $N_x$ = 601'),
]


def load_registry():
    out = {}
    with open(REG, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            out[row['id']] = row
    return out


def norm(img):
    a = np.asarray(img, dtype=float)
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    m = a.max()
    return a / m if m > 0 else a


def main():
    reg = load_registry()

    fig = plt.figure(figsize=(15.6, 7.8))
    gs = fig.add_gridspec(2, 12, left=0.008, right=0.985, top=0.775,
                          bottom=0.028, wspace=0.10, hspace=1.15)

    for gi, (rid, did, folder, tag, obj, geom, cfg) in enumerate(ROWS):
        gr, gc0 = gi // 3, (gi % 3) * 4
        mat = os.path.join(ROOT, folder, '%s_results.mat' % tag)
        with h5py.File(mat, 'r') as f:
            imgs = {k: norm(f['IM'][k][...]) for k, _ in VARIANTS}

        axes = []
        for j, (key, _) in enumerate(VARIANTS):
            ax = fig.add_subplot(gs[gr, gc0 + j])
            ax.imshow(imgs[key], origin='lower', cmap=CMAP, vmin=0.0, vmax=1.0,
                      interpolation='nearest')
            ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_color('0.55'); s.set_linewidth(0.5)
            axes.append(ax)

        r = reg[rid]
        dcnr, dgcnr = float(r['dCNR']), float(r['dgCNR'])
        xc = 0.5 * (axes[0].get_position().x0 + axes[-1].get_position().x1)
        y0 = axes[0].get_position().y1
        fig.text(xc, y0 + 0.062,
                 '%s  -  %s   [rung %d/6, %s]' % (did, obj, gi + 1, r['verdict']),
                 ha='center', va='bottom', fontsize=7.9, fontweight='bold')
        fig.text(xc, y0 + 0.036,
                 '%s  |  %s' % (geom, cfg),
                 ha='center', va='bottom', fontsize=6.7, color='0.28')
        fig.text(xc, y0 + 0.011,
                 '$\\Delta$CNR(E$-$M) = %+.3f   $\\Delta$gCNR(E$-$M) = %+.3f   '
                 'DR gain = %+.1f dB' % (dcnr, dgcnr, float(r['DR_gain_dB'])),
                 ha='center', va='bottom', fontsize=6.7, color='0.28')

    # 共享色标（右缘）
    cax = fig.add_axes([0.9885, 0.30, 0.007, 0.40])
    sm = plt.cm.ScalarMappable(cmap=CMAP, norm=plt.Normalize(0, 1))
    cb = fig.colorbar(sm, cax=cax); cb.set_label('normalised amplitude (a.u.)', fontsize=7)
    cb.ax.tick_params(labelsize=6.3)

    fig.suptitle('Six in-house acquisitions under their per-dataset verified '
                 'configurations - all six KEEP\n'
                 'ordered by target difficulty',
                 fontsize=10.6, y=0.985)
    fig.text(0.5, 0.905, 'within each group, left to right:   '
             'D1  $|z|$    -    D1$^2$  $(|z|)^2$    -    '
             "D2'  Hilbert-free  (this work)    -    D2  bare $x^2$",
             ha='center', va='top', fontsize=8.2, color='0.15')
    fig.savefig(OUT, dpi=200, bbox_inches='tight', facecolor='white')
    print('saved:', OUT)


if __name__ == '__main__':
    main()
