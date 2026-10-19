# -*- coding: utf-8 -*-
"""
Fig. 7(d) —— 3D-PACT 大鼠脑与人乳腺（**仅重建体，定性展示**）

数据来源：data_ext/3D-PACT/Fig. 4/
  · rat_brain_image_raw.mat      image_comp (180, 250, 120)
  · left_breast_image_raw.mat     image_comp (800, 800, 305)
  · right_breast_image_raw.mat    image_comp (800, 800, 305)

口径纪律（MEMORY §7 与docs/13）：
  · 3D-PACT **只有官方重建体，没有原始通道数据** ⇒ 本面板**不做任何三臂对照、
    不报gCNR / ΔgCNR / 宽度**。它的唯一作用是"方法所处理的信号形态在临床
    在体目标（脑血管、乳腺组织）中确实存在"这一**背景性**陈述。
  · 因此图注必须写明"qualitative display only, reconstructed volumes"，
    **禁止**在图上叠加任何指标数字或色标数值标签以外的定量读数。
  · 显示用最大密度投影（MIP）+ 逐图自适应窗宽；窗参数写在图内小字，
    不隐藏（MEMORY §9：窗是显式约定，不是"调好看"）。
"""
import os
import numpy as np
import scipy.io as sio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..')).replace(os.sep, '/')

PACT = os.path.join(ROOT, 'data_ext', '3D-PACT')
# 大鼠脑在 Fig. 2，人乳腺在 Fig. 4（作者按图分目录存放）
SRC = {'rat': os.path.join(PACT, 'Fig. 2'),
       'brs': os.path.join(PACT, 'Fig. 4')}
OUT = os.path.join(ROOT, 'paper', 'figures', 'Fig07d_3dpact_qualitative.png')

for cand in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf']:
    if os.path.exists(cand):
        font_manager.fontManager.addfont(cand)
        break
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 8.5

CMAP = matplotlib.colormaps['inferno']


def _load(subdir, fname, key):
    p = os.path.join(SRC[subdir], fname)
    if not os.path.exists(p):
        raise SystemExit('missing: %s' % p)
    d = sio.loadmat(p)
    return np.asarray(d[key], dtype=float)


def _mip(vol, keep=None):
    """最大密度投影。keep 指定保留的轴顺序（0,1,2 的子集/置换）。"""
    if keep is not None:
        vol = np.transpose(vol, keep)
    return vol.max(axis=2)


def _win(img, lo_p=50.0, hi_p=99.7):
    """分位数窗：显式给出窗位/窗宽，符合 MEMORY §9的显式窗约定。"""
    lo = np.percentile(img, lo_p)
    hi = np.percentile(img, hi_p)
    if hi <= lo:
        hi = lo + 1e-12
    return lo, hi, hi - lo


def main():
    rat = _load('rat', 'rat_brain_image_raw.mat', 'image_comp')
    lbr = _load('brs', 'left_breast_image_raw.mat', 'image_comp')
    rbr = _load('brs', 'right_breast_image_raw.mat', 'image_comp')
    print('loaded: rat %s  lbr %s  rbr %s' % (rat.shape, lbr.shape, rbr.shape))

    panels = [
        ('rat brain in vivo', rat, (2, 0, 1), '180 x 250 x 120'),
        ('human breast (left)', lbr, (2, 0, 1), '800 x 800 x 305'),
        ('human breast (right)', rbr, (2, 0, 1), '800 x 800 x 305'),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(11.4, 4.35))
    gs = fig.add_gridspec(1, 3, left=0.035, right=0.975, top=0.78, bottom=0.155,
                          wspace=0.30)
    for ax in axes:
        ax.remove()

    for i, (name, vol, keep, dims) in enumerate(panels):
        ax = fig.add_subplot(gs[0, i])
        mip = _mip(vol, keep)
        lo, hi, ww = _win(mip)
        im = ax.imshow(mip, origin='lower', cmap=CMAP, vmin=lo, vmax=hi,
                       aspect='auto', interpolation='nearest')
        cb = fig.colorbar(im, ax=ax, fraction=0.040, pad=0.025)
        cb.ax.tick_params(labelsize=6.4)
        cb.set_label('MIP (a.u.)', fontsize=7)
        ax.set_xticks([]); ax.set_yticks([])
        # 面板编号用 (c1)(c2)(c3)：本图是正文 Fig. 7 的 (c) 面板，内部子图沿用同一字母。
        ax.set_title('(c%d) %s' % (i + 1, name), fontsize=8.8, pad=5)
        ax.text(0.0, -0.055,
                'volume %s; MIP along the 3rd axis\n'
                'window: WL = %.3g, WW = %.3g (p50–p99.7)'
                % (dims, lo, ww),
                transform=ax.transAxes, fontsize=6.5, va='top', color='0.25')

    fig.suptitle(
        '3D-PACT reconstructed volumes — qualitative display only\n'
        'supplied as reconstructed volumes by the authors; no raw channel data, '
        'so no three-arm\ncomparison and no gCNR / width is computed or claimed '
        'here',
        fontsize=10.0, y=0.985)
    fig.savefig(OUT, dpi=220, bbox_inches='tight', facecolor='white')
    print('saved:', OUT)


if __name__ == '__main__':
    main()
