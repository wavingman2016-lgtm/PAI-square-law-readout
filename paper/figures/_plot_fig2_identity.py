# -*- coding: utf-8 -*-
"""
Fig.2 —— 恒等式、交叉项与相干场 mu

数据来源：results/fig2_identity/fig2_identity.mat（pa_study_fig2_identity.m 产出）

面板（6 联）：
  (a) I_C=|sum a_m|            相干幅值（Arm C）        —— 幅值域
  (b) I_BS=I_C^2               图像域平方（D4）        —— 注意这不是 I_E
  (c) I_E=sum|a_m|^2           能量域（Arm E）        —— 能量型
  (d) X = I_BS - I_E           交叉项（相干分量）—— E 臂整个丢弃的部分
  (e) mu(r)相干场              实测标量场，叠加 1/M 均匀相位期望线
  (f) 恒等式检验               逐像素 |I_BS - M*mu*I_E|/I_BS 的直方图（对数横轴）

口径纪律（对应 MEMORY §1/§8）：
  · 三个场必须来自**同一次反投影采样**，否则恒等式不成立（脚本已保证）。
  · 几何补偿只有 g_m = d_m/R；不做 r^2（正文 §2.4）。
  · 不画 D3（保号平方，非物理量）—— 旧 draft 的主要缺陷。
  · mu 只用第一次实现（恒等式是单次实现内的陈述）。
  · 面板 (f) 的残差应落在机器精度量级，如实标注，不掩饰。
"""
import os
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..')).replace(os.sep, '/')

MAT = os.path.join(ROOT, 'results', 'fig2_identity', 'fig2_identity.mat')
OUT = os.path.join(ROOT, 'paper', 'figures', 'Fig02_identity_crossterm.png')

# ---- 字体（中英混排）----
for cand in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf',
             'C:/Windows/Fonts/arial.ttf']:
    if os.path.exists(cand):
        font_manager.fontManager.addfont(cand)
        break
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 9


def _read(v):
    """h5py dataset -> ndarray（MATLAB 列主序需转置还原）。"""
    arr = np.array(v)
    if arr.ndim >= 2 and arr.shape[0] > 1 and arr.shape[1] == 1:
        arr = arr.T
    return arr


def _node(g):
    """dataset -> ndarray；group -> dict（递归）。"""
    out = {}
    for k in g.keys():
        v = g[k]
        if isinstance(v, h5py.Group):
            out[k] = _node(v)
        else:
            out[k] = _read(v)
    return out


def load(path):
    """读 MATLAB v7.3 struct（-struct 展开 => 顶层各字段为 dataset）。"""
    with h5py.File(path, 'r') as f:
        return _node(f)


def m(v):
    """MATLAB logical -> bool"""
    return np.array(v).astype(bool)


def im(ax, img, extent_mm, title, cmap='gray', vmin=None, vmax=None):
    im_ = ax.imshow(img.T, origin='lower', cmap=cmap, extent=extent_mm,
                    vmin=vmin, vmax=vmax, interpolation='nearest',
                    aspect='equal')
    ax.set_title(title, fontsize=8.5, pad=4)
    ax.set_xlabel('x (mm)', fontsize=7.5)
    ax.set_ylabel('y (mm)', fontsize=7.5)
    ax.tick_params(labelsize=7)
    return im_


