# -*- coding: utf-8 -*-
"""
Figure 7 — external in-vivo tissue datasets, qualitative overview.

Four panels:
    (a) 3D-PACT rat brain in vivo           MIP, 180 x 250 x 120
    (b) 3D-PACT human breast in vivo        MIP, 800 x 800 x 305
    (c) PATATO mouse in vivo - this work    envelope reconstruction (arm M, D1)
    (d) PATATO mouse in vivo - official     provider reference reconstruction

口径：面板 (a)(b) 只有官方重建体、没有原始通道数据 ⇒ 一律**定性展示**
      （qualitative display only），不报任何指标。
      面板 (c)(d) 的定量核验见 Figure 7b。

数据来源
  data_ext/3D-PACT/Fig. 2/rat_brain_image_raw.mat        key image_comp
  data_ext/3D-PACT/Fig. 4/left_breast_image_raw.mat      key image_comp
  results/study_patato/patato_images.mat                 key env
  data_ext/invivo_oe.hdf5 + results/study_patato/patato_check.mat  (official ref)
"""
import os
import numpy as np
import h5py
import scipy.io as sio
from scipy.interpolate import RegularGridInterpolator
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..')).replace(os.sep, '/')

PACT = os.path.join(ROOT, 'data_ext', '3D-PACT')
OUT = os.path.join(ROOT, 'paper', 'figures', 'Fig07_invivo_tissue.png')

plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 8.4

CMAP = matplotlib.colormaps['inferno']


def _mip(vol, keep=(2, 0, 1)):
    return np.transpose(vol, keep).max(axis=2)


def _win(img, lo_p=50.0, hi_p=99.7):
    lo = float(np.percentile(img, lo_p)); hi = float(np.percentile(img, hi_p))
    if hi <= lo:
        hi = lo + 1e-12
    return lo, hi


def official_reference():
    """复建 PATATO 官方参考重建（与 Fig. 7b 同一对齐流程）。"""
    with h5py.File(os.path.join(ROOT, 'results', 'study_patato',
                                'patato_check.mat'), 'r') as f:
        fov = float(np.asarray(f['align/fov_mm']).ravel()[0])
        tf = ''.join(chr(c) for c in np.asarray(f['align/tf']).ravel().astype(np.uint16))
        gx = np.asarray(f['grid/x']).ravel()
    with h5py.File(os.path.join(ROOT, 'data_ext', 'invivo_oe.hdf5'), 'r') as f:
        arr = np.asarray(f['recons/Reference Backprojection/0'][...], dtype=np.float64)
    ref2 = arr.mean(axis=0)[0, 0, :, :]
    n = ref2.shape[0]; c0 = (n - 1) / 2.0; px = fov / (n - 1)
    idx = gx / px + c0
    rgi = RegularGridInterpolator((np.arange(n), np.arange(n)), ref2,
                                  method='linear', bounds_error=False, fill_value=0.0)
    XX, YY = np.meshgrid(idx, idx)
    A = rgi(np.column_stack([YY.ravel(), XX.ravel()])).reshape(len(idx), len(idx))
    return A.T if tf == 'transpose' else A


def main():
    rat = np.asarray(sio.loadmat(os.path.join(PACT, 'Fig. 2',
                     'rat_brain_image_raw.mat'))['image_comp'], dtype=float)
    brs = np.asarray(sio.loadmat(os.path.join(PACT, 'Fig. 4',
                     'left_breast_image_raw.mat'))['image_comp'], dtype=float)
    with h5py.File(os.path.join(ROOT, 'results', 'study_patato',
                                'patato_images.mat'), 'r') as f:
        env = np.asarray(f['env'][...], dtype=float)
    ref = official_reference()
    print('shapes: rat %s  breast %s  env %s  ref %s'
          % (rat.shape, brs.shape, env.shape, ref.shape))

    panels = [
        ('(a) 3D-PACT rat brain in vivo - MIP',
         _mip(rat), 'volume 180 x 250 x 120\nqualitative display only', False),
        ('(b) 3D-PACT human breast in vivo - MIP',
         _mip(brs), 'volume 800 x 800 x 305\nqualitative display only', False),
        ('(c) PATATO mouse in vivo - this work (envelope, arm M, D1)',
         env, 'FOV 30 mm, unified pipeline', True),
        ('(d) PATATO mouse in vivo - official reference reconstruction',
         ref, 'provider reconstruction, 76-frame mean', True),
    ]

    fig, axes = plt.subplots(1, 4, figsize=(15.0, 4.9))
    fig.subplots_adjust(left=0.030, right=0.975, top=0.775, bottom=0.155,
                        wspace=0.30)
    for ax, (ttl, img, note, is_image) in zip(axes, panels):
        lo, hi = _win(img)
        pc = ax.imshow(img, origin='lower', cmap=CMAP, vmin=lo, vmax=hi,
                       aspect='auto', interpolation='nearest')
        cb = fig.colorbar(pc, ax=ax, fraction=0.043, pad=0.025)
        cb.ax.tick_params(labelsize=6.2)
        cb.set_label('MIP (a.u.)' if not is_image else 'intensity (a.u.)',
                     fontsize=6.8)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(ttl, fontsize=8.0, pad=5)
        ax.text(0.0, -0.045, note + '\nwindow: WL = %.3g, WW = %.3g (p50-p99.7)'
                % (lo, hi - lo), transform=ax.transAxes, fontsize=6.4,
                va='top', color='0.3')

    fig.text(0.5, 0.905,
             'External in-vivo tissue datasets - qualitative display only',
             ha='center', va='center', fontsize=10.8, fontweight='bold')
    fig.text(0.5, 0.048,
             'panels (a) and (b) are reconstructed volumes supplied by the '
             'authors: no raw channel data, so no three-arm comparison and no '
             'metric is claimed;   panels (c) and (d) are quantified in '
             'Figure 7b', ha='center', va='center', fontsize=8.2, color='0.25')
    fig.savefig(OUT, dpi=210, bbox_inches='tight', facecolor='white')
    print('saved:', OUT)


if __name__ == '__main__':
    main()
