# -*- coding: utf-8 -*-
"""
pa_audit_arms.py - 三臂（C 传统相干 / M 包络叠加 / E 本文能量）证据总账

目的：用**统一口径**重算所有已跑数据的三臂指标，把「E 优于 C」的证据系统性挖出来。

两套口径（各自内部自洽，两套都报）：
  口径 A（2D 病灶 ROI，主口径）：in = 半径 0.5mm 圆盘；out = 3~6mm 圆环
  口径 B（1D 中心行剖面，辅口径）：in = |x|<=0.9mm；out = 0.25~0.45 * 半跨度

跨臂合法性：
  gCNR  对任意单调映射不变 -> 跨臂（含跨域）**唯一合法**的对比指标
  CNR/PSR/DR  依赖「域」，只有**同域**可比；跨域比较一律标 [跨域不可比]
  宽度  统一还原到幅度域 -6dB（E 取 sqrt(I_E)）—— 公平口径
"""
import h5py, numpy as np, os

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', 'results')).replace(os.sep, '/')


# ---------------------------------------------------------------- 工具
def gcnr(a, b, nb=65):
    a = np.asarray(a, float).ravel(); b = np.asarray(b, float).ravel()
    if a.size == 0 or b.size == 0: return np.nan
    lo, hi = min(a.min(), b.min()), max(a.max(), b.max())
    if hi <= lo: return 1.0
    e = np.linspace(lo, hi, nb)
    pa, _ = np.histogram(a, e); pb, _ = np.histogram(b, e)
    pa = pa / pa.sum(); pb = pb / pb.sum()
    return 1.0 - np.minimum(pa, pb).sum()

def cnr(a, b):
    a = np.asarray(a, float).ravel(); b = np.asarray(b, float).ravel()
    if b.size < 2: return np.nan
    return (a.mean() - b.mean()) / (b.std() + 1e-16)

def psr(img, b):
    b = np.asarray(b, float).ravel()
    return img.max() / (b.max() + 1e-16) if b.size else np.nan

def dr(img):
    return 20 * np.log10((img.max() + 1e-16) / (np.median(img) + 1e-16))

def conc(img, mask):
    return img[mask].sum() / (img.sum() + 1e-16)

def width(ax, y, lvl):
    ax = np.asarray(ax, float).ravel(); y = np.asarray(y, float).ravel()
    pk = y.max()
    if pk <= 0: return np.nan
    thr = lvl * pk; n = len(y); i0 = int(np.argmax(y))
    L = i0
    while L > 0 and y[L] > thr: L -= 1
    R = i0
    while R < n - 1 and y[R] > thr: R += 1
    xl = ax[0] if y[L] > thr else ax[L] + (thr - y[L]) * (ax[L+1] - ax[L]) / (y[L+1] - y[L])
    xr = ax[-1] if y[R] > thr else ax[R-1] + (thr - y[R-1]) * (ax[R] - ax[R-1]) / (y[R] - y[R-1])
    return abs(xr - xl)

def roi2d(nx, fov_mm, r_in=0.5, r_out=(3.0, 6.0), cx=0.0, cy=0.0):
    """返回 in/out 布尔掩膜（行=y，列=x）"""
    dx = fov_mm / (nx - 1)
    q = (np.arange(nx) - nx / 2) * dx
    X, Y = np.meshgrid(q, q)
    R = np.hypot(X - cx, Y - cy)
    return (R <= r_in), (R >= r_out[0]) & (R <= r_out[1])

# ---------------------------------------------------------------- 读 2D 图
def get2d(mat, name):
    """h5py 读 MATLAB 2D 数组 -> 转置回 row=y, col=x"""
    a = np.array(mat[name])
    while a.ndim > 2: a = a[0]
    return a.T.astype(float)

# ================================================================ 1. 受控仿真四组（有 2D 图）
print("#" * 96)
print("# 一、受控仿真四组（2D 病灶 ROI 口径，主口径）")
print("#" * 96)
print(f"{'case':<26}{'arm':<5}{'gCNR':>9}{'CNR':>9}{'PSR':>9}{'DR':>9}{'Conc':>9}{'w(-6dB)':>10}{'域':>8}")
print("-" * 96)

sim_cases = [
    ('study_semicircle128_noise',   'semicircle128 noise'),
    ('study_ring256_noise',         'ring256 noise'),
    ('study_semicircle128_clutter', 'semicircle128 clutter'),
    ('study_ring256_clutter',       'ring256 clutter'),
]

