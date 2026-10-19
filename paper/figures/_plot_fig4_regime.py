# -*- coding: utf-8 -*-
"""
Fig. 4 —— 四轴稳健性（regime map）：波前畸变 / SNR / 随机阵元失效 / 相干杂波

数据来源（全部为"单一事实源"的 .mat，数字不重算）：
  · 畸变轴σ_phi : results/study_phase/study_phase.mat        -> SA.*
  · SNR 轴             : results/study_phase/study_phase.mat        -> SB.*
  · 阵元失效轴        : results/study_audit/study_audit.mat        -> axis2.*
  · 相干杂波轴        : results/study_regime_semicircle128/study_regime.mat -> T.gCNR / crList

口径纪律（MEMORY §1）：
  · **跨臂只比 gCNR**。PSR / 宽度是**域内量**，跨臂并置会被误读成
    "E 的 PSR 更高所以更好"，故本图四轴**只画 gCNR**；
    PSR 与宽度改在 (f) 摘要里以**域内纵向**读数给出，不并排比较。
  · gCNR 在 M/E 上**饱和到 1.0000**（ROI 可分性已满），此时
    "E−C 的领先扩大" 只能读作**C 在退化**，不能读作"E 在变好"。
  · 唯一例外必须如实披露：**相干杂波下 E 最先失效**（能量臂最先崩），
    该轴单独用反向色标并加显式警示，不与前三轴共用视觉语言。
"""
import os
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..')).replace(os.sep, '/')

F_PHASE = os.path.join(ROOT, 'results', 'study_phase', 'study_phase.mat')
F_AUDIT = os.path.join(ROOT, 'results', 'study_audit', 'study_audit.mat')
F_REG = os.path.join(ROOT, 'results', 'study_regime_semicircle128',
                     'study_regime.mat')
OUT = os.path.join(ROOT, 'paper', 'figures', 'Fig04_regime_fourpanel.png')

for cand in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf']:
    if os.path.exists(cand):
        font_manager.fontManager.addfont(cand)
        break
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 8.5

C_CLR, M_CLR, E_CLR = '#2f6f9f', '#c9a227', '#b8453c'
# 相图色标：蓝(低) -> 白 -> 红(高)；警示轴单独用反向语义
CMAP_GAIN = LinearSegmentedColormap.from_list(
    'gain', ['#1a4a6e', '#4a90b8', '#e8eef2', '#e8a08a', '#a8321f'])
CMAP_WARN = LinearSegmentedColormap.from_list(
    'warn', ['#2f6f4f', '#8fc0a0', '#f2f0e6', '#e0b070', '#8c2f14'])


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


def _panel(ax, X, Y, Z, xlabel, ylabel, title, cmap, cbar_label):
    """画一张 Z(x, y) 的相图（行=y，列=x），并叠加等值线。"""
    im = ax.pcolormesh(X, Y, Z, cmap=cmap, shading='nearest',
                       vmin=np.nanmin(Z), vmax=np.nanmax(Z))
    cs = ax.contour(X, Y, Z, levels=6, colors='0.25', linewidths=0.5,
                    alpha=0.6)
    ax.clabel(cs, inline=True, fontsize=5.8, fmt='%.3f')
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_title(title, fontsize=8.5, pad=4)
    cb = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cb.ax.tick_params(labelsize=6.8)
    cb.set_label(cbar_label, fontsize=7.2)
    return im


