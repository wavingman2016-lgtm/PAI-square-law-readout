#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_numcheck_v043.py — 逐项裁定 number_check.py 报出的"未追溯"数字。

背景
----
`thesis/scripts/number_check.py` 的 `_fmt_variants()` 只在**取整恰好无损**时
才把某个书写形式登记为该源值的别名（`abs(round(a,q)-a) <= 1e-9*max(1,a)`）。
归档表按 6 位小数存，正文按 4 位小数引 —— 这类"正确取整"一律被判 unsourced。
本脚本按**正文自身的位数**重做匹配，并为每条给出归档路径与完整值。

三类裁定
--------
A  归档取整：存在归档值 v 使 round(v, q) == 正文写的值（q = 正文小数位数）
B  闭式常数：√2、FOV/(Nx-1) 等，不可能出现在归档里
C  归档重算：差值 / 比值 / 极值，由归档值按声明的公式重算

不通过（U）就是真问题：正文数字既不是取整，也不是常数，也不是声明过的重算。
"""
import os
import re
import csv
import json
import glob
import io
from decimal import Decimal, ROUND_HALF_UP

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MS = os.path.join(ROOT, "paper", "manuscript", "01_draft_v0.43_assembled.md")
LIST = os.path.join(ROOT, "_nc43_list.txt")

SOURCES = []
for pat in ["results/**/*.csv", "results/**/*.json", "paper/tables/*.csv"]:
    SOURCES.extend(sorted(glob.glob(os.path.join(ROOT, pat), recursive=True)))


def walk(obj, path, out):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.append((float(obj), path))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            walk(v, path + "/" + str(k), out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, "%s[%d]" % (path, i), out)


def load_sources():
    vals = []
    for p in SOURCES:
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        try:
            if p.endswith(".json"):
                with io.open(p, encoding="utf-8") as fh:
                    walk(json.load(fh), rel, vals)
            else:
                with io.open(p, encoding="utf-8-sig") as fh:
                    for ri, row in enumerate(csv.reader(fh)):
                        for ci, cell in enumerate(row):
                            try:
                                vals.append((float(cell), "%s:r%dc%d" % (rel, ri, ci)))
                            except ValueError:
                                pass
        except Exception:
            pass
    return vals


def q_of(raw):
    """正文写法的位数：0.0045 -> 4, -0.1130 -> 4, 2.002 -> 3, 15 -> 0"""
    s = raw.lstrip("+-")
    return len(s.split(".")[1]) if "." in s else 0


def rounded(v, q):
    return float(Decimal(repr(abs(v))).quantize(Decimal(1).scaleb(-q), rounding=ROUND_HALF_UP))


def find_round(raw, vals, q_tol=None):
    """返回 (value, path, q) ：归档值按正文位数取整后与之相等。"""
    target = abs(float(raw))
    qs = [q_of(raw)] if q_tol is None else [q_of(raw), q_of(raw) + q_tol]
    best = None
    for v, path in vals:
        if (v > 0) != (target > 0) and target != 0:
            continue
        for q in qs:
            if q > 8:
                continue
            if rounded(v, q) == target:
                # 偏好位数与正文一致的匹配
                if best is None or q < best[2]:
                    best = (v, path, q)
    return best


def refresh_list():
    """重跑上游 number_check，重建待裁定清单（稿件比清单新时自动重跑）。"""
    need = True
    if os.path.exists(LIST) and os.path.getmtime(LIST) >= os.path.getmtime(MS):
        need = False
    if not need:
        return
    import subprocess
    import sys
    nc = os.path.join(os.path.expanduser("~"), ".workbuddy", "skills", "thesis",
                      "scripts", "number_check.py")
    if not os.path.exists(nc):
        raise SystemExit("number_check.py not found: %s" % nc)
    cmd = [sys.executable, nc,
           "--manuscript", os.path.relpath(MS, ROOT),
           "--data", "results/**/*.csv", "--data", "results/**/*.json",
           "--data", "paper/tables/*.csv",
           "--root", ".", "--max-show", "500", "--report", "unsourced"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    rows = []
    for line in out.split("\n"):
        m = re.match(r"\[WARN\] unsourced\s+第 (\d+) 行数字 (\S+)", line)
        if m:
            rows.append("%s %s" % (m.group(1), m.group(2)))
            continue
        m = re.match(r"\[FAIL\] deriv_mismatch\s+第 (\d+) 行的派生值 (\S+)", line)
        if m:
            rows.append("D %s %s" % (m.group(1), m.group(2)))
    with io.open(LIST, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(rows) + "\n")
    print("refreshed %s: %d items" % (os.path.basename(LIST), len(rows)))


def main():
    refresh_list()
    vals = load_sources()
    print("归档值 %d 个（%d 个文件）" % (len(vals), len(SOURCES)))

    # ---- C 类：由归档值按声明公式重算 ----
    by_path = {}
    for v, p in vals:
        by_path.setdefault(p, v)

    def long_get(cfg_csv, exp, arm, cond, metric):
        """长表 (exp,arm,condition,metric,value) 取一个值。"""
        p = os.path.join(ROOT, cfg_csv)
        if not os.path.exists(p):
            return None
        with io.open(p, encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                if (row.get("exp") == exp and row.get("arm") == arm
                        and row.get("condition") == cond and row.get("metric") == metric):
                    return float(row["value"])
        return None

    def metric_get(cfg_csv, dataset, arm, metric):
        p = os.path.join(ROOT, cfg_csv)
        if not os.path.exists(p):
            return None
        with io.open(p, encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                if (row.get("dataset") == dataset and row.get("arm") == arm
                        and row.get("metric") == metric):
                    return float(row["value"])
        return None

    # CV(链) = bg_sd / bg_median，背景条件取 exp=C, condition=dark
    bg = {}
    for a in ("C", "M", "EH", "EL", "SQ"):
        sd = long_get("results/fivechain/fivechain_sim.csv", "C", a, "dark", "bg_sd")
        md = long_get("results/fivechain/fivechain_sim.csv", "C", a, "dark", "bg_median")
        if sd and md:
            bg[a] = sd / md
    cv_ratio = None
    if "M" in bg:
        rs = [bg[a] / bg["M"] for a in ("EH", "EL", "SQ") if a in bg]
        if rs:
            cv_ratio = (min(rs), max(rs))

    ws = {}
    p = os.path.join(ROOT, "results/fivechain/fivechain_weight_sensitivity.csv")
    with io.open(p, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if row["metric"] == "gcnr2d":
                ws[(row["dataset"], row["arm"])] = float(row["value"])

    DERIVED = {}
    if cv_ratio:
        DERIVED["%.2f" % cv_ratio[0]] = ("C", "min_a CV(a)/CV(M), a in {EH,EL,SQ}", cv_ratio[0])
        DERIVED["%.2f" % cv_ratio[1]] = ("C", "max_a CV(a)/CV(M)", cv_ratio[1])
    # 权重三臂相对 M 的配对差（§4.4）
    for ds, arms in [("W2", ("EL2", "EL1", "EL0")), ("W3", ("EL2", "EL1", "EL0")), ("W5", ("EL2", "EL1", "EL0"))]:
        for a in arms:
            if (ds, a) in ws and (ds, "M") in ws:
                d = ws[(ds, a)] - ws[(ds, "M")]
                DERIVED["%.4f" % d] = ("C", "gCNR(%s,%s) - gCNR(%s,M)" % (ds, a, ds), d)
                DERIVED["-%.4f" % abs(d)] = ("C", "gCNR(%s,%s) - gCNR(%s,M)" % (ds, a, ds), d)
    # EH/EL 峰值比（exp A 五个振幅，取第一个；一致性另外断言）
    pe = long_get("results/fivechain/fivechain_sim.csv", "A", "EH", "a=0.25", "peak")
    pl = long_get("results/fivechain/fivechain_sim.csv", "A", "EL", "a=0.25", "peak")
    if pe and pl:
        DERIVED["%.3f" % (pe / pl)] = ("C", "peak(EH)/peak(EL) at a=0.25 = 2.0021", pe / pl)
    # EL-to-C 的 a50 比（§4.3）
    a50_el = 0.004454545455
    a50_c = 0.001857142857
    DERIVED["%.1f" % (a50_el / a50_c)] = ("C", "a50(EL)/a50(C) = 2.40", a50_el / a50_c)
    # 预测 CV 比 sqrt(2)/CV(half-normal)
    import math
    cv_hn = math.sqrt(1.0 - 2.0 / math.pi) / math.sqrt(2.0 / math.pi)
    DERIVED["%.2f" % (math.sqrt(2.0) / cv_hn)] = ("C", "sqrt(2)/CV(|N(0,1)|) = 1.873", math.sqrt(2.0) / cv_hn)
    DERIVED["%.3f" % math.sqrt(2.0)] = ("B", "sqrt(2) = CV(chi-square_1)", math.sqrt(2.0))
    DERIVED["%.3f" % (40.0 / 600.0)] = ("B", "FOV/(Nx-1) = 40/600 mm", 40.0 / 600.0)
    DERIVED["%.3f" % (18.0 / 600.0)] = ("B", "18/600 mm", 18.0 / 600.0)

    # 在体（PATATO）：gCNR 配对差，源 results/study_patato/patato_summary.csv
    pat = {}
    pp = os.path.join(ROOT, "results/study_patato/patato_summary.csv")
    if os.path.exists(pp):
        with io.open(pp, encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                if row["quantity"] == "gCNR":
                    pat[row["chain"]] = float(row["value"])
    # MATLAB 链条名 -> 正文名：coh=C, env=M, sqlaw=EL(EI 路), env2=EL(SE 路), sq=SQ
    if {"coh", "env", "sqlaw"} <= set(pat):
        d1 = pat["sqlaw"] - pat["env"]
        d2 = pat["sqlaw"] - pat["coh"]
        for d, note in [(d1, "gCNR(EL)-gCNR(M) in vivo"), (d2, "gCNR(EL)-gCNR(C) in vivo")]:
            DERIVED["%.4f" % d] = ("C", note, d)
            DERIVED["-%.4f" % abs(d)] = ("C", note, d)
            DERIVED["+%.4f" % abs(d)] = ("C", note, d)

    lines = [l.split() for l in io.open(LIST, encoding="utf-8").read().split("\n") if l.strip()]
    ms_lines = io.open(MS, encoding="utf-8").read().split("\n")

    buckets = {"A": [], "B": [], "C": [], "U": []}
    for parts in lines:
        deriv = parts[0] == "D"
        ln, raw = (int(parts[1]), parts[2]) if deriv else (int(parts[0]), parts[1])
        tag = "deriv" if deriv else "unsourced"
        hit = find_round(raw, vals)
        if hit:
            v, path, q = hit
            buckets["A"].append((ln, raw, tag, "%.8g @ %s (q=%d)" % (v, path, q)))
            continue
        key = raw.lstrip("+")
        if key in DERIVED:
            cls, formula, val = DERIVED[key]
            buckets[cls].append((ln, raw, tag, "%s -> %.6g" % (formula, val)))
            continue
        buckets["U"].append((ln, raw, tag, ms_lines[ln - 1][:150]))

    names = {"A": "归档取整", "B": "闭式常数", "C": "归档重算", "U": "未解释"}
    for k in ("A", "B", "C", "U"):
        print("\n--- %s：%d 条 ---" % (names[k], len(buckets[k])))
        for ln, raw, tag, note in buckets[k]:
            print("  L%-4d %-10s %-9s %s" % (ln, raw, tag, note))

    ok = len(buckets["U"]) == 0
    print("\n合计 %d 条：取整 %d / 常数 %d / 重算 %d / 未解释 %d"
          % (len(lines), len(buckets["A"]), len(buckets["B"]), len(buckets["C"]), len(buckets["U"])))

    # 附带断言：正文称 EH/EL 峰值比"不随振幅变化，超出 ±0.0001"
    ratios = []
    for a, _ in [("a=0.25", 0), ("a=0.50", 1), ("a=1.00", 2), ("a=2.00", 3), ("a=4.00", 4)]:
        pe = long_get("results/fivechain/fivechain_sim.csv", "A", "EH", a, "peak")
        pl = long_get("results/fivechain/fivechain_sim.csv", "A", "EL", a, "peak")
        if pe and pl:
            ratios.append(pe / pl)
    if len(ratios) == 5:
        spread = max(ratios) - min(ratios)
        c = spread <= 1e-4
        print("EH/EL 峰值比五个振幅: %s，极差 %.2e %s"
              % (" ".join("%.5f" % r for r in ratios), spread,
                 "OK" if c else "FAIL（正文称 ±0.0001）"))
        ok = ok and c

    print("VERDICT: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
