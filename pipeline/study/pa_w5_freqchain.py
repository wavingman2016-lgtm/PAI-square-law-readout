"""W5 (data5) 频率链重新核对：在原始记录（未做 0.5-15 MHz 设备带通）上复算谱量。

背景：pa_band_audit 的输入 D0.filtered 已被 pa_cfg own5 预设的分析带 [0.5, 15] MHz
带通过，因此审计给出的"实测带中心" f0_meas=1.25 MHz 对低于 0.5 MHz 的低频主导成分
不敏感（循环性）。Table S1 的 decision_basis 另称"未滤波谱峰 0.188 MHz"，而实际使用
的分析中心 f0_eff=0.35 MHz 既非 1.25 也非 0.188。本脚本在原始记录上直接测量，
检验 0.35 MHz 是否对应某个可定义的谱量（原始 -6 dB 带中心 / 峰 / 累积带中心等）。

口径与 pa_band_audit.m 对齐：Hann 窗、逐通道周期图、对数域中位数、movmean 平滑、
-6 dB 带、5-95% 累积能量带、能量重心、50% 累积频率。
"""
import glob
import os

import numpy as np
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data5")
OUT = os.path.join(ROOT, "results", "study_e4c")
os.makedirs(OUT, exist_ok=True)

FS = 100e6
NS = 3200


def load_channels(idxs):
    """data5 的 *.xlsx 实为 TAB 分隔文本（3 位小数），非真 xlsx。"""
    cols = []
    for i in idxs:
        p = os.path.join(DATA, "%d.xlsx" % i)
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            txt = fh.read()
        vals = [float(t) for t in txt.replace("\n", "\t").split("\t") if t.strip()]
        cols.append(np.asarray(vals[:NS], dtype=float))
    return cols


def audit(sigMat, fs, in_band=None, smooth_bins=None, label=""):
    """复刻 pa_band_audit v2 的统计量（中位数对数周期图 + 平滑 + 三类带）。"""
    nS, nC = sigMat.shape
    win = np.hanning(nS)
    nHalf = nS // 2 + 1
    df = fs / nS
    freq = np.arange(nHalf) * df
    Lg = np.empty((nHalf, nC))
    for j in range(nC):
        Pf = np.abs(np.fft.fft(sigMat[:, j] * win)) ** 2
        Lg[:, j] = np.log(Pf[:nHalf] + np.finfo(float).eps)
    P = np.exp(np.median(Lg, axis=1))
    if smooth_bins is None:
        smooth_bins = max(3, round(0.05 * (in_band[1] - in_band[0]) / df)) if in_band else 23
    # movmean (MATLAB 居中窗)
    k = smooth_bins
    pad = k // 2
    Pp = np.pad(P, pad, mode="edge")
    Ps = np.convolve(Pp, np.ones(k) / k, mode="valid")[:nHalf]
    Psb = Ps.copy()
    if in_band is not None:
        m = (freq >= in_band[0]) & (freq <= in_band[1])
        if m.any():
            Psb[~m] = 0.0
    ipk = int(np.argmax(Psb))
    f_peak = freq[ipk]
    pdb = 10 * np.log10(Psb / (Psb.max() + np.finfo(float).eps))
    k = ipk
    while k > 1 and pdb[k] > -6:
        k -= 1
    f_lo6 = freq[k]
    k = ipk
    while k < nHalf - 1 and pdb[k] > -6:
        k += 1
    f_hi6 = freq[k]
    B6 = f_hi6 - f_lo6
    tot = Psb.sum() + np.finfo(float).eps
    c = np.cumsum(Psb / tot)
    i05 = int(np.argmax(c >= 0.05))
    i95 = int(np.argmax(c >= 0.95))
    i50 = int(np.argmax(c >= 0.50))
    f05, f95, f50 = freq[i05], freq[i95], freq[i50]
    fcnt = float((freq * (Psb / tot)).sum())
    spur = B6 < 0.25 * max(f_peak, 1.0)
    return dict(label=label, f_peak_MHz=f_peak / 1e6, f_lo6_MHz=f_lo6 / 1e6,
                f_hi6_MHz=f_hi6 / 1e6, B6_MHz=B6 / 1e6, b6_centre_MHz=0.5 * (f_lo6 + f_hi6) / 1e6,
                f05_MHz=f05 / 1e6, f95_MHz=f95 / 1e6, f50_MHz=f50 / 1e6,
                fcnt_MHz=fcnt / 1e6, spurFlag=bool(spur), smooth_bins=int(smooth_bins))


def main():
    files = sorted(int(os.path.splitext(os.path.basename(p))[0])
                   for p in glob.glob(os.path.join(DATA, "*.xlsx")))
    print("channels found: %d (first %s ... last %s)" % (len(files), files[:3], files[-3:]))
    # 与审计一致：取 AC 有效值最强的 64 通道
    rng = np.random.default_rng(20261017)
    probe = list(rng.choice(len(files), size=min(160, len(files)), replace=False))
    cols = load_channels([files[i] for i in probe])
    rms = np.array([np.sqrt(np.mean(c ** 2)) for c in cols])
    order = np.argsort(rms)[::-1]
    sel = [cols[j] for j in order[:64]]
    X = np.column_stack(sel)
    print("selected 64 channels by RMS: rms %.4g .. %.4g" % (rms[order[0]], rms[order[63]]))

    # (1) 原始记录：仅去直流（逐通道减均值）
    Xraw = X - X.mean(axis=0, keepdims=True)
    r1 = audit(Xraw, FS, in_band=None, smooth_bins=23, label="raw (DC-removed, no band-pass)")

    # (2) 复刻管线：0.5-15 MHz 设备/分析带带通后（ Butterworth 3 阶零相位近似）
    from scipy.signal import butter, filtfilt
    b, a = butter(3, [0.5e6 / (FS / 2), 15e6 / (FS / 2)], btype="band")
    Xbp = filtfilt(b, a, Xraw, axis=0)
    r2 = audit(Xbp, FS, in_band=(0.5e6, 15e6), label="after [0.5,15] MHz band-pass (= audit input)")

    lines = []
    hdr = ("quantity_MHz,f_raw_peak,f_raw_b6_centre,f_raw_f50,f_raw_fcnt,"
           "f_bp_peak,f_bp_b6_lo,f_bp_b6_hi,f_bp_b6_centre,f_bp_f50,f_bp_fcnt")
    lines.append(hdr)
    lines.append("%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f" % (
        0.35, r1["f_peak_MHz"], r1["b6_centre_MHz"], r1["f50_MHz"], r1["fcnt_MHz"],
        r2["f_peak_MHz"], r2["f_lo6_MHz"], r2["f_hi6_MHz"], r2["b6_centre_MHz"],
        r2["f50_MHz"], r2["fcnt_MHz"]))
    lines.append("# reference (archived W5_report.txt): audited peak 0.78, -6dB band [0.47,2.03], "
                 "centre 1.25, cum band [0.56,7.44]; decision_basis raw unfiltered peak 0.188")
    lines.append("# raw detail: " + str(r1))
    lines.append("# bp  detail: " + str(r2))
    out = os.path.join(OUT, "w5_frequency_chain.csv")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
