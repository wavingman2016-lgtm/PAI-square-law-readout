#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validate results/fivechain/fivechain_sim.csv, and optionally repair it.

背景：MATLAB 侧若把一个向量写进 `%.6g`，fprintf 的格式串会错位，把后续字段
挤到下一行，生成 9 列的垃圾行，且不报错。这类损坏只能在落盘后查出来，
所以要有独立的一道闸。

用法
    python pa_validate_sim_csv.py <csv>              # 只校验，退出码 0/2
    python pa_validate_sim_csv.py <csv> --clean      # 校验并重写（丢弃非白名单行）
    python pa_validate_sim_csv.py <csv> --replace A E --patch <patch.csv>
                                                     # 用 patch 文件替换指定实验的行

规则
    1. 每行恰好 6 个字段（exp, arm, condition, metric, value, unit）
    2. exp 属于白名单 {A,B,C,D,D2,E}
    3. value 可解析为 float（允许 NaN / Inf，它们是有意义的）
    4. unit 非空
    5. 键 (exp, arm, condition, metric) 唯一
"""
import csv
import io
import os
import sys

COLS = ["exp", "arm", "condition", "metric", "value", "unit"]
ALLOWED_EXP = ["A", "B", "C", "D", "D2", "E"]


def read_raw(path):
    with io.open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.reader(fh))


def check(path, rows):
    problems = []
    header = rows[0]
    if header[:6] != COLS:
        problems.append("header is %r" % (header,))
    seen = {}
    counts = {}
    for ln, r in enumerate(rows[1:], start=2):
        if not r or all(c.strip() == "" for c in r):
            continue
        if len(r) != 6:
            problems.append("line %d: %d fields, not 6 -> %r" % (ln, len(r), r))
            continue
        exp, arm, cond, metric, val, unit = r
        if exp not in ALLOWED_EXP:
            problems.append("line %d: unknown exp %r" % (ln, exp))
            continue
        try:
            float(val)
        except ValueError:
            problems.append("line %d: value %r not numeric" % (ln, val))
            continue
        if unit.strip() == "":
            problems.append("line %d: empty unit" % ln)
            continue
        key = (exp, arm, cond, metric)
        if key in seen:
            problems.append("line %d: duplicate key %r (first at line %d)"
                            % (ln, key, seen[key]))
        else:
            seen[key] = ln
        counts[exp] = counts.get(exp, 0) + 1
    return problems, counts


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    path = argv[1]
    if not os.path.exists(path):
        print("[error] missing %s" % path)
        return 1
    rows = read_raw(path)
    problems, counts = check(path, rows)

    if "--replace" in argv:
        patch = argv[argv.index("--patch") + 1]
        exps = argv[argv.index("--replace") + 1:argv.index("--patch")]
        exps = [e.upper() for e in exps]
        prows = read_raw(patch)
        pproblems, _ = check(patch, prows)
        if pproblems:
            print("[error] patch file fails validation:")
            for p in pproblems:
                print("   ", p)
            return 2
        body = [r for r in rows[1:] if r and len(r) == 6 and r[0] in ALLOWED_EXP]
        for e in exps:
            add = [r for r in prows[1:] if r and r[0].upper() == e]
            if not add:
                print("[error] patch has no rows for exp=%s" % e)
                return 2
            old = sum(1 for r in body if r[0] == e)
            body = [r for r in body if r[0] != e]
            body.extend(add)
            print("[replace] exp=%-3s %4d -> %4d rows" % (e, old, len(add)))
        rows = [COLS] + body
        problems, counts = check(path, rows)

    if "--clean" in argv or "--replace" in argv:
        with io.open(path, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
            w.writerows(rows)
        print("[write] %s" % path)

    print("[counts] " + ", ".join("%s=%d" % (e, counts.get(e, 0)) for e in ALLOWED_EXP))
    print("[total] %d rows" % sum(counts.values()))
    if problems:
        print("[FAIL] %d problem(s):" % len(problems))
        for p in problems[:40]:
            print("   ", p)
        return 2
    print("[PASS] all rows valid")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
