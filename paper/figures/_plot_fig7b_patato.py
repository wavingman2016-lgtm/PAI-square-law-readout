# -*- coding: utf-8 -*-
"""
Figure 7b — PATATO in-vivo mouse: unified-pipeline geometric check, six panels.

Panels: C (coherent back-projection), M (envelope stacking), E via the Hilbert
path, E Hilbert-free (this work), I_BS = I_C^2 (image-domain square), and the
provider's official reference reconstruction.

数据来源
  results/study_patato/patato_images.mat   fields coh, env, env2, sqlaw, sq, IBS
  results/study_patato/patato_check.mat    metrics/{names,CNR,gCNR}, align/{fov_mm,tf,corr_env}
  data_ext/invivo_oe.hdf5                  '/recons/Reference Backprojection/0'
                                           (76, 10, 1, 333, 333) -> 76-frame mean,
                                           wavelength 0, resampled to our grid and
                                           transposed per align/tf (see pa_patato_check.m)

口径：本图披露**边界情形** —— 在该宽带有限视角在体数据上，
      E 对包络叠加臂 M 是负的（flag），对相干臂 C 仍是正的。
"""
import os
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..')).replace(os.sep, '/')

IMATE = os.path.join(ROOT, 'results', 'study_patato', 'patato_images.mat')
CHK = os.path.join(ROOT, 'results', 'study_patato', 'patato_check.mat')
H5 = os.path.join(ROOT, 'data_ext', 'invivo_oe.hdf5')
OUT = os.path.join(ROOT, 'paper', 'figures', 'Fig07b_patato_three_arms.png')

plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 8.6

PANELS = [
    ('coh',   'C  coherent back-projection  $|\\sum_m z_m|$'),
    ('env',   'M  envelope stacking  $\\sum_m |z_m|$'),
    ('env2',  'E  energy domain (Hilbert path)'),
    ('sqlaw', 'E  energy domain (Hilbert-free, this work)'),
    ('IBS',   '$I_{BS}=I_C^{2}$  (image-domain square)'),
    ('ref',   'official reference reconstruction'),
]


def rebuild_reference(gridx, gridy, fov_mm, tf_name, env_img=None):
    """按 pa_patato_check.m 的对齐逻辑从 HDF5 复建官方参考图。

    MATLAB 侧：ii = grid.x/px + c0 + 1；[XX,YY]=meshgrid(ii,ii)；
              rImg = interp2(ref2, XX, YY)  =>  rImg(i,j) = ref2(ii(j), ii(i))
    复建后自检 corr(rImg, env) 是否等于归档的 align/corr_env。
    """
    from scipy.interpolate import RegularGridInterpolator
    with h5py.File(H5, 'r') as f:
        arr = np.asarray(f['recons/Reference Backprojection/0'][...], dtype=np.float64)
    ref2 = arr.mean(axis=0)[0, 0, :, :]          # 76-frame mean, wavelength 0
    n = ref2.shape[0]
    c0 = (n - 1) / 2.0
    px = fov_mm / (n - 1)
    idx = gridx / px + c0
    rgi = RegularGridInterpolator((np.arange(n), np.arange(n)), ref2,
                                  method='linear', bounds_error=False, fill_value=0.0)
    XX, YY = np.meshgrid(idx, idx)               # MATLAB meshgrid
    A = rgi(np.column_stack([YY.ravel(), XX.ravel()])).reshape(len(idx), len(idx))
    rImg = A                                     # rImg(i,j) = ref2(ii(i), ii(j))
    if tf_name == 'transpose':
        rImg = rImg.T
    elif tf_name == 'flipud':
        rImg = rImg[::-1, :]
    elif tf_name == 'fliplr':
        rImg = rImg[:, ::-1]
    if env_img is not None:
        a = rImg.ravel() - rImg.mean(); b = env_img.ravel() - env_img.mean()
        cc = float(a @ b / np.sqrt((a @ a) * (b @ b)))
        print('  [check] rebuilt reference vs env corr = %+.4f' % cc)
    return rImg


