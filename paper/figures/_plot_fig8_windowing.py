# -*- coding: utf-8 -*-
"""
Figure 8 — the display window is part of the method.

Five windowing settings applied to the same Arm-E image, on two datasets:
    top row    W1 / data1  (single wire, point-like; FOV = 40 mm)
    bottom row W3 / data4  (X-shaped crossed filaments; FOV = 60 mm)

Settings (from results/supp/window_table.csv; lo/hi are the colour limits):
    (1) all-range (baseline)        affine
    (2) narrow-detail window        affine
    (3) balanced - legacy default   CROPPED  - collapses structure, inflates CNR
    (4) wide-dynamic window         affine
    (5) adaptive quantile (reco.)   affine

口径：仿射窗对 gCNR/CNR 严格不变；只有**裁剪/饱和**窗会改变可分性。
      本图把 legacy 裁剪窗与四个仿射窗并列，就是为了让这一点可见。
"""
import os
import csv
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..')).replace(os.sep, '/')

TAB = os.path.join(ROOT, 'results', 'supp', 'window_table.csv')
OUT = os.path.join(ROOT, 'paper', 'figures', 'Fig08_windowing.png')

plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 8.4

ROWS = [
    ('W1', 'results/wire/W1_single/W1_results.mat',
     'W1 / data1  -  single wire (point-like),  FOV = 40 mm', 40.0),
    ('W3', 'results/recheck/W3_fov60/W3_results.mat',
     'W3 / data4  -  X-shaped crossed filaments,  FOV = 60 mm', 60.0),
]

EN = ['(1) all-range (baseline)', '(2) narrow-detail window',
      '(3) balanced - legacy default', '(4) wide-dynamic window',
      '(5) adaptive quantile (recommended)']
IS_CROPPED = [False, False, True, False, False]


def load_windows():
    out = {}
    with open(TAB, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            out.setdefault(r['dataset'].split()[0], []).append(r)
    return out


def main():
    win = load_windows()
    fig, axes = plt.subplots(2, 5, figsize=(15.4, 7.4))
    fig.subplots_adjust(left=0.030, right=0.982, top=0.800, bottom=0.105,
                        wspace=0.20, hspace=0.42)

    for ri, (tag, folder, rowtitle, fov) in enumerate(ROWS):
        with h5py.File(os.path.join(ROOT, folder), 'r') as f:
            img = np.asarray(f['IM/sqlaw'][...], dtype=np.float64)
        ext = [-fov / 2, fov / 2, -fov / 2, fov / 2]
        for ci, r in enumerate(win[tag]):
            lo, hi = float(r['lo']), float(r['hi'])
            ax = axes[ri, ci]
            pc = ax.imshow(img, origin='lower', extent=ext, cmap='inferno',
                           vmin=lo, vmax=hi, aspect='equal',
                           interpolation='nearest')
            cb = fig.colorbar(pc, ax=ax, fraction=0.046, pad=0.025)
            cb.ax.tick_params(labelsize=6.0)
            if ri == 0:
                ax.set_title(EN[ci], fontsize=7.8, pad=4.0)
            sv = float(r['structure_visible']); bg = float(r['bitdepth_gain'])
            lab = 'structure %.0f%%   gain x%.2f' % (sv * 100, bg)
            ax.text(0.025, 0.022, lab, transform=ax.transAxes, ha='left',
                    va='bottom', fontsize=6.6,
                    color=('crimson' if IS_CROPPED[ci] else 'white'),
                    bbox=dict(facecolor='black', alpha=0.55, pad=1.6,
                              edgecolor='none'))
            ax.tick_params(labelsize=6.2)
            if ci == 0:
                ax.set_ylabel('%s\ny (mm)' % tag, fontsize=8.0)
            else:
                ax.set_yticklabels([])
            if ri == 1:
                ax.set_xlabel('x (mm)', fontsize=7.6)

    fig.canvas.draw()
    for ri in range(2):
        bbs = [axes[ri, c].get_position() for c in range(5)]
        x0 = min(b.x0 for b in bbs); x1 = max(b.x1 for b in bbs)
        y1 = max(b.y1 for b in bbs)
        fig.text(0.5 * (x0 + x1), y1 + 0.042, ROWS[ri][2], ha='center',
                 va='bottom', fontsize=9.8, fontweight='bold')

    fig.text(0.5, 0.965,
             'Window settings on the same Arm-E image - the display window is '
             'part of the method', ha='center', va='center',
             fontsize=10.8, fontweight='bold')
    fig.text(0.5, 0.012,
             'affine windows (1, 2, 4, 5) leave gCNR / CNR strictly invariant;   '
             'only the cropped legacy window (3) collapses the visible structure '
             'and inflates CNR / DR', ha='center', va='bottom',
             fontsize=8.4, color='0.2')
    fig.savefig(OUT, dpi=200, bbox_inches='tight', facecolor='white')
    print('saved:', OUT)


if __name__ == '__main__':
    main()
