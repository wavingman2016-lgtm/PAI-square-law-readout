# -*- coding: utf-8 -*-
"""
Figure 7c — RSOM human skin in vivo: what squaring does and does not change.

Four rasters built from the same A-lines (25351 lines, 101 x 251 grid,
dx = 12 um, dy = 20 um, 1 GHz sampling, 532 nm):
    (1) MIP of the linear envelope      max_t |z|
    (2) MIP of the squared envelope     max_t |z|^2
    (3) depth-integrated amplitude      sum_t |z|
    (4) depth-integrated energy         sum_t |z|^2

要点：max 与单调映射可交换 ⇒ (1)、(2) 逐像素等价（仅显示标度不同）；
      而求和**不**与映射交换 ⇒ (3)、(4) 是真正不同的聚合量。
      这正是"通道级平方不是免费的收益"在图像上的一个具体体现。

数据来源：data_ext/RSOM_melanoma/Normal_Breathing.mat
          fields S (25351 x 2528, int16), positionXY, dx, dy（v7 格式，scipy.io.loadmat）
"""
import os
import numpy as np
import scipy.io as sio
from scipy.signal import hilbert
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..')).replace(os.sep, '/')

SRC = os.path.join(ROOT, 'data_ext', 'RSOM_melanoma', 'Normal_Breathing.mat')
OUT = os.path.join(ROOT, 'paper', 'figures', 'Fig07c_rsom_check.png')

plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 8.6


def envelope(S, chunk=1500):
    """沿采样轴做 Hilbert 变换并取模；分块以控内存。"""
    out = np.empty_like(S, dtype=np.float32)
    for i in range(0, S.shape[0], chunk):
        j = min(i + chunk, S.shape[0])
        out[i:j] = np.abs(hilbert(np.asarray(S[i:j], dtype=np.float64), axis=1))
    return out


def main():
    d = sio.loadmat(SRC, squeeze_me=True)
    S = np.asarray(d['S'], dtype=np.float32)
    P = np.asarray(d['positionXY'], dtype=float)
    dx = float(np.asarray(d['dx']).ravel()[0])   # mm
    dy = float(np.asarray(d['dy']).ravel()[0])   # mm
    print('S', S.shape, 'dx', dx, 'dy', dy)

    xs = np.unique(P[:, 0]); ys = np.unique(P[:, 1])
    nx, ny = xs.size, ys.size
    ix = np.searchsorted(xs, P[:, 0]); iy = np.searchsorted(ys, P[:, 1])
    lin = iy * nx + ix

    env = envelope(S)                    # |z|
    mip_a = np.zeros(ny * nx, dtype=np.float32)
    mip_e = np.zeros(ny * nx, dtype=np.float32)
    sum_a = np.zeros(ny * nx, dtype=np.float32)
    sum_e = np.zeros(ny * nx, dtype=np.float32)
    mip_a[lin] = env.max(axis=1)
    sq = env * env
    mip_e[lin] = sq.max(axis=1)
    sum_a[lin] = env.sum(axis=1)
    sum_e[lin] = sq.sum(axis=1)

    rasters = [mip_a.reshape(ny, nx), mip_e.reshape(ny, nx),
               sum_a.reshape(ny, nx), sum_e.reshape(ny, nx)]
    titles = [r'(1)  MIP, linear envelope    $\max_t|z|$',
              r'(2)  MIP, squared envelope    $\max_t|z|^{2}$',
              r'(3)  depth-integrated amplitude    $\sum_t|z|$',
              r'(4)  depth-integrated energy    $\sum_t|z|^{2}$']

    ext = [0, nx * dx, 0, ny * dy]       # mm
    fig, axes = plt.subplots(1, 4, figsize=(15.4, 4.5))
    fig.subplots_adjust(left=0.035, right=0.965, top=0.80, bottom=0.16, wspace=0.28)
    for k, (ax, img, ttl) in enumerate(zip(axes, rasters, titles)):
        img = np.nan_to_num(img, nan=0.0)
        lo, hi = 0.0, np.percentile(img, 99.5)
        if hi <= lo:
            hi = lo + 1e-12
        pc = ax.imshow(img, origin='lower', extent=ext, cmap='hot',
                       vmin=lo, vmax=hi, aspect='auto', interpolation='nearest')
        cb = fig.colorbar(pc, ax=ax, fraction=0.043, pad=0.025)
        cb.ax.tick_params(labelsize=6.4)
        ax.set_title(ttl, fontsize=8.8, fontweight='bold', pad=5)
        ax.set_xlabel('x (mm)', fontsize=8.0)
        if k == 0:
            ax.set_ylabel('y (mm)', fontsize=8.0)
        else:
            ax.set_yticklabels([])
        ax.tick_params(labelsize=6.8)

    fig.text(0.5, 0.925,
             'RSOM human skin in vivo (melanoma study, 532 nm, 1 GHz sampling, '
             '25351 A-lines)', ha='center', va='center',
             fontsize=10.6, fontweight='bold')
    fig.text(0.5, 0.055,
             'max and a monotone map commute:  (1) and (2) are pixel-identical;   '
             'summation and a monotone map do not:  (3) and (4) are genuinely '
             'different aggregates', ha='center', va='center', fontsize=8.4,
             color='0.2')
    fig.savefig(OUT, dpi=220, bbox_inches='tight', facecolor='white')
    print('saved:', OUT)
    # 一致性自检：② 必须恰为 ① 的平方（max 与平方可交换，因 |z| >= 0）
    a = rasters[0].ravel(); b = rasters[1].ravel()
    rel = np.abs(b - a * a) / np.maximum(np.abs(b), 1e-12)
    print('max relative deviation of (2) from (1)^2 = %.3e (must be ~0)' % rel.max())
    assert rel.max() < 1e-5, 'panel (2) must be exactly panel (1) squared'


if __name__ == '__main__':
    main()
