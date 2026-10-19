# -*- coding: utf-8 -*-
"""
pa_common_domain_control.py -- 共同域控制：把 E 与 M^2 放在同一（功率/能量）域比较。

为什么存在
    外审（v0.24 第二轮）指出：正文的 DR 增益（+2.4…+16.0 dB）与能量集中度比值
    （Conc(E)/Conc(M)=1.17–2.60×）是**原生域（E=平方域, M=幅度域）**上各自取值的
    跨域比较。把幅度图 M 逐像素平方后，DR(M^2)=2·DR(M)（20log10 约定）、
    Conc(M^2)>Conc(M)，因此这两个"收益"可能只是平方映射的数值效应，而非 E 的聚合优势。

    本脚本从已归档的 per-dataset `*_results.mat`（含完整剖面 profCol/profRow 与指标
    Mcol/Mrow）重算共同域控制，**不新增实验、不重跑 MATLAB**：

        Conc(I_M^2)   = Σ_ROI (profCol_env)^2 / Σ_FOV (profCol_env)^2     （ROI = 峰值 ± Band）
        Conc(I_E)     = Σ_ROI profCol_env2 / Σ_FOV profCol_env2           （= Mcol/env2/Conc）
        DR_power(E)   = 10·log10( peak(profRow_env2) / median(profRow_env2) )
        DR_power(M^2) = 10·log10( peak(profRow_env)^2 / median(profRow_env)^2 )
                        = 20·log10( peak(profRow_env) / median(profRow_env) )  = DR(M)

    定义与 `pipeline/recon/pa_metrics.m`、`pipeline/recon/pa_profile.m` 一一对应：
        DR    = 20·log10(peak/median)，取自**行剖面**（Mrow）
        Conc  = Σ_ROI / Σ_FOV，取自**列剖面**（Mcol），ROI = 峰值 ± Band，
                Band = max(2, round(0.05·N))，N = 剖面长度
    两条剖面均已随 `*_results.mat` 归档，故本脚本是**纯后处理**，与正文口径一致。

数据流
    results/wire/<Wn>/*_results.mat  （IM/profCol/profRow/Mcol/Mrow 已归档）
        -->  results/registry/common_domain_control.csv
        -->  results/registry/common_domain_control.log

用法
    python pipeline/study/pa_common_domain_control.py

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
OUT_CSV = os.path.join(ROOT, "results", "registry", "common_domain_control.csv")
OUT_LOG = os.path.join(ROOT, "results", "registry", "common_domain_control.log")


def band_of(n):
    """pa_profile 的 Band = max(2, round(0.05 * min(Ny,Nx)))；1D 剖面长度即 N。"""
    return max(2, int(round(0.05 * n)))


def conc(prof, pk, band):
    """Conc = Σ_ROI / Σ_FOV，ROI = 峰值 ± band（与 pa_metrics/pa_profile 一致）。"""
    n = len(prof)
    mask = np.zeros(n, dtype=bool)
    mask[max(0, pk - band):min(n, pk + band + 1)] = True
    return prof[mask].sum() / prof.sum()


def main():
    matfiles = sorted(glob.glob(os.path.join(WIRE, "W*", "*_results.mat")))
    if not matfiles:
        raise SystemExit("no *_results.mat under results/wire")

    rows, log = [], []
    for p in matfiles:
        wid = os.path.basename(os.path.dirname(p))
        with h5py.File(p, "r") as f:
            def g(n):
                return np.array(f[n]).squeeze()

            pc_env = g("profCol/env")      # M 列剖面（归一化）
            pc_env2 = g("profCol/env2")    # E 列剖面
            pr_env = g("profRow/env")      # M 行剖面
            pr_env2 = g("profRow/env2")    # E 行剖面
            mc_env = g("Mcol/env/Conc")    # Conc(M) 归档值
            mc_env2 = g("Mcol/env2/Conc")  # Conc(E) 归档值
            mr_env = g("Mrow/env/DR")      # DR(M) 归档值
            mr_env2 = g("Mrow/env2/DR")    # DR(E) 归档值

        n = len(pc_env)
        band = band_of(n)
        pkM = int(np.argmax(pc_env))
        pkE = int(np.argmax(pc_env2))

        cM = conc(pc_env, pkM, band)
        cE = conc(pc_env2, pkE, band)
        cM2 = conc(pc_env ** 2, pkM, band)          # Conc(I_M^2)

        drp_E = 10 * np.log10((pr_env2.max() + 1e-12) / (np.median(pr_env2) + 1e-12))
        drp_M2 = 20 * np.log10((pr_env.max() + 1e-12) / (np.median(pr_env) + 1e-12))

        # 一致性校验：本脚本对 M/E 的 Conc 必须复现归档值（否则口径漂移）
        assert abs(cM - mc_env) < 1e-4, (wid, "Conc(M) drift", cM, mc_env)
        assert abs(cE - mc_env2) < 1e-4, (wid, "Conc(E) drift", cE, mc_env2)

        rows.append({
            "id": wid,
            "Conc_M": "%.6f" % mc_env,
            "Conc_E": "%.6f" % mc_env2,
            "Conc_M_sq": "%.6f" % cM2,
            "Conc_E_over_M_sq": "%.4f" % (cE / cM2),
            "DR_M_native_dB": "%.4f" % mr_env,
            "DR_E_native_dB": "%.4f" % mr_env2,
            "DRp_E_dB": "%.3f" % drp_E,
            "DRp_M_sq_dB": "%.3f" % drp_M2,
            "DRp_E_minus_M_sq_dB": "%+.3f" % (drp_E - drp_M2),
        })
        log.append("%-10s Conc(E)/Conc(M^2)=%.3f  DRp(E)-DRp(M^2)=%+.2f dB "
                   "(DR E=%.2f, M=%.2f dB native)" %
                   (wid, cE / cM2, drp_E - drp_M2, mr_env2, mr_env))

    conc_ratio = [float(r["Conc_E_over_M_sq"]) for r in rows]
    drp_diff = [float(r["DRp_E_minus_M_sq_dB"]) for r in rows]
    log.append("")
    log.append("Conc(E)/Conc(M^2) over %d datasets : %.3f .. %.3f  (E>M^2 in %d/6)"
               % (len(rows), min(conc_ratio), max(conc_ratio), sum(1 for x in conc_ratio if x > 1)))
    log.append("DRp(E)-DRp(M^2) over %d datasets  : %+.2f .. %+.2f dB  (E>M^2 in %d/6)"
               % (len(rows), min(drp_diff), max(drp_diff), sum(1 for x in drp_diff if x > 0)))

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
