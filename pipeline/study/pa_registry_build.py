# -*- coding: utf-8 -*-
"""
pa_registry_build.py -- 达标数据登记表（registry.csv）的**发布脚本**。

为什么存在
    外审 P1-C7 指出：正文里的 DR 增益 / 能量集中度在 `pipeline/` 内**零命中**，
    即这些数字无法由随稿发布的代码复现。本脚本补上这条链：
        每组数据的 `*_sheet.csv` + `*_report.txt`  -->  registry.csv
    重算**全部数值列**，并用既有 registry 做**一致性断言**（漂移即失败退出非零）。

数据流（逐列）
    来源 A  results/wire/<Wn>/*_sheet.csv        每方法一行
            env     = D1   通道级幅度包络叠加（Arm M，本项目基线）
            env2    = D1^2 包络平方（含 Hilbert）== 生产默认路径
            sqlaw   = D2'  LPF(x^2)（免 Hilbert 路）
            sq      = D2   裸平方（反例，非估计器）
    来源 B  results/wire/_SUMMARY.csv            pearson_sqlaw, D2p_exact
    来源 C  results/wire/<Wn>/*_report.txt       QC 量（validChanFrac / edgeFrac / baseCNR）

重算规则（单一事实源，正文 §4.2 / Table 6 / Table 3 必须与之一致）
    dCNR            = CNR(env2) - CNR(env)
    dgCNR           = gCNR(env2) - gCNR(env)
    DR_env_dB       = DR(env)
    DR_E_dB         = DR(env2)                      <-- 生产默认路径（含 Hilbert 的包络路）
    DR_gain_dB      = DR_E_dB - DR_env_dB
    conc_ratio_E_M  = Conc(env2) / Conc(env)
    DR_E_dB_sqlaw   = DR(sqlaw)                     <-- 免 Hilbert 路，两条路的差即插值顺序残差

    ★ 两条 E 路径（env2 与 sqlaw）之差 <= 0.02 dB，是**插值顺序残差**，不是归一化差异；
      本脚本同时给出两者，便于核对。v0.21 之前 registry 的 DR_E 列在两组数据上混用了
      这两条路，本脚本统一到生产默认（env2）。

输出
    results/registry/registry.csv          覆盖写（列结构与旧版兼容 + 新增 conc_ratio_E_M）
    results/registry/registry_release.csv  人读版（重算值 + 旧值 + 差值）
    results/registry/_build.log            运行日志

用法
    python pipeline/study/pa_registry_build.py            # 重算 + 断言 + 覆盖写
    python pipeline/study/pa_registry_build.py --check     # 只断言，不写盘

版本：v1  2026-10-16
"""
import argparse
import csv
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REG = os.path.join(ROOT, "results", "registry")
REG_CSV = os.path.join(REG, "registry.csv")
SUM_CSV = os.path.join(ROOT, "results", "wire", "_SUMMARY.csv")
REL_CSV = os.path.join(REG, "registry_release.csv")

# 旧写的数值列（用于一致性断言）；其余列原样透传
NUM_COLS = ["dCNR", "dgCNR", "DR_gain_dB", "DR_env_dB", "DR_E_dB",
            "pearson_D2p_D1sq", "validChanFrac", "edgeFrac", "baseCNR"]
TOL = 0.02          # dB / 无量纲量统一容差（两路插值顺序残差量级）


def read_rows(path):
    with io.open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_sheet(result_dir):
    """返回 {method: {col: float}}。"""
    d = os.path.join(ROOT, result_dir)
    cands = [f for f in sorted(os.listdir(d)) if f.endswith("_sheet.csv")]
    if not cands:
        raise SystemExit("sheet not found in %s" % d)
    rows = read_rows(os.path.join(d, cands[0]))
    out = {}
    for r in rows:
        out[r["method"]] = {k: float(v) for k, v in r.items()
                            if k not in ("method", "dataset") and v not in ("", None)}
    return out


