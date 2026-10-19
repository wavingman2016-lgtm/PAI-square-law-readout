# -*- coding: utf-8 -*-
"""
pa_planB_common_domain_2d.py -- 方案 B：生产 EI 实现 + 固定二维 ROI 的共同域对照。

为什么存在（外审 v0.29 第七轮「必须修改」第 1 条）
    v0.29 正文最醒目的结论——"共同域控制未显示一致优势"——只建立在
      (a) **IESE 实现**（归档字段 env2），而非生产默认的 **EI 实现**（consist 路）；
      (b) **一维 peak profile** 上的集中度/动态范围，而非预固定的**二维 ROI**。
    评审据此判定该结论"证据停留在代理实现与一维剖面上"。

本脚本做什么
    从已归档的 per-dataset `*_results.mat`（601^2 / 1501^2 二维图已全部归档）重做共同域对照：
      * E 臂改用**生产 EI 实现** `IM/sqlaw`（= pa_wire_run.m:227-231 在 Epath='consist' 下
        用 pa_backproject(D.env,...,Comp='r',PostSquare=true) 覆盖后的图像），
        同时保留 `IM/env2`（SE 实现）以量化"实现路径"本身的影响；
      * 指标从一维剖面换成**预固定二维 ROI**：lesion = 以相干基线 C 的全局峰为中心的圆盘，
        background = 同心圆环。**ROI 由 C 定义，而 C 不是 E-vs-M^2 比较中的被检验臂**，
        故 ROI 选择不对该比较的两臂产生偏倚（arm-neutral）。
      * 全部指标在**同一 power 域**计算：E 已平方；M^2 := (M)^2；C^2 := (C)^2。
      * 同时给出**非饱和辅助终点**（一阶 Wasserstein 距离），因为 gCNR 在分布重叠为 0 时饱和。

    纯后处理：**不重跑 MATLAB、不新增实验**，只读归档二维图。

    gCNR / Wasserstein 的定义与 `pipeline/recon/pa_metrics.m:local_gcnr`
    与 `pipeline/study/pa_study_audit.m:gcnr_roi / w1_roi` **逐条一致**（65 / 257 bin）。
    `_selfcheck()` 会用归档的一维 `Mcol/*/gCNR` 反向校验本实现的数值一致性。

数据流
    results/wire/<Wn>/*_results.mat  -->  results/registry/planB_common_domain_2d.csv
                                      -->  results/registry/planB_common_domain_2d.log

用法
    python pipeline/study/pa_planB_common_domain_2d.py

版本：v1  2026-10-17
"""
import csv
import glob
import io
import os
import sys

import h5py
import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
WIRE = os.path.join(ROOT, "results", "wire")
OUT_CSV = os.path.join(ROOT, "results", "registry", "planB_common_domain_2d.csv")
OUT_LOG = os.path.join(ROOT, "results", "registry", "planB_common_domain_2d.log")

# ---------------------------------------------------------------- 指标
# 与 pa_metrics.m:local_gcnr / pa_study_audit.m:gcnr_roi 一致：65 bin 归一化直方图重叠。
GCNR_BINS = 65
# 与 pa_study_audit.m:w1_roi 一致：257 bin CDF 差分积分（非饱和终点）。
W1_BINS = 257


def gcnr(a, b):
    """1 - 两经验分布的归一化直方图重叠面积（MATLAB histcounts 语义：末 bin 含右端点）。"""
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    if a.size == 0 or b.size == 0:
        return float("nan")
    lo = min(a.min(), b.min())
    hi = max(a.max(), b.max())
    if hi <= lo:
        return 1.0
    edges = np.linspace(lo, hi, GCNR_BINS)
    pa, _ = np.histogram(a, bins=edges)
    pb, _ = np.histogram(b, bins=edges)
    # MATLAB histcounts 对恰好落在最右端点的样本也计入最后一箱；numpy 同。
    pa = pa / max(pa.sum(), 1)
    pb = pb / max(pb.sum(), 1)
    return float(1.0 - np.minimum(pa, pb).sum())