def main():
    if not os.path.exists(MAT):
        raise SystemExit('missing: %s' % MAT)
    D = load(MAT)

    IC = np.asarray(D['IC']).T          # 还原为 (row=y, col=x)
    IE = np.asarray(D['IE']).T
    IBS = np.asarray(D['IBS']).T
    MU = np.asarray(D['MU']).T
    XT = np.asarray(D['XT']).T
    RELERR = np.asarray(D['RELERR']).T
    valid = m(D['valid']).T

    # 注意：MATLAB 侧 `axis_mm` 字段实际以**米**存储（数值 ±0.02），并非毫米。
    # 乘以 1e3 得到真正的毫米坐标（±20 mm），与正文 R = 55 mm、目标 5/6 mm 一致。
    ax_mm = np.asarray(D['grid']['axis_mm']).ravel() * 1e3
    Nx = len(ax_mm)
    ex = [ax_mm[0], ax_mm[-1], ax_mm[0], ax_mm[-1]]

    # 目标位置（读 target）
    if 'target' in D:
        tr = np.asarray(D['target']['r']).ravel()
        ta = np.asarray(D['target']['amp']).ravel()
    else:
        tr, ta = [], []

    M = int(np.asarray(D['sensor']['M']).ravel()[0])

    def norm(a):
        return a / (np.nanmax(np.abs(a)) + 1e-30)

    def dw(a, lo_p=2.0, hi_p=99.7):
        """分位数显示窗：避免旁瓣/零区淹没目标（不改数据，只改显示）。"""
        v = np.abs(a[np.isfinite(a)])
        v = v[v > 0]
        if v.size == 0:
            return 0.0, 1.0
        lo = np.percentile(v, lo_p)
        hi = np.percentile(v, hi_p)
        return max(lo, 1e-30), max(hi, lo * 1.000001)

    fig = plt.figure(figsize=(11.6, 7.4))
    gs = fig.add_gridspec(2, 3, hspace=0.30, wspace=0.26,
                          left=0.06, right=0.985, top=0.90, bottom=0.075)

    # (a) I_C
    ax = fig.add_subplot(gs[0, 0])
    lo, hi = dw(IC)
    im_ = im(ax, IC, ex, r'(a)  $I_C=|\sum_m a_m|$  coherent amplitude (Arm C)',
             cmap='gray', vmin=lo, vmax=hi)
    plt.colorbar(im_, ax=ax, fraction=0.046, pad=0.03)

    # (b) I_BS
    ax = fig.add_subplot(gs[0, 1])
    lo, hi = dw(IBS)
    im_ = im(ax, IBS, ex, r'(b)  $I_{BS}=I_C^2$  image-domain square (D4)',
             cmap='gray', vmin=lo, vmax=hi)
    plt.colorbar(im_, ax=ax, fraction=0.046, pad=0.03)

    # (c) I_E
    ax = fig.add_subplot(gs[0, 2])
    lo, hi = dw(IE)
    im_ = im(ax, IE, ex, r'(c)  $I_E=\sum_m|a_m|^2$  energy domain (Arm E)',
             cmap='gray', vmin=lo, vmax=hi)
    plt.colorbar(im_, ax=ax, fraction=0.046, pad=0.03)

    # (d) 交叉项
    ax = fig.add_subplot(gs[1, 0])
    lim = np.nanpercentile(np.abs(XT[valid]), 99.5) + 1e-30
    im_ = im(ax, XT, ex, r'(d)  cross term  $X=I_{BS}-I_E$  (discarded by $E$)',
             cmap='RdBu_r', vmin=-lim, vmax=lim)
    plt.colorbar(im_, ax=ax, fraction=0.046, pad=0.03)

    # (e) mu 场（对数色标：mu 的动态范围跨 3 个数量级）
    ax = fig.add_subplot(gs[1, 1])
    mv = MU[valid]
    pos = mv[mv > 0]
    lo = np.percentile(pos, 2)
    hi = np.percentile(pos, 99.5)
    im_ = im(ax, np.where(valid, np.maximum(MU, lo), np.nan), ex,
             '', cmap='viridis', vmin=lo, vmax=hi)
    im_.norm = matplotlib.colors.LogNorm(vmin=lo, vmax=hi)
    ax.set_title(r'(e)  coherence field  $\mu(r)$  (log colour)' +
                 '\nmedian %.4f, uniform-phase $1/M$ = %.4f' %
                 (np.nanmedian(mv), 1.0 / M), fontsize=8.5, pad=4)
    cb = plt.colorbar(im_, ax=ax, fraction=0.046, pad=0.03)
    cb.ax.tick_params(labelsize=6.5)

    # (f) 恒等式残差直方图
    ax = fig.add_subplot(gs[1, 2])
    r = RELERR[valid]
    r = np.maximum(r, 1e-20)
    ax.hist(np.log10(r), bins=60, color='#3b6ea5', edgecolor='none')
    ax.axvline(np.log10(np.finfo(float).eps),
               color='crimson', ls='--', lw=1.0,
               label='double precision  $\\epsilon$ = %.1e' % np.finfo(float).eps)
    ax.set_xlabel(r'$\log_{10}\left[\,|I_{BS}-M\mu I_E| / I_{BS}\,\right]$', fontsize=8)
    ax.set_ylabel('pixels', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=7, frameon=False, loc='upper left')
    ax.set_title(r'(f)  identity residual $I_{BS}=M\mu I_E$' +
                 '\nmax = %.2e  (round-off, not a measurement)'
                 % np.nanmax(RELERR[valid]), fontsize=8.5, pad=4)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)

    # 目标标记（叠在 (a)(b)(c) 上）
    for k in range(3):
        a = fig.axes[k]
        for j, rr in enumerate(tr):
            a.plot(rr * 1e3, 0, 'r+', ms=7, mew=1.1)   # tr 以米存储，换算为 mm

    fig.suptitle('Fig. 2  Channel-wise squaring vs image-domain squaring: '
                 'the cross term and the measurable coherence field',
                 fontsize=10.5, y=0.975)
    fig.savefig(OUT, dpi=220, bbox_inches='tight', facecolor='white')
    print('saved:', OUT)
    print('  max identity residual : %.3e' % np.nanmax(RELERR[valid]))
    print('  mu  median / (1/M)    : %.4f / %.4f' % (np.nanmedian(mv), 1.0 / M))


if __name__ == '__main__':
    main()