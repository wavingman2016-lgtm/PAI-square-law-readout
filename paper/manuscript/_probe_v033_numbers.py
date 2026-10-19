# -*- coding: utf-8 -*-
"""v0.33 数字独立复核：把正文里的关键数字从 registry / 表中重算一遍。

判定三档：
  OK       —— 正文数字等于重算值按同一小数位的正确舍入
  DEV      —— 舍入后仍不等（末位错、写反、取错量），或相对误差超阈
  MISSING  —— 产物里没有这个量，无法重算

为什么不用"相对误差 < 1%"单条判据：0.00446 与真值 0.00445455 只差 0.12%，
但正解是 0.00445——末位错在相对误差上几乎不可见，只有逐位舍入才能抓住。

用法：python paper/manuscript/_probe_v033_numbers.py
退出码：0 = 无 DEV / 无 MISSING；否则 1。
"""
import csv
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REG = os.path.join(ROOT, "results", "fivechain", "fivechain_sim.csv")

V = defaultdict(dict)
T3 = {}
T4 = []
ROWS = []          # (status, label, text, calc, decimals, unit)


def load():
    with open(REG, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                V[r["exp"]][(r["arm"], r["condition"], r["metric"])] = float(r["value"])
            except ValueError:
                pass
    with open(os.path.join(ROOT, "paper", "tables", "T3_sim_summary.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            T3[r["quantity"]] = r
    with open(os.path.join(ROOT, "paper", "tables", "T4_morphology.csv"), encoding="utf-8") as f:
        T4.extend(csv.DictReader(f))


def get(exp, arm, metric, cond=None):
    d = V[exp]
    if cond is not None:
        return d.get((arm, cond, metric))
    for c in ("all", "timing", "amp_ladder"):
        if (arm, c, metric) in d:
            return d[(arm, c, metric)]
    hits = [v for (a, c, m), v in d.items() if a == arm and m == metric]
    return hits[0] if len(hits) == 1 else None


ARMS = ["C", "M", "EH", "EL", "SQ"]


def chk(label, text_val, calc, decimals, unit="", tol=0.02):
    """登记一条复核。decimals = 正文该数的小数位数。"""
    ROWS.append(("CHK", label, text_val, calc, decimals, unit, tol))


def main():
    load()

    # ---- 1. a50：两档精度都查（正文同一量出现两种写法，必须都舍入正确）----
    for arm, tv, dec in [("C", 0.0019, 4), ("SQ", 0.0039, 4), ("M", 0.0045, 4),
                         ("EH", 0.0045, 4), ("EL", 0.0045, 4)]:
        chk("a50 %s (2 s.f.)" % arm, tv, get("C", arm, "a50"), dec, "s")
    for arm, tv in [("M", 0.00455), ("EH", 0.00455), ("EL", 0.00445)]:
        chk("a50 %s (3 s.f.)" % arm, tv, get("C", arm, "a50"), 5, "s")

    # ---- 2. EH/EL 峰值比恒为 2.002（摘要级数字）----
    amps = sorted({c for (a, c, m) in V["A"] if m == "peak" and a == "EH"})
    ratios = [get("A", "EH", "peak", c) / get("A", "EL", "peak", c)
              for c in amps if get("A", "EH", "peak", c) and get("A", "EL", "peak", c)]
    chk("EH/EL peak ratio", 2.002, sum(ratios) / len(ratios) if ratios else None, 3, "1")

    # ---- 3. 阈值 / 背景中位数 ----
    for arm, tv in [("M", 1.19), ("EL", 1.38), ("EH", 1.41), ("SQ", 1.53), ("C", 3.81)]:
        t, b = get("C", arm, "thr_p95"), get("C", arm, "bg_median")
        chk("thr/bg %s" % arm, tv, (t / b) if (t and b) else None, 2, "1")

    # ---- 3b. §4.3 的检测预算分解（v0.36 新增：正文按百分比写，必须能从这里重算）----
    thr_el, thr_sq = get("C", "EL", "thr_p95"), get("C", "SQ", "thr_p95")
    a50_el, a50_sq = get("C", "EL", "a50"), get("C", "SQ", "a50")
    if thr_el and thr_sq:
        chk("threshold drop EL vs SQ", 9.7, (1.0 - thr_el / thr_sq) * 100.0, 1, "%")
    if a50_el and a50_sq:
        chk("a50 rise EL vs SQ", 15, (a50_el / a50_sq - 1.0) * 100.0, 0, "%")
        chk("power drop SQ vs EL", 25, (1.0 - (a50_sq / a50_el) ** 2) * 100.0, 0, "%")

    # ---- 3c. §3.5 的插值口径（v0.37 新增：线性 in a，非 log a）----
    ts3 = os.path.join(ROOT, "paper", "tables", "TS3_detection_thresholds.csv")
    if os.path.exists(ts3):
        worst, worst_arm = 0.0, ""
        with open(ts3, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                al = float(r["lower bracket (x1e-3)"])
                ah = float(r["upper bracket (x1e-3)"])
                kl = int(r["successes lower / 20"])
                kh = int(r["successes upper / 20"])
                frac = (0.5 - kl / 20.0) / (kh / 20.0 - kl / 20.0)
                lin = al + frac * (ah - al)
                lg = al * (ah / al) ** frac          # log-amplitude interpolation
                d = abs(lg - lin) / lin * 100.0
                if d > worst:
                    worst, worst_arm = d, r["chain"]
        chk("a50 log-vs-linear worst (C)", 2.5, worst, 1, "%")
        chk("a50 log-vs-linear label", 1, 1 if worst_arm == "C" else 0, 0, "bool")

    # ---- 4. 平方链背景波动 / M ----
    cvs = {}
    for arm in ARMS:
        s, b = get("C", arm, "bg_sd"), get("C", arm, "bg_median")
        if s and b:
            cvs[arm] = s / b
    if "M" in cvs:
        chk("bg-CV ratio low", 1.85, min(cvs[a] / cvs["M"] for a in ("EH", "EL", "SQ")), 2, "1")
        chk("bg-CV ratio high", 2.00, max(cvs[a] / cvs["M"] for a in ("EH", "EL", "SQ")), 2, "1")

    # ---- 5. 检波级耗时（分项以 arm=all 存放）与加速比 ----
    s_el = (get("E", "all", "tSquare") or 0) + (get("E", "all", "tLPF") or 0)
    s_m = (get("E", "all", "tHilbert") or 0) + (get("E", "all", "tEnv") or 0)
    chk("detection stage EL", 0.0107, s_el or None, 4, "s")
    chk("detection stage M", 0.0244, s_m or None, 4, "s")
    # 正文报的是"逐次配对比值"（归档指标 env_stage_ratio_EL_over_M 的倒数），
    # 不是两个均值的比——两者差 1.4%，正文必须说清用哪一个。
    paired = get("E", "EL", "env_stage_ratio_EL_over_M")
    chk("speed-up EL vs M (paired)", 2.25, (1.0 / paired) if paired else None, 2, "x")
    if s_el and s_m:
        ROWS.append(("INFO", "  ratio of the two means", "%.2f" % (s_m / s_el),
                     None, None, "x", None))
    e2e = get("E", "EL", "e2e_mean")
    chk("detection share of EL e2e", 0.013, (s_el / e2e) if e2e else None, 3, "1", tol=0.06)

    # ---- 6. 端到端与反投影代价 ----
    for arm, tv in [("C", 1.564), ("M", 0.857), ("EH", 0.853), ("EL", 0.843)]:
        chk("end-to-end %s" % arm, tv, get("E", arm, "e2e_mean"), 3, "s")
    chk("e2e M..EL low", 0.84, min(get("E", a, "e2e_mean") for a in ("M", "EH", "EL")), 2, "s")
    chk("e2e M..EL high", 0.86, max(get("E", a, "e2e_mean") for a in ("M", "EH", "EL")), 2, "s")
    chk("tBP complex", 1.520, get("E", "all", "tBP_complex"), 3, "s")
    chk("tBP real", 0.809, get("E", "all", "tBP_real"), 3, "s")

    # ---- 7. D 段弱目标显示对比度（供人工比对，不作判据）----
    for arm in ARMS:
        v = get("D", arm, "weak_display_contrast")
        if v is not None:
            ROWS.append(("INFO", "D weak_display_contrast %s" % arm, "%.4f" % v, None, None, "1", None))

    # ---- 8. T4：EL/M 视场宽度比 ----
    lat = [float(r["EL/M"]) for r in T4
           if r["metric"] == "lateral FWHM (mm)" and r["EL/M"] not in ("", "NA")]
    if lat:
        s = sorted(lat)
        med = s[len(s) // 2] if len(s) % 2 else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2
        chk("EL/M lateral low", 0.37, min(lat), 2, "1")
        chk("EL/M lateral high", 0.92, max(lat), 2, "1")
        chk("EL/M lateral median", 0.68, med, 2, "1")
    axi = [float(r["EL/M"]) for r in T4
           if r["metric"] == "axial FWHM (mm)" and r["EL/M"] not in ("", "NA")]
    if axi:
        ROWS.append(("INFO", "EL/M axial range", "%.2f-%.2f" % (min(axi), max(axi)),
                     None, None, "1", None))

    # ---- 9. 谷深：裸平方在 4:1 下的 0.50/0.60/0.80 mm ----
    for d, tv in [("0.50", 0.17), ("0.60", 0.11), ("0.80", 0.15)]:
        chk("dip SQ @4:1, %s mm" % d, tv, get("B", "SQ", "dip", "r=4:1,d=%smm" % d), 2, "ratio")

    # ---- 10. Fig.4(b) 图注的跌幅极小值（逐臂） ----
    # 图注原写 "reaches -0.9 to -1.0"：复算最深仅 -0.95，-1.0 从未出现 —— 该表述
    # 把跌幅说重了。改为逐臂列出，并在本探针里独立重算，防止再次漂移。
    amps = sorted({c[2:] for (a, c, m) in V["C"] if m == "Pd_fpr5" and c.startswith("a=")},
                  key=float)
    base = {s: V["C"].get(("C", "a=" + s, "Pd_fpr5")) for s in amps}
    for arm, tv in [("M", -0.85), ("EL", -0.90), ("EH", -0.95), ("SQ", -0.80)]:
        dd = [(float(s), V["C"][(arm, "a=" + s, "Pd_fpr5")] - base[s]) for s in amps
              if base[s] is not None and (arm, "a=" + s, "Pd_fpr5") in V["C"]]
        calc = min(dd, key=lambda t: t[1])[1] if dd else None
        chk("min dPd vs C, %s" % arm, tv, calc, 2, "ratio")

    # ---- 输出 ----
    w = max(len(str(r[1])) for r in ROWS) + 2
    print("=== v0.33 数字独立复核（逐位舍入判据）===")
    print("%-9s %-*s %12s %14s %9s" % ("判定", w, "项目", "正文", "重算", "相对误差"))
    print("-" * (w + 50))
    n = defaultdict(int)
    for st, label, tv, cv, dec, unit, tol in ROWS:
        if st == "INFO":
            print("%-9s %-*s %12s" % ("INFO", w, label, tv))
            continue
        if cv is None:
            n["MISSING"] += 1
            print("%-9s %-*s %12s %14s %9s" % ("MISSING", w, label, tv, "-", "-"))
            continue
        rel = abs(cv - tv) / abs(tv) if tv else float("inf")
        same = (round(cv, dec) == round(tv, dec))
        # 唯一合法差异是"按 dec 位舍入"本身，故容差取半个末位（半个 ulp）。
        half_ulp = 0.5 * 10.0 ** (-dec) / abs(tv) if tv else 0.0
        ok = same and rel <= half_ulp * 1.05 + 1e-12
        st = "OK" if ok else "DEV"
        n[st] += 1
        print("%-9s %-*s %12s %14.8g %8.2f%%%s"
              % (st, w, label, tv, cv, rel * 100, "" if same else "  <- 舍入不等"))
    print("-" * (w + 50))
    print("复核 %d 项：OK %d / DEV %d / MISSING %d"
          % (n["OK"] + n["DEV"] + n["MISSING"], n["OK"], n["DEV"], n["MISSING"]))
    print("VERDICT:", "PASS" if n["DEV"] == 0 and n["MISSING"] == 0 else "FAIL")
    return 0 if (n["DEV"] == 0 and n["MISSING"] == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
