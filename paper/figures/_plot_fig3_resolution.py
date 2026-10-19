# -*- coding: utf-8 -*-
"""
Fig. 3 —— 分辨率判定四联（三臂：C 相干反投影 / M 包络叠加 / E 声能域）

数据来源：results/study_resolution/study_resolution.mat
          （pipeline/study/pa_study_resolution.m，Nx=801，Nrep 次独立实现）

面板：
  (a) E1 单点PSF 的**域内归一化 dB 剖面** —— 说明 FWHM 差是"读数电平"而非分辨率
  (b) E1 三臂公平宽度（均值±SD）+ 指标条（gCNR 为跨臂唯一可比起）
  (c) E2 双点 Rayleigh 凹陷比 三臂（均值±SD）
  (d) E3 对比度阶梯 三臂（均值±SD）

口径纪律（MEMORY §1/§5）：
  · **禁据平方主张分辨率**。`FWHM(g^2) = W_{-3dB}(g)` 是严格恒等式：
    平方只是把读数电平从 -6 dB 换到 -3 dB（高斯为 1/sqrt(2)）。
    故 (a) 用**各臂各自域内归一化**的 dB 剖面，**不把sqrt(I_E) 与 I_M
    画在同一线性幅值轴上**——那是跨域比较，会被误读成"能量臂更宽=分辨率更低"。
  · 宽度只称"**表观宽度 / 公平宽度**"，且必须与 (c) 双点 Rayleigh 合看：
    分辨率结论落在 (c)，不落在宽度。
  · 跨臂只比 **gCNR**；CNR / PSR / 宽度是域内量，各自归一化后只做**同臂纵向**读数。
  · Nrep>=4，报 均值±SD（MEMORY §5.2）。
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

# pa_study_resolution 按 <Array>_<Regime> 命名输出目录（如 study_semicircle128_noise），
# 不是固定的 study_resolution/。这里按优先级探测，避免脚本与数据目录名耦合。
_CAND = [os.path.join(ROOT, 'results', d, 'study_resolution.mat')
         for d in ('study_semicircle128_noise', 'study_resolution')]
MAT = next((p for p in _CAND if os.path.exists(p)), _CAND[0])
OUT = os.path.join(ROOT, 'paper', 'figures', 'Fig03_resolution_sixpanel.png')

for cand in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf']:
    if os.path.exists(cand):
        font_manager.fontManager.addfont(cand)
        break
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 8.5

C_CLR, M_CLR, E_CLR = '#2f6f9f', '#c9a227', '#b8453c'
ARMS = [('C', C_CLR, r'$I_C$ (coherent)'),
        ('M', M_CLR, r'$I_M$ (envelope)'),
        ('E', E_CLR, r'$I_E$ (energy)')]


def _read(v):
    """读 h5py dataset并还原 MATLAB 的维序。

    MATLAB v7.3 把数组**反序**存进 HDF5（(Nrep,4) 存成 (4,Nrep)）。
    对 2D 数组：若 shape[0]==1 或 shape[1]==1 就是列向量，**直接ravel**；
    否则无法从 shape 单独判断方向，必须由调用方按已知语义转置
    （见脚本内np.transpose 的注释）。
    """
    a = np.array(v)
    if a.ndim == 2 and (a.shape[0] == 1 or a.shape[1] == 1):
        a = a.T
    return a


def _node(g):
    o = {}
    for k in g.keys():
        v = g[k]
        o[k] = _node(v) if isinstance(v, h5py.Group) else _read(v)
    return o


def _dbnorm(p, floor=1e-12):
    """域内归一化到 dB：各自峰值 -> 0 dB。跨臂比较时**只读形状，不读绝对电平**。"""
    p = np.maximum(np.asarray(p, float).ravel(), 0)
    pk = p.max()
    if pk <= 0:
        return np.full_like(p, -np.inf)
    return 20.0 * np.log10(np.maximum(p / pk, floor))


def _metric_table(v, ncol=4):
    """把 4 列指标矩阵取成"每行一个 replicate、每列一个指标"。

    MATLAB 存 (Nrep, ncol)；h5py 读成 (ncol, Nrep)。方阵时无法从形状判断，
    改用**语义**定位：gCNR ∈ [0,1] 且 CNR/PSR/DR 通常远大于 1，
    因此"每一行都落在 [0,1]"的那一行就是 gCNR 行。
    若仍无法判定，则按 MATLAB 原序（即不转置）返回，并交给调用方报错。
    """
    a = np.array(v)
    if a.shape[0] == ncol and a.shape[1] != ncol:
        a = a.T                      # 明确的 (ncol, Nrep) ->转正
    elif a.shape[0] == ncol and a.shape[1] == ncol:
        in01 = np.all((a >= 0) & (a <= 1), axis=1)
        if in01.sum() == 1 and not in01.all():
            a = a.T                  # 方阵：靠 gCNR 行定位方向
    return a


def main():
    if not os.path.exists(MAT):
        raise SystemExit('missing: %s' % MAT)
    D = _node(h5py.File(MAT, 'r'))

    W = D['W']
    Nr = int(_read(W['Nrep']).ravel()[0])
    ax = _read(D['R1']['ax']).ravel()
    E2, E3 = D['E2'], D['E3']

    fC = _read(W['fwhmC']).ravel()
    fM = _read(W['fwhmM']).ravel()
    fE = _read(W['fwhmE']).ravel()
    w3 = _read(W['w3env']).ravel()
    fs_ = _read(W['fwhmSqrtE']).ravel()
    # gCNR 在 4 列指标里是第 2 列（[CNR gCNR PSR DR]），用语义定位避免方向歧义
    gC = _metric_table(W['MC'])[:, 1]
    gM = _metric_table(W['MM'])[:, 1]
    gE = _metric_table(W['ME'])[:, 1]
    assert np.all((gC >= 0) & (gC <= 1)), 'gCNR out of [0,1]: column order wrong'

    fig = plt.figure(figsize=(11.6, 7.6))
    gs = fig.add_gridspec(2, 3, hspace=0.46, wspace=0.30,
                          left=0.062, right=0.985, top=0.855, bottom=0.085)

    # ---------------- (a) 域内归一化 dB 剖面 ----------------
    ax_ = fig.add_subplot(gs[0, 0])
    m = np.abs(ax) <= 3.0
    # sqrt(I_E) 是把能量读回幅度域的**同臂纵向**换算，不是把 E 与 M 放在同一物理尺度
    ax_.plot(ax[m], _dbnorm(_read(D['R1']['profC']).ravel()[m]), '-',
             color=C_CLR, lw=1.3, label=r'$I_C$')
    ax_.plot(ax[m], _dbnorm(_read(D['R1']['profM']).ravel()[m]), '-',
             color=M_CLR, lw=1.3, label=r'$I_M$')
    ax_.plot(ax[m], _dbnorm(_read(D['R1']['profEa']).ravel()[m]), '--',
             color=E_CLR, lw=1.2, label=r'$\sqrt{I_E}$ (same arm, read back)')
    ax_.axhline(-3, color='0.55', ls=':', lw=0.9)
    ax_.axhline(-6, color='0.55', ls=':', lw=0.9)
    ax_.text(2.9, -2.6, '-3 dB', fontsize=6.6, color='0.35', ha='right')
    ax_.text(2.9, -5.6, '-6 dB', fontsize=6.6, color='0.35', ha='right')
    ax_.set_xlabel('x (mm)', fontsize=8)
    ax_.set_ylabel('within-arm normalised level (dB)', fontsize=8)
    ax_.set_ylim(-32, 1.5)
    ax_.tick_params(labelsize=7)
    ax_.grid(alpha=0.25)
    ax_.legend(fontsize=6.6, frameon=False, loc='lower left')
    ax_.set_title(r'(a) single-point PSF, each arm normalised in its own domain' +
                  '\n' + r'$FWHM(g^2)=W_{-3\,\mathrm{dB}}(g)$: squaring moves the'
                  '\n' + r'reading level $-6\to-3$ dB, not the resolution',
                  fontsize=8.3, pad=4)
    # ---------------- (b) 公平宽度 + gCNR ----------------
    ax_ = fig.add_subplot(gs[0, 1])
    xs = np.arange(3)
    vals = [fC, fM, fE]
    mu = [v.mean() for v in vals]
    sd = [v.std(ddof=0) for v in vals]
    ax_.bar(xs, mu, 0.56, yerr=sd, capsize=3,
            color=[C_CLR, M_CLR, E_CLR], edgecolor='none')
    # env 的 -3 dB 宽度：与 FWHM(I_E) 对照，说明"同一电平"读数
    ax_.plot([2], [w3.mean()], marker='D', ms=5, mfc='white',
             mec=E_CLR, mew=1.4, ls='none', zorder=5)
    ax_.errorbar([2], [w3.mean()], yerr=[w3.std(ddof=0)], fmt='none',
                 ecolor=E_CLR, elinewidth=1.0, capsize=3, alpha=0.75, zorder=4)
    for i, (m_, s_) in enumerate(zip(mu, sd)):
        ax_.text(i, m_ + s_ + 0.03, '%.3f' % m_, ha='center', fontsize=7.2)
    ax_.set_xticks(xs)
    ax_.set_xticklabels([r'$I_C$', r'$I_M$', r'$I_E$'], fontsize=8.5)
    ax_.set_ylabel('apparent width (mm), mean±SD', fontsize=8)
    ax_.set_ylim(0, max(np.array(mu) + np.array(sd)) * 1.28)
    ax_.tick_params(labelsize=7)
    ax_.grid(axis='y', alpha=0.25)
    ax_.legend(handles=[
        plt.Line2D([], [], marker='s', ls='none', mfc='0.6', mec='none',
                   label='apparent width (FWHM)'),
        plt.Line2D([], [], marker='D', ls='none', mfc='white', mec=E_CLR,
                   mew=1.4, label=r'env $-3$ dB width')],
        fontsize=6.6, frameon=False, loc='upper left')
    ax_.set_title(r'(b) E1 apparent width and the cross-arm metric' +
                  '\n' + r'gCNR: C %.4f±%.4f, M %.4f±%.4f, E %.4f±%.4f'
                  % (gC.mean(), gC.std(ddof=0), gM.mean(), gM.std(ddof=0),
                     gE.mean(), gE.std(ddof=0)) +
                  '\n' + r'$\Delta gCNR$: E−C %+.4f, E−M %+.4f  (Nrep=%d)'
                  % (gE.mean() - gC.mean(), gE.mean() - gM.mean(), Nr),
                  fontsize=8.3, pad=4)

    # ---------------- (c) 双点 Rayleigh ----------------
    ax_ = fig.add_subplot(gs[0, 2])
    d_mm = _read(E2['d_mm']).ravel()
    # MATLAB 存 (Nrep, arm, nD)；h5py 按**反序**维读出 (nD, arm, Nrep)
    DIP = np.transpose(_read(E2['dip']), (2, 1, 0))       # -> Nrep x3 x nD
    ax_.errorbar(d_mm, DIP[:, 0, :].mean(0), DIP[:, 0, :].std(0, ddof=0),
                 fmt='o-', color=C_CLR, lw=1.3, ms=3.6, capsize=2.5,
                 label=r'$I_C$')
    ax_.errorbar(d_mm, DIP[:, 1, :].mean(0), DIP[:, 1, :].std(0, ddof=0),
                 fmt='s-', color=M_CLR, lw=1.3, ms=3.6, capsize=2.5,
                 label=r'$I_M$')
    ax_.errorbar(d_mm, DIP[:, 2, :].mean(0), DIP[:, 2, :].std(0, ddof=0),
                 fmt='^-', color=E_CLR, lw=1.3, ms=4.0, capsize=2.5,
                 label=r'$I_E$')
    ax_.axhline(0.05, color='k', ls='--', lw=0.9)
    ax_.text(d_mm[-1], 0.062, 'resolved thr. 0.05', fontsize=6.6, ha='right')
    ax_.set_xlabel('two-point separation (mm)', fontsize=8)
    ax_.set_ylabel('Rayleigh dip ratio', fontsize=8)
    ax_.tick_params(labelsize=7)
    ax_.grid(alpha=0.25)
    ax_.legend(fontsize=6.8, frameon=False, loc='center right')
    # 判决阈值（均值曲线 dip>0.05 的最小间距）
    def min_sep(dd, dip):
        idx = np.where(np.asarray(dip) > 0.05)[0]
        return dd[idx[0]] if len(idx) else np.nan
    sepC = min_sep(d_mm, DIP[:, 0, :].mean(0))
    sepM = min_sep(d_mm, DIP[:, 1, :].mean(0))
    sepE = min_sep(d_mm, DIP[:, 2, :].mean(0))
    ax_.set_title(r'(c) E2 two-point Rayleigh, mean±SD (Nrep=%d)' % Nr +
                  '\n' + r'min. resolved sep.: C %.2f, M %.2f, E %.2f mm'
                  % (sepC, sepM, sepE), fontsize=8.3, pad=4)

    # ---------------- (d) 对比度阶梯 ----------------
    ax_ = fig.add_subplot(gs[1, 0])
    eps = _read(E3['eps']).ravel()
    RAT = np.transpose(_read(E3['ratio']), (2, 1, 0))   # 同上 -> Nrep x 3 x nEp
    o = np.argsort(eps)
    for j, (_, c, lab) in enumerate(ARMS):
        mu = RAT[:, j, :].mean(0)[o]
        sd = RAT[:, j, :].std(0, ddof=0)[o]
        ax_.errorbar(eps[o], mu, sd, fmt='o-', color=c, lw=1.3, ms=3.6,
                     capsize=2.5, label=lab)
    ax_.plot(eps, eps, 'k--', lw=0.9, label='ideal (read-out = $A$)')
    ax_.set_xscale('log'); ax_.set_yscale('log')
    ax_.set_xlabel(r'true amplitude ratio $A_{weak}/A_{strong}$', fontsize=8)
    ax_.set_ylabel('measured read-out ratio', fontsize=8)
    ax_.tick_params(labelsize=7)
    ax_.grid(alpha=0.25, which='both')
    ax_.legend(fontsize=6.6, frameon=False, loc='upper left')
    fidE = RAT[:, 2, :].mean(0) / eps
    ax_.set_title(r'(d) E3 contrast ladder, mean±SD' +
                  '\n' + r'energy arm fidelity $A_{read}/A_{true}$ = %.2f–%.2f'
                  % (fidE.min(), fidE.max()), fontsize=8.3, pad=4)

    # ---------------- (e) 三臂单点图像 ----------------
    ax_ = fig.add_subplot(gs[1, 1])
    vmax = np.percentile(np.maximum(_read(D['R1']['IE']), 0), 99.5)
    im = ax_.imshow(np.maximum(_read(D['R1']['IE']), 0), origin='lower',
                    cmap='gray', vmin=0, vmax=vmax, extent=[ax[0], ax[-1], ax[0], ax[-1]])
    cb = fig.colorbar(im, ax=ax_, fraction=0.046, pad=0.03)
    cb.ax.tick_params(labelsize=6.5)
    cb.set_label(r'$I_E$ (a.u.)', fontsize=7)
    ax_.set_xlabel('x (mm)', fontsize=8)
    ax_.set_ylabel('y (mm)', fontsize=8)
    ax_.tick_params(labelsize=7)
    ax_.set_title(r'(e) single-point image, arm E ($N_{\rm rep}$=1 shown)' +
                  '\n' + r'same grid / kernel / window as C and M', fontsize=8.3, pad=4)

    # ---------------- (f) 判定摘要 ----------------
    ax_ = fig.add_subplot(gs[1, 2])
    ax_.axis('off')
    rel1 = 100 * abs(fE.mean() - w3.mean()) / max(w3.mean(), 1e-12)
    rel2 = 100 * abs(fs_.mean() - fM.mean()) / max(fM.mean(), 1e-12)
    fidM = RAT[:, 1, :].mean(0) / eps
    fidC = RAT[:, 0, :].mean(0) / eps
    txt = [
        'E1 apparent widths (mm, mean±SD, Nrep=%d)' % Nr,
        '   FWHM(I_C)          %7.4f ± %.4f' % (fC.mean(), fC.std(ddof=0)),
        '   FWHM(I_M)          %7.4f ± %.4f' % (fM.mean(), fM.std(ddof=0)),
        '   FWHM(I_E)          %7.4f ± %.4f' % (fE.mean(), fE.std(ddof=0)),
        '   env −3 dB width    %7.4f ± %.4f' % (w3.mean(), w3.std(ddof=0)),
        '   FWHM(sqrt(I_E))    %7.4f ± %.4f' % (fs_.mean(), fs_.std(ddof=0)),
        '',
        'H1  identity check',
        '   |FWHM(I_E) - w(-3 dB)| / w(-3 dB) = %5.2f %%' % rel1,
        '   |FWHM(sqrt I_E) - FWHM(I_M)| / FWHM(I_M) = %5.2f %%' % rel2,
        '   => the width gap is a reading-level effect,',
        '      NOT a resolution gain.',
        '',
        'H2  two-point Rayleigh (dip > 0.05)',
        '   min resolved sep.   C %5.2f   M %5.2f   E %5.2f mm' % (sepC, sepM, sepE),
        '',
        'E3 fidelity  A_read / A_true',
        '   C %.2f–%.2f    M %.2f–%.2f    E %.2f–%.2f'
        % (fidC.min(), fidC.max(), fidM.min(), fidM.max(), fidE.min(), fidE.max()),
        '',
        'Cross-arm metric (the only admissible one)',
        '   gCNR  C %.4f   M %.4f   E %.4f' % (gC.mean(), gM.mean(), gE.mean()),
        '   Δ(E−C) = %+.4f    Δ(E−M) = %+.4f'
        % (gE.mean() - gC.mean(), gE.mean() - gM.mean()),
    ]
    ax_.text(0.0, 1.0, '\n'.join(txt), transform=ax_.transAxes,
             va='top', ha='left', fontsize=7.0, family='DejaVu Sans Mono',
             linespacing=1.42)
    ax_.set_title('(f) verdict summary', fontsize=8.5, pad=4, loc='left')

    fig.suptitle('Fig. 3  Resolution adjudication: the width gap is a reading-level '
                 'artefact,\nnot a resolution gain; only gCNR is comparable '
                 'across arms', fontsize=10.6, y=0.985)
    fig.savefig(OUT, dpi=220, bbox_inches='tight', facecolor='white')
    print('saved:', OUT)
    print('  Nrep=%d  FWHM C=%.4f M=%.4f E=%.4f  env-3dB=%.4f'
          % (Nr, fC.mean(), fM.mean(), fE.mean(), w3.mean()))
    print('  gCNR C=%.4f M=%.4f E=%.4f' % (gC.mean(), gM.mean(), gE.mean()))
    print('  min resolved sep: C=%.2f M=%.2f E=%.2f mm' % (sepC, sepM, sepE))


if __name__ == '__main__':
    main()