sim_summary = {}
for d, label in sim_cases:
    p = os.path.join(ROOT, d, 'study_resolution.mat')
    if not os.path.exists(p):
        print(f"{label:<26}[缺] {p}"); continue
    f = h5py.File(p, 'r')
    r1 = f['R1']
    ax = np.squeeze(np.array(r1['ax'])).astype(float)
    nx = int(r1['IC'].shape[0]) if isinstance(r1['IC'], h5py.Dataset) else 801
    fov = 40.0
    IN, OUT = roi2d(nx, fov)
    imgs = {'C': get2d(r1, 'IC'), 'M': get2d(r1, 'IM'), 'E': get2d(r1, 'IE')}
    profs = {
        'C': np.squeeze(np.array(r1['profC'])).astype(float),
        'M': np.squeeze(np.array(r1['profM'])).astype(float),
        'E': np.squeeze(np.array(r1['profE'])).astype(float),
    }
    dom = {'C': '声压幅值', 'M': '声压幅值', 'E': '声能密度'}
    row = {}
    for arm in ['C', 'M', 'E']:
        img = imgs[arm]
        a, b = img[IN], img[OUT]
        prof = profs[arm]
        prof_amp = np.sqrt(np.maximum(prof, 0)) if arm == 'E' else prof
        w = width(ax, prof_amp, 0.5)
        g, c = gcnr(a, b), cnr(a, b)
        print(f"{label:<26}{arm:<5}{g:>9.4f}{c:>9.2f}{psr(img,b):>9.2f}{dr(img):>9.2f}{conc(img,IN):>9.4f}{w:>10.4f}{dom[arm]:>8}")
        row[arm] = dict(gCNR=g, CNR=c, w=w)
    print(f"{'':<26}{'Δ(E-C)':<5}{row['E']['gCNR']-row['C']['gCNR']:>+9.4f}{'':>9}{'':>9}{'':>9}{'':>9}{row['E']['w']/row['C']['w']:>9.2f}x")
    print(f"{'':<26}{'Δ(E-M)':<5}{row['E']['gCNR']-row['M']['gCNR']:>+9.4f}{'':>9}{'':>9}{'':>9}{'':>9}{row['E']['w']/row['M']['w']:>9.2f}x")
    print("-" * 96)
    sim_summary[label] = row
    f.close()

# ================================================================ 2. 自有数据 W1/W2（有 2D 图）
print()
print("#" * 96)
print("# 二、自有钨丝数据（2D 病灶 ROI 口径）")
print("#" * 96)
print(f"{'case':<26}{'arm':<5}{'gCNR':>9}{'CNR':>9}{'PSR':>9}{'DR':>9}{'Conc':>9}{'w(-6dB)':>10}{'域':>8}")
print("-" * 96)

wire_cases = [('W1_single', 'W1', 40.0), ('W2_double', 'W2', 40.0)]
for d, tag, fov in wire_cases:
    p = os.path.join(ROOT, 'wire_arms', d, f'{tag}_results.mat')
    if not os.path.exists(p):
        print(f"{tag:<26}[缺] {p}"); continue
    f = h5py.File(p, 'r')
    ax = np.squeeze(np.array(f['axRow'])).astype(float)
    IMg = f['IM']
    for arm, key in [('C', 'coh'), ('M', 'env'), ('E', 'sqlaw')]:
        img = get2d(IMg, key)
        nx = img.shape[0]
        # 以图像峰值位置为 ROI 中心（W1单丝/W2双丝均在中心附近）
        iy, ix = np.unravel_index(np.argmax(img), img.shape)
        dx = fov / (nx - 1)
        cx = (ix - nx / 2) * dx; cy = (iy - nx / 2) * dx
        IN, OUT = roi2d(nx, fov, cx=cx, cy=cy)
        a, b = img[IN], img[OUT]
        prof = np.squeeze(np.array(f['profRow'][key])).astype(float)
        prof_amp = np.sqrt(np.maximum(prof, 0)) if arm == 'E' else prof
        w = width(ax, prof_amp, 0.5)
        domv = '声能密度' if arm == 'E' else '声压幅值'
        print(f"{tag:<26}{arm:<5}{gcnr(a,b):>9.4f}{cnr(a,b):>9.2f}{psr(img,b):>9.2f}{dr(img):>9.2f}{conc(img,IN):>9.4f}{w:>10.4f}{domv:>8}")
    print("-" * 96)
    f.close()

# ================================================================ 3. 已有扫描（regime / snr）
for subdir, tagname in [('study_regime_semicircle128', 'rc'), ('study_snr_semicircle128', 'snr')]:
    p = os.path.join(ROOT, subdir, 'study_regime.mat' if tagname == 'rc' else 'study_snr.mat')
    if not os.path.exists(p):
        # 试其它命名
        import glob
        cand = glob.glob(os.path.join(ROOT, subdir, '*.mat'))
        if not cand: continue
        p = cand[0]
    f = h5py.File(p, 'r')
    print()
    print("#" * 96)
    print(f"# 三、已有扫描：{subdir}  （keys={list(f.keys())}）")
    print("#" * 96)
    for k in f.keys():
        if isinstance(f[k], h5py.Dataset):
            a = np.array(f[k]); print(f"  {k}: shape={a.shape} dtype={a.dtype}")
    f.close()