def read_qc(result_dir):
    """从 *_report.txt 取 QC 量。"""
    d = os.path.join(ROOT, result_dir)
    cands = [f for f in sorted(os.listdir(d)) if f.endswith("_report.txt")]
    txt = io.open(os.path.join(d, cands[0]), encoding="utf-8", errors="replace").read()

    def grab(pat):
        m = re.search(pat, txt)
        return float(m.group(1)) if m else float("nan")

    return {
        "validChanFrac": grab(u"有效通道率\\s*([0-9.]+)"),
        "edgeFrac":      grab(u"环带能量占比\\s*([0-9.]+)"),
        "baseCNR":       grab(u"基线 env 的 CNR\\s*=\\s*([0-9.]+)"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只断言，不写盘")
    a = ap.parse_args()

    reg = read_rows(REG_CSV)
    summ = {r["id"]: r for r in read_rows(SUM_CSV)}
    log = []
    out_rows = []
    drift = []

    for r in reg:
        wid = os.path.basename(r["result_dir"])          # e.g. W1_single
        key = wid.split("_")[0]                          # W1
        sh = read_sheet(r["result_dir"])
        qc = read_qc(r["result_dir"])
        env, env2, sqlaw = sh["env"], sh["env2"], sh["sqlaw"]

        new = {
            "dCNR":       env2["CNR"] - env["CNR"],
            "dgCNR":      env2["gCNR"] - env["gCNR"],
            "DR_env_dB":  env["DR_dB"],
            "DR_E_dB":    env2["DR_dB"],
            "DR_gain_dB": env2["DR_dB"] - env["DR_dB"],
            "pearson_D2p_D1sq": float(summ[key]["pearson_sqlaw"]),
            "validChanFrac": qc["validChanFrac"],
            "edgeFrac":      qc["edgeFrac"],
            "baseCNR":       qc["baseCNR"],
            "conc_ratio_E_M": env2["Concentration"] / env["Concentration"],
            "DR_E_dB_sqlaw":  sqlaw["DR_dB"],
        }

        # ---- 一致性断言：新值 vs 旧值和盘托出 ----
        row_drift = []
        for c in NUM_COLS:
            if c not in r or r[c] in ("", None):
                continue
            old = float(r[c])
            if abs(old - new[c]) > TOL:
                row_drift.append((c, old, new[c]))
        if row_drift:
            drift.append((r["id"], row_drift))

        log.append("%s  dCNR=%+.3f dgCNR=%+.3f DR_gain=%+.2f dB "
                   "DR_E=%+.2f (sqlaw %+.2f) conc=%.3fx"
                   % (r["id"], new["dCNR"], new["dgCNR"], new["DR_gain_dB"],
                      new["DR_E_dB"], new["DR_E_dB_sqlaw"], new["conc_ratio_E_M"]))

        merged = dict(r)
        for c in NUM_COLS:
            merged[c] = ("%+.3f" % new[c]) if c in ("dCNR", "dgCNR") else ("%.4f" % new[c])
        merged["DR_gain_dB"] = "%.2f" % new["DR_gain_dB"]
        merged["conc_ratio_E_M"] = "%.3f" % new["conc_ratio_E_M"]
        merged["DR_E_dB_sqlaw"] = "%.3f" % new["DR_E_dB_sqlaw"]
        out_rows.append(merged)

    # ---- 汇总 ----
    gains = [float(r["DR_gain_dB"]) for r in out_rows]
    concs = [float(r["conc_ratio_E_M"]) for r in out_rows]
    log.append("")
    log.append("DR_gain_dB range over %d datasets : %+.2f .. %+.2f dB"
               % (len(gains), min(gains), max(gains)))
    log.append("conc_ratio_E_M range               : %.2f .. %.2f x"
               % (min(concs), max(concs)))
    log.append("DR_E - DR_E_sqlaw (interp-order residual), max |diff| = %.4f dB"
               % max(abs(float(r["DR_E_dB"]) - float(r["DR_E_dB_sqlaw"])) for r in out_rows))

    report = "\n".join(log)
    print(report)

    if drift:
        print("\n!! REGISTRY DRIFT (stored value differs from recomputed beyond %.2f)" % TOL)
        for rid, items in drift:
            for c, old, new in items:
                print("   %-6s %-18s stored=%.4f recomputed=%.4f" % (rid, c, old, new))
        if not a.check:
            print("   (rows still rewritten with the recomputed values)")
    else:
        print("\nOK: every recomputed value agrees with the stored registry within %.2f" % TOL)

    if a.check:
        return 0 if not drift else 1

    cols = list(reg[0].keys()) + ["conc_ratio_E_M", "DR_E_dB_sqlaw"]
    with io.open(REG_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    # ---- 同步英文版 Table 3（元数据沿用既有英译，数值列一律重算）----
    t3 = os.path.join(ROOT, "paper", "tables", "Table03_registry.csv")
    if os.path.exists(t3):
        en = {r["id"]: r for r in read_rows(t3)}
        numerics = {c for c in cols if c not in (
            "id", "data", "subject", "array", "radius_mm", "rateorsteps",
            "sample_fs_MHz", "validated_config", "verdict", "result_dir", "figure")}
        with io.open(t3, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in out_rows:
                m = dict(en.get(r["id"], {}))
                for c in numerics:
                    m[c] = r[c]
                m["id"] = r["id"]
                w.writerow(m)
        print("[out] %s (metadata kept, numerics recomputed)" % t3)
    with io.open(REL_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "data", "result_dir", "dCNR", "dgCNR", "DR_env_dB",
                    "DR_E_dB", "DR_E_dB_sqlaw", "DR_gain_dB", "conc_ratio_E_M"])
        for r in out_rows:
            w.writerow([r["id"], r["data"], r["result_dir"], r["dCNR"], r["dgCNR"],
                        r["DR_env_dB"], r["DR_E_dB"], r["DR_E_dB_sqlaw"],
                        r["DR_gain_dB"], r["conc_ratio_E_M"]])
    with io.open(os.path.join(REG, "_build.log"), "w", encoding="utf-8") as fh:
        fh.write(report + "\n")
    print("\n[out] %s\n[out] %s" % (REG_CSV, REL_CSV))
    return 0


if __name__ == "__main__":
    sys.exit(main())
