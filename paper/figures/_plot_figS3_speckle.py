# -*- coding: utf-8 -*-
"""
Fig. S3 —— 散斑统计：闭式的成立域与实测偏差的归因

数据来源：results/study_speckle/speckle.mat（pa_study_speckle.m v3，Part A/B/C/D）

面板（2 x 3）：
  (a) Part A前提检验 —— 逐半径的通道级统计
      CV_inst（等强度指数型 =>1）、R_circ（相位均匀 =>0）、Kuiper V（均匀性检验）
  (b) Part B 系综分布 —— I_E 与 I_BS 的 CV 直方图 + 闭式理论线
  (c) Part D1 理论自洽对照 —— 合成 i.i.d. 模型命中闭式 => 理论与实现无误
  (d) Part D2 有效自由度 —— N_eff = M*(theo/CV)^2，说明实测偏高不是"理论错"
  (e) Part C 空间斑图 —— I_E 与 I_BS 的斑图 + 自相关衰减长度
  (f) Part C 分环包络 CV —— 能量域在同一实现内更平滑

口径纪律（对应 MEMORY §8；**v0.21 定稿口径**）：
  · P2 的闭式**只在「联合零均值正规复高斯」等独立随机模型内成立**。
  · ★ 实测 CV 高于闭式**指示**对该模型的偏离，但**归因未定（unresolved）**。
    候选机制至少四条：非高斯性 / 非正规性（伪协方差非零）/ realization 间方差混合 /
    有限系综与估计偏差；判别需要基于 R̂ 的有限样本区间分析（实验包 E8，**未做**）。
  · ⚠️ **不得**把超出量归给「通道独立性失效」：在正规复高斯下 `CV(I_BS) \equiv 1`
    **与 R 是否对角无关**；旧稿的「shared wavefront ⇒ CV rises」与 `N_eff(I_BS)=62.5/128`
    均已在 v0.21 **撤回**，本图亦不再绘 I_BS 的 N_eff。
  · 因此本图**不得**被读成"P2 被否证"，也**不得**用实测值去替换闭式。
  · Part D1 用合成 i.i.d. 对照把"理论错"与"前提不严格"两种可能分开：
    若 D1 命中闭式，则偏差出在**传播实现**，而非公式或代码——但**出在哪一机制仍未定**。
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

MAT = os.path.join(ROOT, 'results', 'study_speckle', 'speckle.mat')
OUT = os.path.join(ROOT, 'paper', 'figures', 'FigS3_speckle_cv.png')

for cand in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf']:
    if os.path.exists(cand):
        font_manager.fontManager.addfont(cand)
        break
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 8.5


def _read(v):
    a = np.array(v)
    if a.ndim >= 2 and a.shape[0] > 1 and a.shape[1] == 1:
        a = a.T
    return a


def _node(g):
    o = {}
    for k in g.keys():
        v = g[k]
        o[k] = _node(v) if isinstance(v, h5py.Group) else _read(v)
    return o


def main():
    if not os.path.exists(MAT):
        raise SystemExit('missing: %s' % MAT)
    D = _node(h5py.File(MAT, 'r'))

    M = int(_read(D['M_channels']).ravel()[0])
    theo = float(_read(D['theo_eq']).ravel()[0])

    fig = plt.figure(figsize=(11.4, 7.2))
    gs = fig.add_gridspec(2, 3, hspace=0.40, wspace=0.30,
                          left=0.065, right=0.985, top=0.855, bottom=0.08)

    # ---------------- (a) Part A 前提检验 ----------------
    ax = fig.add_subplot(gs[0, 0])
    r_mm = _read(D['premise']['r_mm']).ravel()
    cv = _read(D['premise']['cv_inst']).ravel()
    rc = _read(D['premise']['r_circ']).ravel()
    ku = _read(D['premise']['kuiper']).ravel()
    ax.plot(r_mm, cv, 'o-', color='#3b6ea5', lw=1.3, ms=4, label=r'$CV_{inst}$')
    ax.axhline(1.0, color='gray', ls='--', lw=0.9, label='target 1')
    ax.set_ylim(0, 2.45)
    ax.set_xlabel('radius (mm)', fontsize=8)
    ax.set_ylabel(r'$CV_{inst}$  (target 1)', fontsize=8)
    ax2 = ax.twinx()
    ax2.plot(r_mm, rc, 's-', color='#c0504d', lw=1.3, ms=4,
             label=r'$R_{circ}$ (target 0)')
    ax2.set_ylabel(r'$R_{circ}$  (target 0)', fontsize=8, color='#c0504d')
    ax2.tick_params(labelsize=7, colors='#c0504d')
    ax.tick_params(labelsize=7)
    ax.set_title(r'(a) premises, $a_m=g_mz_m(\tau_m)$' +
                 '\n$K_V$ = %.2f–%.2f (uniform exp. 0.016)' % (ku.min(), ku.max()),
                 fontsize=8.5, pad=4)
    # 图例放在轴**下方**，避免压住R_circ 的峰值（r = 2 mm 处 0.25）
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=6.6, frameon=False,
              loc='upper center', bbox_to_anchor=(0.5, -0.20), ncol=3)

    # ---------------- (b) Part B 系综分布 ----------------
    # I_E 与 I_BS 的量纲不同（能量 vs 幅值平方），**不能画在同一坐标轴上**：
    # 否则 I_BS 的长尾会把 I_E 的分布压成一根柱子，读者会误读成"I_E 没有散布"。
    # 故各自分布归一化到 [0,1] 后再画，并各自标出 CV。
    ax = fig.add_subplot(gs[0, 1])
    Ie = _read(D['ensemble']['Ie']).ravel()
    Ib = _read(D['ensemble']['Ibs']).ravel()
    cvE = Ie.std() / Ie.mean()
    cvB = Ib.std() / Ib.mean()
    rel = float(_read(D['ensemble']['Nens']).ravel()[0])
    bins = np.linspace(0, 1, 41)
    uE = (Ie - Ie.min()) / (Ie.max() - Ie.min() + 1e-30)
    uB = (Ib - Ib.min()) / (Ib.max() - Ib.min() + 1e-30)
    ax.hist(uE, bins=bins, color='#3b6ea5', alpha=0.80, edgecolor='none',
            label=r'$I_E$: CV = %.4f (%.2f$\times$)' % (cvE, cvE / theo))
    ax.hist(uB, bins=bins, color='#c0504d', alpha=0.55, edgecolor='none',
            label=r'$I_{BS}$: CV = %.4f (%.2f$\times$)' % (cvB, cvB))
    ax.set_xlabel('each estimator rescaled to [0, 1]', fontsize=8)
    ax.set_ylabel('counts (%d realisations)' % rel, fontsize=8)
    ax.tick_params(labelsize=7)
    se = 1.0 / np.sqrt(2.0 * rel)
    ax.set_title(r'(b) ensemble at the centre pixel' +
                 '\n' + r'closed form: $1/\sqrt{M}$ = %.4f for $I_E$, 1 for $I_{BS}$;' % theo +
                 '\n' + r'relative s.e. $1/\sqrt{2N_{ens}}$ = %.3f' % se,
                 fontsize=8.5, pad=4)
    ax.legend(fontsize=6.8, frameon=False)

    # ---------------- (c) Part D1 理论自洽 ----------------
    ax = fig.add_subplot(gs[0, 2])
    hasD = 'attrib' in D
    if hasD:
        sE = float(_read(D['attrib']['cvE_syn']).ravel()[0])
        sB = float(_read(D['attrib']['cvBS_syn']).ravel()[0])
    else:
        sE = sB = np.nan
    labels = [r'synthetic i.i.d.\n(D1 control)', r'back-projection\n(Part B)']
    valsE = [sE, cvE]
    valsB = [sB, cvB]
    x = np.arange(2)
    wd = 0.34
    if hasD:
        ax.bar(x - wd / 2, valsE, wd, color='#3b6ea5', label=r'$CV(I_E)$')
        ax.bar(x + wd / 2, valsB, wd, color='#c0504d', label=r'$CV(I_{BS})$')
        ax.plot([-0.45, 1.45], [theo, theo], 'k--', lw=1.0,
                label=r'closed form $1/\sqrt{M}$ = %.4f' % theo)
        ax.plot([-0.45, 1.45], [1.0, 1.0], ':', color='gray', lw=1.0,
                label=r'closed form 1')
        ax.set_ylim(0, max(1.7, np.nanmax(valsB) * 1.25))
        ax.legend(fontsize=6.4, frameon=False, ncol=2)
        # 注意：含 '$\times$' 的那一段必须是 **raw** 字符串，否则 '\t' 会被当成制表符，
        # 标题会渲染成 "0.989⟨TAB⟩imes"。换行 '\n' 则要留在 raw 串之外。
        ttl = (r'(c) theory self-consistency' + '\n'
               + r'D1 hits the closed form: %.3f$\times$, %.3f$\times$'
               % (sE / theo, sB))
    else:
        # Part D 缺失时**不用空图占位**——直接画出已有的证据并说明缺什么
        ax.bar([1 - wd / 2, 1 + wd / 2], [cvE, cvB], wd,
               color=['#3b6ea5', '#c0504d'])
        ax.plot([-0.45, 1.45], [theo, theo], 'k--', lw=1.0)
        ax.set_xticks([1])
        ax.set_xticklabels([r'back-projection\n(Part B)'], fontsize=7)
        ax.text(0.05, 0.60,
                'Part D (synthetic i.i.d.\ncontrol) not available in\n'
                'this run: the left bar is\n'
                'missing, so the excess CV\n'
                'cannot yet be attributed\n'
                'to any single mechanism\n'
                '(unresolved; E8 not done).',
                transform=ax.transAxes, fontsize=6.4, va='top',
                bbox=dict(fc='white', ec='#999', lw=0.5))
        ax.set_ylim(0, max(1.7, cvB * 1.25))
        ttl = r'(c) theory self-consistency' + '\n(control run pending)'
    ax.set_ylabel('coefficient of variation', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_title(ttl, fontsize=8.5, pad=4)

    # ---------------- (d) Part D2 矩匹配描述（**只给 I_E**） ----------------
    # v0.21：I_BS 的闭式基准是 Gamma(1)（指数分布），**不是** M；把 1/CV^2 当通道数
    # 没有模型依据，旧稿的 62.5/128 已撤回。故本面板**只画 I_E**，并把"这是描述、
    # 不是独立性证明"写在图上，同时明示 I_BS 不定义 N_eff。
    ax = fig.add_subplot(gs[1, 0])
    if hasD:
        nE = float(_read(D['attrib']['Neff_E']).ravel()[0])
    else:
        nE = M * (theo / cvE) ** 2
    ax.bar([0], [M], 0.5, color='#bbbbbb', label='$M$ channels (geometric)')
    ax.bar([0], [nE], 0.5, color='#3b6ea5',
           label=r'$N_{eff}$ of $I_E$ (moment-matching)')
    ax.text(0, nE + 2, '%.0f%%' % (100 * nE / M), ha='center', fontsize=7.5)
    ax.plot([-0.45, 0.45], [nE, nE], 'k--', lw=1.0)
    ax.set_xticks([0])
    ax.set_xticklabels([r'$I_E$'], fontsize=9)
    ax.set_xlim(-0.6, 0.6)
    ax.set_ylabel('effective number of channels', fontsize=8)
    ax.set_ylim(0, M * 1.25)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6.4, frameon=False, loc='upper right')
    ax.text(0.03, 0.10,
            '$N_{eff}$ here is a moment-matching\n'
            'description, not a proof of channel\n'
            'independence.\n'
            r'$I_{BS}$: no $N_{eff}$ is defined' '\n'
            r'(its closed form is Gamma(1), not $M$);'
            '\nthe former 62.5/128 is withdrawn.',
            transform=ax.transAxes, fontsize=6.0, va='bottom',
            bbox=dict(fc='white', ec='#999', lw=0.5))
    ax.set_title(r'(d) effective degrees of freedom' + '\n' +
                 r'$N_{eff}=M\,(CV_{th}/CV_{meas})^2$' + ' (descriptive)', fontsize=8.5, pad=4)

    # ---------------- (e) 空间斑图 ----------------
    # 只显示分析区（|r| <= roiR），**不能**显示全40 mm 视场：
    # 全视场的未插值 BP 由放射状通道几何主导，读者会把它误读成"能量臂有条纹伪影"，
    # 而 (f) 的分环 CV 恰恰是在这个分析区里算的，两者必须同域。
    # 显示用三次样条上采样（仅影响显示，**所有 CV/自相关仍在原始网格上算**）。
    ax = fig.add_subplot(gs[1, 1])
    IE = _read(D['roiImg']['E'])
    IBS = _read(D['roiImg']['BS'])
    ax_mm = _read(D['ax_mm']).ravel()
    dx = float(ax_mm[1] - ax_mm[0])
    half = 4.0                                   # mm，与 (f) 的最外环一致
    n = int(round(half / dx))
    c0 = IE.shape[0] // 2
    w = slice(c0 - n, c0 + n + 1)
    up = 4
    from scipy.ndimage import zoom
    IEc = zoom(np.maximum(IE[w, w], 0), up, order=3)
    IBc = zoom(np.maximum(IBS[w, w], 0), up, order=3)
    ext = [-half, half, -half, half]
    vE = np.percentile(IEc, 99.0)
    ax.imshow(IEc, origin='lower', cmap='gray', vmin=0, vmax=vE,
              extent=ext, interpolation='bilinear')
    axi = ax.inset_axes([0.635, 0.455, 0.355, 0.40])
    axi.imshow(IBc, origin='lower', cmap='gray', vmin=0,
               vmax=np.percentile(IBc, 99.0), extent=ext,
               interpolation='bilinear')
    axi.set_xticks([]); axi.set_yticks([])
    axi.set_title(r'$I_{BS}$', fontsize=7, pad=2)
    ax.set_xlim(-half, half); ax.set_ylim(-half, half)
    ax.set_xticks([-4, 0, 4]); ax.set_yticks([-4, 0, 4])
    ax.tick_params(labelsize=7)
    lagE = float(_read(D['lagE_mm']).ravel()[0])
    lagB = float(_read(D['lagB_mm']).ravel()[0])
    ax.set_title(r'(e) speckle maps, same realisation' +
                 '\n' + r'$I_E$ (main), $I_{BS}$ (inset); analysis window $\pm$4 mm',
                 fontsize=8.5, pad=4)
    ax.set_xlabel(r'1/e autocorr. width:  $I_E$ %.2f mm,  $I_{BS}$ %.2f mm '
                  r'($\lambda/2$ = %.2f mm)' % (lagE, lagB,
                                                 float(_read(D['lamR_D_mm']).ravel()[0])),
                  fontsize=7.2)

    # ---------------- (f) 分环包络 CV ----------------
    ax = fig.add_subplot(gs[1, 2])
    ed = _read(D['ring']['edges']).ravel()
    cE = _read(D['ring']['cvE']).ravel()
    cB = _read(D['ring']['cvB']).ravel()
    ctr = 0.5 * (ed[:-1] + ed[1:])
    wid = np.diff(ed)
    ax.bar(ctr - wid / 4, cE, wid / 2, color='#3b6ea5', edgecolor='none',
           label=r'$CV(I_E)$')
    ax.bar(ctr + wid / 4, cB, wid / 2, color='#c0504d', edgecolor='none',
           label=r'$CV(I_{BS})$')
    ax.axhline(theo, color='k', ls='--', lw=1.0,
               label=r'$1/\sqrt{M}$ = %.4f' % theo)
    ax.set_xlabel('ring radius (mm)', fontsize=8)
    ax.set_ylabel('within-ring CV', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6.8, frameon=False)
    ax.set_title(r'(f) local envelope CV per ring' +
                 '\nenergy domain is smoother within one realisation',
                 fontsize=8.5, pad=4)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)

    fig.suptitle('Fig. S3  Speckle statistics: the domain in which the closed form '
                 'holds,\nand the size of the measured excess (attribution unresolved)',
                 fontsize=10.6, y=0.985)
    fig.savefig(OUT, dpi=220, bbox_inches='tight', facecolor='white')
    print('saved:', OUT)
    print('  M=%d  closed form 1/sqrt(M)=%.4f' % (M, theo))
    print('  CV(I_E)=%.4f (%.2fx)   CV(I_BS)=%.4f (%.2fx)'
          % (cvE, cvE / theo, cvB, cvB))
    if hasD:
        print('  D1 synthetic: CV(I_E)=%.4f (%.3fx)  CV(I_BS)=%.4f (%.3fx)'
              % (sE, sE / theo, sB, sB))
        print('  N_eff: I_E %.1f/M (%.2f)   I_BS %.1f (%.2f)'
              % (nE, nE / M, nB, nB / M))


if __name__ == '__main__':
    main()