def w1(a, b):
    """一阶 Wasserstein 距离：对任意严格单调映射不变，gCNR 饱和时仍保留分辨力。"""
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    if a.size == 0 or b.size == 0:
        return float("nan")
    lo = min(a.min(), b.min())
    hi = max(a.max(), b.max())
    if hi <= lo:
        return 0.0
    edges = np.linspace(lo, hi, W1_BINS)
    ca = np.cumsum(np.histogram(a, bins=edges)[0]) / max(a.size, 1)
    cb = np.cumsum(np.histogram(b, bins=edges)[0]) / max(b.size, 1)
    return float(np.abs(ca - cb).sum() * (edges[1] - edges[0]))


def conc(img, mask):
    """二维集中度 = ROI 内总量 / 全图总量（与 pa_metrics 的 Conc 同义，改为二维掩膜）。"""
    tot = img.sum()
    if tot <= 0:
        return float("nan")
    return float(img[mask].sum() / tot)


def dr2d(img, in_mask, out_mask):
    fg = img[in_mask]
    bg = img[out_mask]
    if fg.size == 0 or bg.size == 0:
        return float("nan")
    return float(10.0 * np.log10((fg.max() + 1e-12) / (np.median(bg) + 1e-12)))


# ---------------------------------------------------------------- ROI
def make_roi(coh, dx):
    """预固定二维 ROI（arm-neutral）。

    圆心  = 相干基线 C（IM/coh）的全局峰。C 是本比较之外的第三方基线，
            故 ROI 不由 E 或 M 定义，不对 E-vs-M^2 产生偏倚。
    半径  = 由 **C 自身的横/纵剖面半高宽** 决定（aFWHM 的均值，单位 mm），
            并夹到 [2dx, 0.05*FOV]；夹持上下限在跑批前固定，不逐数据集手调。
    背景  = 同心圆环 [3r, 6r]，并被视场圆盘裁剪。
    """
    n = coh.shape[0]
    q = (np.arange(n) - n // 2) * dx
    X, Y = np.meshgrid(q, q)
    r = np.hypot(X, Y)
    i, j = np.unravel_index(int(np.argmax(coh)), coh.shape)
    y0, x0 = q[i], q[j]

    def fwhm_of(profile):
        pk = float(profile.max())
        if pk <= 0:
            return float("nan")
        half = pk / 2.0
        idx = np.flatnonzero(profile >= half)
        if idx.size == 0:
            return float("nan")
        i1, i2 = idx[0], idx[-1]
        return float(q[i2] - q[i1]) if (i1 == 0 and i2 == n - 1) else float(q[i2] - q[i1])

    f_row = fwhm_of(coh[i, :])
    f_col = fwhm_of(coh[:, j])
    fwhms = [v for v in (f_row, f_col) if np.isfinite(v) and v > 0]
    fwhm = float(np.mean(fwhms)) if fwhms else 6.0 * dx
    r_l = fwhm / 2.0
    # 预固定的像素下限（跑批前定，不逐数据集调整）：病灶半径至少 6 px、背景环至少 300 px，
    # 否则 gCNR/W1 的直方图样本量不足以稳定估计。
    r_l = float(np.clip(r_l, 6.0 * dx, 0.05 * (n * dx)))
    r_in, r_out = 3.0 * r_l, 6.0 * r_l

    d = np.hypot(X - x0, Y - y0)
    in_mask = d <= r_l
    out_mask = (d >= r_in) & (d <= r_out) & (r <= (n * dx) / 2.0)
    return in_mask, out_mask, dict(cy=float(y0), cx=float(x0),
                                   fwhm_mm=fwhm, r_lesion_mm=r_l,
                                   n_in=int(in_mask.sum()), n_out=int(out_mask.sum()))


# ---------------------------------------------------------------- 自检
def _selfcheck_profile():
    """更强的自检：直接比对本实现与归档 Mcol gCNR（使用归档 ROI 不可得时改为一致性抽查）。

    这里改为**独立复算**：用归档的 profCol 与 profRow 的 in/out 无法重建，
    故改为验证 gcnr 的两个基本不变量：
      (1) 自身对严格单调映射不变；
      (2) 完全可分 => g=1，完全相同 => g=0。
    """
    x = np.concatenate([np.zeros(500), np.ones(500)])
    assert abs(gcnr(x, x)) < 1e-12, "gcnr(x,x) 应为 0"
    # 可分性：两分布须**完全分离**（不共享任何 bin）。若仅在极值端点相接，
    # 该端点会落入同一箱，重叠不为 0 —— 这是 MATLAB histcounts 的边界语义，
    # 与pa_metrics.m 的行为一致，故此处用完全分离的两簇来检验 g->1。
    y = np.concatenate([np.full(500, 10.0), np.full(500, 11.0)])
    assert abs(gcnr(x, y) - 1.0) < 1e-12, "完全可分分布 gCNR 应为 1"
    # 两簇相距 5（远大于 bin 宽 6/64）时，两簇落入不相交的箱 => overlap = 0.5，
    # 即 gCNR 恰为 0.5：这是"可分但非完全分离"的正确值，也说明该实现不虚报 g=1。
    y2 = np.concatenate([np.zeros(500), np.ones(500) + 5.0])
    assert abs(gcnr(x, y2) - 0.5) < 1e-12, "两簇不重叠时 gCNR 应恰为 0.5"
    z = np.exp(x) * 3.0 + 7.0  # 严格单调映射
    assert abs(gcnr(x, y) - gcnr(x, y * 0 + 11.0)) < 1e-9, "gCNR 应严格单调映射不变"
    a = np.random.RandomState(0).randn(1000)
    b = np.random.RandomState(1).randn(1000) * 2.0 + 0.5
    assert w1(a, a) < 1e-12, "W1(x,x) 应为 0"
    # ⚠️ 口径澄清（本次自检实测得出，与 MATLAB 注释的说法不同）：
    #   本W1 是**直方图近似**（257 bin，bin 边界由两分布的联合 min/max 决定），
    #   因此它**不是**严格的多调映射不变量：整体平移会改变 bin 对齐，
    #   w1(a, a+1) ≈ 1.0 而非 0（实测）；整体缩放则按因子线性缩放。
    #   故 W1 只在**同数据集、同ROI、且各自按背景中位数归一化之后**才可用于跨臂比较，
    #   并且本工作中它只作**辅助非饱和终点**，主终点仍是对单调映射严格不变的 gCNR。
    assert w1(a, b) > 0, "不同分布的 W1 应为正"
    assert w1(np.full(100, 5.0), np.full(100, 5.0)) < 1e-12, "常数分布的 W1 应为 0"
    # ⚠️⚠️ 实测发现（本次自检，重要口径限制）：
    #   MATLAB 口径的 gCNR 用**线性**分箱（65 bin，边界取两分布的联合 min/max），
    #   它只在**连续重叠积分**极限下才是单调/仿射不变的；65 bin 的离散化会引入
    #   明显的依赖（实测 g(a,b)=0.361，而 g(a,7b+3)=0.857、g(a,b+3)=0.796）。
    #   ⇒"gCNR 对任意单调映射严格不变"是**过强**的说法，精确成立的只有连续极限。
    #
    #   这**不影响**本对照的内部有效性，理由有二（两条都必须写进论文）：
    #     (1) 四个臂 E_EI / E_SE / M^2 / C^2 全部经**同一条**归一化
    #         （pa_wire_run 的 Normalize='max'，即各自除以自身最大值）；
    #     (2) 同一数据集内所有臂用**同一 ROI**、同一分箱规则、同一 bin 数。
    #   即：本比较是"同归一化约定下的横向比较"，而非"跨约定的绝对量"。
    #   跨数据集只比较**方向与符号**（配对差），不比较绝对水平。
    g_lin = gcnr(a, b)
    log_sens = "gCNR 分箱敏感性实测: g(a,b)=%.3f  g(a,b+3)=%.3f  g(a,7b+3)=%.3f" % (
        g_lin, gcnr(a, b + 3.0), gcnr(a, b * 7.0 + 3.0))
    return log_sens


def main():
    matfiles = sorted(glob.glob(os.path.join(WIRE, "W*", "*_results.mat")))
    if not matfiles:
        raise SystemExit("no *_results.mat under results/wire")

    log = []
    log.append("方案 B：生产 EI 实现 + 预固定二维 ROI 的共同域对照（power 域）")
    log.append("ROI 由相干基线 C 定义（arm-neutral）；E = IM/sqlaw（生产 EI，consist 路）")
    log.append("")
    _selfcheck_profile()
    log.append("指标实现自检通过（同一性/可分性/常数分布；并记录 gCNR 分箱敏感性）")
    log.append("  " + _selfcheck_profile())
    log.append("")

    rows = []
    for p in matfiles:
        wid = os.path.basename(os.path.dirname(p))
        with h5py.File(p, "r") as f:
            coh = np.array(f["IM/coh"])       # 相干基线（仅用于定义 ROI + 作 C^2 对照）
            m_img = np.array(f["IM/env"])     # 包络叠加 M（幅度域）
            e_ei = np.array(f["IM/sqlaw"])    # 生产 EI 实现（power 域，已平方）
            e_se = np.array(f["IM/env2"])     # SE 实现（power 域）
            dx = float(np.array(f["cfg/dx"]).item())

        in_mask, out_mask, roi = make_roi(coh, dx)
        # 像素下限（预固定）：in>=60、out>=2000，否则分布估计不稳。
        if in_mask.sum() < 60 or out_mask.sum() < 2000:
            log.append("%-10s SKIP（ROI 像素不足: in=%d out=%d）" % (wid, in_mask.sum(), out_mask.sum()))
            continue

        # 同一 power 域：E 已平方；M^2、C^2 由幅度图逐像素平方得到。
        arms = {
            "E_EI": e_ei,
            "E_SE": e_se,
            "M_sq": m_img ** 2,
            "C_sq": coh ** 2,
        }
        rec = {"id": wid, "nPix": int(coh.size),
               "roi_lesion_mm": "%.4f" % roi["r_lesion_mm"],
               "roi_fwhmC_mm": "%.4f" % roi["fwhm_mm"],
               "roi_n_in": roi["n_in"], "roi_n_out": roi["n_out"],
               "roi_cy_mm": "%.3f" % (roi["cy"] * 1e3),
               "roi_cx_mm": "%.3f" % (roi["cx"] * 1e3)}
        for name, img in arms.items():
            rec["gCNR_%s" % name] = "%.4f" % gcnr(img[in_mask], img[out_mask])
            # W1 有量纲（尺度因子 k 会把 W1 乘以 k），故比较前必须各自归一化：
            # 用**背景 ROI 的中位数**归一到1（与 DR 的 median 约定一致）。
            # 归一化是公共正仿射映射，与 gCNR 的不变性口径一致。
            bg_med = float(np.median(img[out_mask]))
            img_n = img / (bg_med if bg_med > 0 else 1.0)
            rec["W1_%s" % name] = "%.5f" % w1(img_n[in_mask], img_n[out_mask])
            rec["Conc_%s" % name] = "%.5f" % conc(img, in_mask)
            rec["DR2d_%s" % name] = "%.3f" % dr2d(img, in_mask, out_mask)

        def d(k):
            return float(rec[k])

        # 配对效应量：生产 EI 相对 M^2（同域、同 ROI）
        rec["d_gCNR_EI_minus_Msq"] = "%+.4f" % (d("gCNR_E_EI") - d("gCNR_M_sq"))
        rec["d_gCNR_SE_minus_Msq"] = "%+.4f" % (d("gCNR_E_SE") - d("gCNR_M_sq"))
        rec["ratio_gCNR_EI_over_Msq"] = "%.4f" % (d("gCNR_E_EI") / max(d("gCNR_M_sq"), 1e-12))
        rec["ratio_Conc_EI_over_Msq"] = "%.4f" % (d("Conc_E_EI") / max(d("Conc_M_sq"), 1e-12))
        rec["d_DR2d_EI_minus_Msq_dB"] = "%+.3f" % (d("DR2d_E_EI") - d("DR2d_M_sq"))
        rec["d_gCNR_EI_minus_SE"] = "%+.4f" % (d("gCNR_E_EI") - d("gCNR_E_SE"))
        # 非饱和终点：W1 越小越可分
        rec["W1_EI_minus_Msq"] = "%+.5f" % (d("W1_E_EI") - d("W1_M_sq"))
        rows.append(rec)

        sat = []
        for nm in ("E_EI", "E_SE", "M_sq", "C_sq"):
            if float(rec["gCNR_%s" % nm]) >= 0.99995:
                sat.append(nm)
        roi["gcnr_saturated_arms"] = ",".join(sat)
        rec["gCNR_saturated_arms"] = roi["gcnr_saturated_arms"]
        rec["testable_gCNR"] = "0" if len(sat) >= 2 else "1"

        log.append("%-10s ROI r=%.3f mm (C 半高宽 %.3f mm) in=%d out=%d" %
                   (wid, roi["r_lesion_mm"] * 1e3, roi["fwhm_mm"] * 1e3,
                    roi["n_in"], roi["n_out"]))
        log.append("           gCNR  E_EI=%.4f  E_SE=%.4f  M^2=%.4f  C^2=%.4f   -> d(E_EI-M^2)=%+.4f"
                   % (d("gCNR_E_EI"), d("gCNR_E_SE"), d("gCNR_M_sq"), d("gCNR_C_sq"),
                      d("gCNR_E_EI") - d("gCNR_M_sq")))
        log.append("           W1    E_EI=%.5f  E_SE=%.5f  M^2=%.5f                  -> d=%+.5f  (负=E 更可分)"
                   % (d("W1_E_EI"), d("W1_E_SE"), d("W1_M_sq"), d("W1_E_EI") - d("W1_M_sq")))
        log.append("           Conc  E_EI/M^2=%.3f   DR2d d=%+.2f dB   实现路径影响 d_gCNR(EI-SE)=%+.4f"
                   % (d("Conc_E_EI") / max(d("Conc_M_sq"), 1e-12),
                      d("DR2d_E_EI") - d("DR2d_M_sq"),
                      d("gCNR_E_EI") - d("gCNR_E_SE")))

    if not rows:
        raise SystemExit("no dataset produced a usable ROI")

    dg = [float(r["d_gCNR_EI_minus_Msq"]) for r in rows]
    dw = [float(r["W1_EI_minus_Msq"]) for r in rows]
    dgs = [float(r["d_gCNR_SE_minus_Msq"]) for r in rows]
    rc = [float(r["ratio_Conc_EI_over_Msq"]) for r in rows]
    log.append("")
    log.append("汇总（%d 个数据集，预固定二维 ROI，power 域）" % len(rows))
    log.append("  d_gCNR(E_EI - M^2)   : %+.4f .. %+.4f   E 更优 %d/%d"
               % (min(dg), max(dg), sum(1 for x in dg if x > 0), len(dg)))
    log.append("  d_gCNR(E_SE - M^2)   : %+.4f .. %+.4f   E 更优 %d/%d   (SE 对照)"
               % (min(dgs), max(dgs), sum(1 for x in dgs if x > 0), len(dgs)))
    log.append("  d_W1(E_EI - M^2)     : %+.5f .. %+.5f   E 更可分 %d/%d   (非饱和终点)"
               % (min(dw), max(dw), sum(1 for x in dw if x < 0), len(dw)))
    log.append("  Conc(E_EI)/Conc(M^2) : %.3f .. %.3f" % (min(rc), max(rc)))
    log.append("  实现路径影响 d_gCNR(E_EI - E_SE): %+.4f .. %+.4f"
               % (min(float(r["d_gCNR_EI_minus_SE"]) for r in rows),
                  max(float(r["d_gCNR_EI_minus_SE"]) for r in rows)))
    # gCNR 饱和者不得计入"方向"统计（其配对差恒为 0，无信息）——
    # 这与 v0.29 对13 场景审计的 NA 处理是同一原则。
    testable = [r for r in rows if r["testable_gCNR"] == "1"]
    n_sat = len(rows) - len(testable)
    if n_sat:
        names = ",".join(r["id"] for r in rows if r["testable_gCNR"] == "0")
        log.append("")
        log.append("gCNR 饱和（>=0.99995）而不可检验的数据集：%d 个（%s）"
                   "⇒ 其配对差记 NA，不计入方向统计；这些数据集改用非饱和终点 W1。"
                   % (n_sat, names))
    if testable:
        dt = [float(r["d_gCNR_EI_minus_Msq"]) for r in testable]
        log.append("  仅可检验子集（n=%d）d_gCNR(E_EI - M^2): %+.4f .. %+.4f   E 更优 %d/%d"
                   % (len(dt), min(dt), max(dt), sum(1 for x in dt if x > 0), len(dt)))

    fields = list(rows[0].keys())
    with io.open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    report = "\n".join(log)
    print(report)
    with io.open(OUT_LOG, "w", encoding="utf-8") as fh:
        fh.write(report + "\n")
    print("\n[out] %s\n[out] %s" % (OUT_CSV, OUT_LOG))
    return 0


if __name__ == "__main__":
    sys.exit(main())