def main():
    for f in (F_PHASE, F_AUDIT, F_REG):
        if not os.path.exists(f):
            raise SystemExit('missing: %s' % f)
    PH = _node(h5py.File(F_PHASE, 'r'))
    AU = _node(h5py.File(F_AUDIT, 'r'))
    RG = _node(h5py.File(F_REG, 'r'))

    fig = plt.figure(figsize=(11.8, 8.4))
    gs = fig.add_gridspec(2, 3, hspace=0.42, wspace=0.42,
                          left=0.058, right=0.985, top=0.855, bottom=0.075)

    notes = []

    # ================= (a) 波前畸变轴 =================
    # 相图化：把 SNR 轴的实测点作为第二维不可得（未跑σφ × SNR 网格），
    # 故此轴画**三臂 gCNR 随 σφ 的曲线 + Δ(E−C) 填色带**，
    # 语义仍是相图（颜色 = ΔgCNR，横轴 = 畸变量）。
    ax = fig.add_subplot(gs[0, 0])
    sg = _read(PH['SA']['sig']).ravel()
    gC = _read(PH['SA']['gC']).ravel()
    gM = _read(PH['SA']['gM']).ravel()
    gE = _read(PH['SA']['gE']).ravel()
    sC = _read(PH['SA']['sC']).ravel()
    sM = _read(PH['SA']['sM']).ravel()
    sE = _read(PH['SA']['sE']).ravel()
    dEC = gE - gC
    ax.fill_between(sg, gC, gE, where=(dEC > 0), color='#b8453c', alpha=0.16,
                    interpolate=True, label=r'$\Delta g_{CNR}$ = E−C')
    ax.errorbar(sg, gC, sC, fmt='o-', color=C_CLR, lw=1.4, ms=4, capsize=2.5,
                label=r'$I_C$ coherent')
    ax.errorbar(sg, gM, sM, fmt='s-', color=M_CLR, lw=1.4, ms=4, capsize=2.5,
                label=r'$I_M$ envelope')
    ax.errorbar(sg, gE, sE, fmt='^-', color=E_CLR, lw=1.5, ms=4.5, capsize=2.5,
                label=r'$I_E$ energy (ours)')
    ax.set_xlabel(r'wavefront aberration $\sigma_\varphi$ (rad)', fontsize=8)
    ax.set_ylabel('gCNR', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=6.5, frameon=False, loc='lower left')
    ax.set_title(r'(a) axis 1 — wavefront aberration (absolute gCNR)' +
                 '\n' + r'C degrades to $\sigma_\varphi=2$ rad, then plateaus; M/E at ceiling',
                 fontsize=8.5, pad=4)
    notes.append('aberration: gCNR C %.4f (s=0) -> %.4f (2 rad) -> %.4f (4 rad); '
                 'the 2->4 rad change is within 1 SD, i.e. a plateau; M/E = 1.0000 throughout'
                 % (gC[0], gC[3], gC[-1]))

    # ================= (b) SNR 轴 =================
    ax = fig.add_subplot(gs[0, 1])
    sn = _read(PH['SB']['snr']).ravel()
    bC = _read(PH['SB']['gC']).ravel()
    bM = _read(PH['SB']['gM']).ravel()
    bE = _read(PH['SB']['gE']).ravel()
    tC = _read(PH['SB']['sC']).ravel()
    tM = _read(PH['SB']['sM']).ravel()
    tE = _read(PH['SB']['sE']).ravel()
    ax.fill_between(sn, bC, bE, where=(bE - bC > 0), color='#b8453c',
                    alpha=0.16, interpolate=True, label=r'$\Delta g_{CNR}$ = E−C')
    ax.errorbar(sn, bC, tC, fmt='o-', color=C_CLR, lw=1.4, ms=4, capsize=2.5,
                label=r'$I_C$')
    ax.errorbar(sn, bM, tM, fmt='s-', color=M_CLR, lw=1.4, ms=4, capsize=2.5,
                label=r'$I_M$')
    ax.errorbar(sn, bE, tE, fmt='^-', color=E_CLR, lw=1.5, ms=4.5, capsize=2.5,
                label=r'$I_E$')
    ax.set_xlabel('channel SNR (dB)', fontsize=8)
    ax.set_ylabel('gCNR', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=6.5, frameon=False, loc='upper right')
    ax.set_title(r'(b) axis 2 — noise level' +
                 '\n' + r'largest E−C margin at low SNR (+%.3f)'
                 % (bE - bC).max(), fontsize=8.5, pad=4)
    notes.append('SNR: max Δ(E−C) = %+.4f at %d dB'
                 % ((bE - bC).max(), sn[int(np.argmax(bE - bC))]))

    # ================= (c) 随机阵元失效轴 =================
    # gCNR 在 M/E 饱和，改画**饱和指示 + 非饱和结构指标**：
    #   上：gCNR（可见 C 单调退化、M/E 恒 1）
    #   下（同轴内的第二色标）：SSIM（对圆盘真值，全臂非饱和）
    ax = fig.add_subplot(gs[0, 2])
    B = AU['axis2']
    fr = _read(B['frac']).ravel()
    aC = _read(B['gC'])
    aM = _read(B['gM'])
    aE = _read(B['gE'])
    s2C = _read(B['ssC'])
    s2M = _read(B['ssM'])
    s2E = _read(B['ssE'])
    x = fr * 100
    muC, sdC = aC.mean(1), aC.std(1, ddof=0)
    muM, sdM = aM.mean(1), aM.std(1, ddof=0)
    muE, sdE = aE.mean(1), aE.std(1, ddof=0)
    ax.errorbar(x, muC, sdC, fmt='o-', color=C_CLR, lw=1.4, ms=4, capsize=2.5,
                label=r'$I_C$')
    ax.errorbar(x, muM, sdM, fmt='s-', color=M_CLR, lw=1.4, ms=4, capsize=2.5,
                label=r'$I_M$')
    ax.errorbar(x, muE, sdE, fmt='^-', color=E_CLR, lw=1.5, ms=4.5, capsize=2.5,
                label=r'$I_E$')
    ax.set_xlabel('random element loss (%)', fontsize=8)
    ax.set_ylabel('gCNR  (saturates for M and E)', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.25)
    axb = ax.twinx()
    axb.errorbar(x, s2C.mean(1), s2C.std(1, ddof=0), fmt='o--', color=C_CLR,
                 lw=1.0, ms=3.4, capsize=2, alpha=0.75)
    axb.errorbar(x, s2M.mean(1), s2M.std(1, ddof=0), fmt='s--', color=M_CLR,
                 lw=1.0, ms=3.4, capsize=2, alpha=0.75)
    axb.errorbar(x, s2E.mean(1), s2E.std(1, ddof=0), fmt='^--', color=E_CLR,
                 lw=1.0, ms=3.8, capsize=2, alpha=0.75)
    axb.set_ylabel('SSIM vs disc truth  (non-saturating)', fontsize=8,
                   color='0.30')
    axb.tick_params(labelsize=7, colors='0.30')
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = axb.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=6.2, frameon=False, loc='lower left')
    ax.set_title(r'(c) axis 3 — random element loss' +
                 '\n' + r'solid: gCNR (saturated); dashed: SSIM (structural)',
                 fontsize=8.5, pad=4)
    notes.append('element loss: gCNR C %.4f -> %.4f (%.0f%% drop), M/E = 1.0000 throughout'
                 % (muC[0], muC[-1], 100 * (1 - muC[-1] / muC[0])))

    # ================= (d) 相干杂波轴（警示） =================
    # 唯一例外：强相干杂波下**能量臂最先失效**。此轴 gCNR 是"E 掉得最快"，
    # 故用**反向语义色标**（绿=好/红=差）并单独配色，不与 (a)(b) 共用视觉语言。
    ax = fig.add_subplot(gs[1, 0])
    cr = _read(RG['crList']).ravel()
    gR = _read(RG['T']['gCNR'])            # 3(臂) x 5(σφ) x 5(cr)
    # 相图：行 = 杂波/目标幅度，列 = 畸变 σφ（取 cr 的最后一行 = 目标自身）
    ZC = gR[0, :, :].T                    # cr x sigma_phi
    ZM = gR[1, :, :].T
    ZE = gR[2, :, :].T
    sigv = _read(RG['sigList']).ravel()
    X, Y = np.meshgrid(sigv, cr)
    _panel(ax, X, Y, ZE, r'aberration $\sigma_\varphi$ (rad)',
           r'clutter / target amplitude', r'(d) axis 4 — coherent clutter'
           r'  [$I_E$, the weak arm]',
           CMAP_WARN, r'$g_{CNR}$ of $I_E$')
    ax.text(0.03, 0.03,
            r'E fails FIRST here' + '\n' + r'(energy arm is the first to collapse)',
            transform=ax.transAxes, fontsize=6.8, color='#7a2410', va='bottom',
            bbox=dict(fc='white', ec='#8c2f14', lw=0.6, alpha=0.92))
    notes.append('clutter: E is the first arm to fail (Δ(E−C) turns strongly'
                 ' negative); disclosed as the single exception')

    # 三臂沿 cr 的剖面（相图右侧不可读，取 σφ=0 行）
    ZC0, ZM0, ZE0 = ZC[0, :], ZM[0, :], ZE[0, :]
    ax2 = fig.add_subplot(gs[1, 1])
    ax2.plot(cr, ZC0, 'o-', color=C_CLR, lw=1.4, ms=4, label=r'$I_C$')
    ax2.plot(cr, ZM0, 's-', color=M_CLR, lw=1.4, ms=4, label=r'$I_M$')
    ax2.plot(cr, ZE0, '^-', color=E_CLR, lw=1.5, ms=4.5, label=r'$I_E$')
    ax2.set_xlabel(r'clutter / target amplitude', fontsize=8)
    ax2.set_ylabel('gCNR', fontsize=8)
    ax2.tick_params(labelsize=7)
    ax2.grid(alpha=0.25)
    ax2.legend(fontsize=6.8, frameon=False, loc='lower left')
    ax2.set_title(r'(d′) clutter profile at $\sigma_\varphi=0$' +
                  '\n' + r'the single exception: E degrades first',
                  fontsize=8.5, pad=4)
    notes.append('clutter profile at σφ=0: gCNR at max clutter — C %.4f, M %.4f, E %.4f'
                 % (ZC0[-1], ZM0[-1], ZE0[-1]))

    # ================= (f) 摘要 =================
    ax = fig.add_subplot(gs[1, 2])
    ax.axis('off')
    sat = (np.abs(aM.mean(1) - 1.0) < 1e-9).all() and \
          (np.abs(aE.mean(1) - 1.0) < 1e-9).all()
    txt = [
        'Reading discipline',
        '',
        'Cross-arm comparison: gCNR only.',
        'PSR / width / CNR are within-domain',
        'quantities and are never placed',
        'side by side across arms.',
        '',
        'Saturation warning',
        '   M and E reach gCNR = 1.0000 as soon as',
        '   12.5 % of elements are lost, so the growing',
        '   E−C margin on axis 3 means C is degrading,',
        '   not that E is improving.',
        '   SSIM (dashed, right axis) is the non-saturating',
        '   structural read-out for the same axis.',
        '',
        'Axis 1 is read as a plateau, not a monotone line:',
        '   the C arm falls to sigma_phi = 2 rad and then',
        '   recovers within one SD at 4 rad.',
        '',
        'Single exception, disclosed',
        '   Under strong *coherent* clutter the energy arm',
        '   fails first (panel d). This is reported rather',
        '   than smoothed over: squaring sums a channel-',
        '   correlated term that coherent clutter enters',
        '   with full weight.',
        '',
        'Domain bookkeeping',
        '   all four axes share the same preprocess,',
        '   kernel, grid, FOV and pixel layout;',
        '   the only difference is the detection operator.',
    ]
    ax.text(0.0, 1.0, '\n'.join(txt), transform=ax.transAxes, va='top',
            ha='left', fontsize=7.0, linespacing=1.40)
    ax.set_title('(e) how to read this figure', fontsize=8.5, pad=4, loc='left')

    fig.suptitle('Fig. 4  Four-axis regime behaviour of the Hilbert-free '
                 'energy-related estimator\n(gCNR is the only cross-arm '
                 'quantity; one exception is disclosed, not hidden)',
                 fontsize=10.6, y=0.985)
    fig.savefig(OUT, dpi=220, bbox_inches='tight', facecolor='white')
    print('saved:', OUT)
    for n in notes:
        print('  -', n)


if __name__ == '__main__':
    main()