def main():
    with h5py.File(IMATE, 'r') as f:
        imgs = {k: np.asarray(f[k][...], dtype=np.float64) for k, _ in PANELS if k != 'ref'}
    with h5py.File(CHK, 'r') as f:
        names = []
        for r in np.asarray(f['metrics/names']).ravel():
            ds = f[r]
            names.append(''.join(chr(c) for c in
                                 np.asarray(ds).ravel().astype(np.uint16)))
        CNR = np.asarray(f['metrics/CNR']).ravel()
        gCNR = np.asarray(f['metrics/gCNR']).ravel()
        fov = float(np.asarray(f['align/fov_mm']).ravel()[0])
        tf = ''.join(chr(c) for c in np.asarray(f['align/tf']).ravel().astype(np.uint16))
        corr = float(np.asarray(f['align/corr_env']).ravel()[0])
        gridx = np.asarray(f['grid/x']).ravel()
        gridy = np.asarray(f['grid/y']).ravel()
    met = {n: (CNR[i], gCNR[i]) for i, n in enumerate(names)}

    imgs['ref'] = rebuild_reference(gridx, gridy, fov, tf, env_img=imgs['env'])

    ext = [gridx[0], gridx[-1], gridy[0], gridy[-1]]
    fig, axes = plt.subplots(2, 3, figsize=(11.6, 7.6))
    fig.subplots_adjust(left=0.055, right=0.945, top=0.845, bottom=0.105,
                        wspace=0.34, hspace=0.42)

    for k, (key, lab) in enumerate(PANELS):
        ax = axes.flat[k]
        im = imgs[key]
        if key == 'ref':
            lo, hi = np.percentile(im, 2), np.percentile(im, 99.8)
        else:
            lo, hi = 0.0, 1.0
        pc = ax.imshow(im, origin='lower', extent=ext, cmap='hot',
                       vmin=lo, vmax=hi, aspect='equal', interpolation='nearest')
        cb = fig.colorbar(pc, ax=ax, fraction=0.046, pad=0.03)
        cb.ax.tick_params(labelsize=6.4)
        if key == 'ref':
            cb.set_label('official recon. (a.u.)', fontsize=6.8)
        ttl = lab
        j = names.index(key) if key in names else None
        if j is not None:
            ttl = '%s\nCNR %.2f  |  gCNR %.3f' % (lab, CNR[j], gCNR[j])
        ax.set_title(ttl, fontsize=8.4, fontweight='bold', pad=4)
        ax.set_xlabel('x (mm)', fontsize=8.0)
        ax.set_ylabel('y (mm)', fontsize=8.0)
        ax.tick_params(labelsize=6.8)

    dEC = met['sqlaw'][1] - met['coh'][1]
    dEM = met['sqlaw'][1] - met['env'][1]
    gC = met['coh'][1]
    fig.text(0.5, 0.905,
             'PATATO in-vivo mouse - unified-pipeline geometric check '
             '(official FOV %.1f mm, coordinate %s, corr = %+.4f)'
             % (fov, tf, corr), ha='center', va='center',
             fontsize=10.4, fontweight='bold')
    fig.text(0.5, 0.025,
             '$\\Delta$gCNR(E$-$C) = %+.3f   |   $\\Delta$gCNR(E$-$M) = %+.3f   '
             '(flagged boundary case: the energy arm stays above coherent '
             'back-projection but not above envelope stacking)' % (dEC, dEM),
             ha='center', va='center', fontsize=8.4, color='0.2')
    fig.suptitle('', y=0.99)
    fig.savefig(OUT, dpi=220, bbox_inches='tight', facecolor='white')
    print('saved:', OUT)
    print('gCNR: C=%.4f M=%.4f E=%.4f | dEC=%+.4f dEM=%+.4f' %
          (gC, met['env'][1], met['sqlaw'][1], dEC, dEM))


if __name__ == '__main__':
    main()
