#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Replace the rows of one experiment in fivechain_sim.csv with rows from another file.

用途：某个实验的实现被修正后需要单独重跑，而不重跑整条 A-E 链。
      本脚本按 exp 字段替换，不做数值合并；顺序无关（下游按 dict 取键）。

用法：
    python pa_merge_sim_rows.py <target.csv> <patch.csv> <EXP> [<EXP> ...] [--drop-malformed]
    python pa_merge_sim_rows.py <target.csv> <patch.csv> <EXP> [--upsert]

    --drop-malformed  丢弃非 6 字段的畸形行（默认报错退出）
    --upsert          按 (exp,arm,condition,metric) 覆盖或新增，而不是整段替换某个 exp。
                      加密幅度网格时必须用它：整段替换会把没重跑的档位一起删掉。

为什么要 --drop-malformed：
    上游 fprintf 格式串错位会产出 10 字段的行（v0.33 首跑踩过：A 段 dr_dB 传了向量）。
    csv.DictReader 对这种行不报错，只把多余字段塞进 None 键，前 6 个字段则整体右移——
    结果是一行"看着合法、数值全错"的数据被写回去。所以这里默认严格：
    只要出现非 6 字段的行就报错退出，必须由人显式加 --drop-malformed 才丢弃。

退出码：0 成功；1 参数/文件问题；2 补丁中缺该 exp 的行或主表存在畸形行（不静默跳过）。
"""
import csv
import io
import os
import sys

COLS = ["exp", "arm", "condition", "metric", "value", "unit"]


def read_strict(path):
    """返回 (rows, malformed)。malformed 为 [(行号, 字段数, 原始字段列表), ...]。"""
    rows, malformed = [], []
    with io.open(path, "r", encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd)
        if [h.strip() for h in header] != COLS:
            raise SystemExit("[error] %s 表头不是 %s，实际为 %s" % (path, COLS, header))
        for i, rec in enumerate(rd, start=2):
            if not rec:
                continue
            if len(rec) != len(COLS):
                malformed.append((i, len(rec), rec))
                continue
            rows.append(dict(zip(COLS, rec)))
    return rows, malformed


def write(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in COLS})


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    unknown = flags - {"--drop-malformed", "--upsert"}
    if unknown:
        print("[error] 未知开关 %s" % sorted(unknown))
        return 1
    if len(args) < 3:
        print(__doc__)
        return 1
    target, patch = args[0], args[1]
    exps = [e.upper() for e in args[2:]]
    for p in (target, patch):
        if not os.path.exists(p):
            print("[error] missing %s" % p)
            return 1

    main_rows, bad_main = read_strict(target)
    patch_rows, bad_patch = read_strict(patch)

    for name, bad in (("主表", bad_main), ("补丁", bad_patch)):
        if not bad:
            continue
        print("[error] %s 有 %d 行字段数不为 %d：" % (name, len(bad), len(COLS)))
        for ln, n, rec in bad[:10]:
            print("    行 %d: %d 字段 -> %s" % (ln, n, rec))
        if len(bad) > 10:
            print("    ...（其余 %d 行略）" % (len(bad) - 10))
        if "--drop-malformed" not in flags:
            print("    默认不丢弃。确认这些行是上游 bug 产物后，加 --drop-malformed 重跑。")
            return 2
        print("    [warn] 已按 --drop-malformed 丢弃 %d 行" % len(bad))

    out = []
    upsert = "--upsert" in flags
    for e in exps:
        add = [r for r in patch_rows if r["exp"].upper() == e]
        if not add:
            print("[error] patch has no rows for exp=%s" % e)
            return 2
        if upsert:
            pos = {(r["exp"], r["arm"], r["condition"], r["metric"]): i
                   for i, r in enumerate(main_rows)}
            n_up = n_new = 0
            for r in add:
                k = (r["exp"], r["arm"], r["condition"], r["metric"])
                if k in pos:
                    main_rows[pos[k]] = r
                    n_up += 1
                else:
                    main_rows.append(r)
                    pos[k] = len(main_rows) - 1
                    n_new += 1
            out.append((e, n_up, n_new, True))
        else:
            old = [r for r in main_rows if r["exp"].upper() == e]
            out.append((e, len(old), len(add), False))
            main_rows = [r for r in main_rows if r["exp"].upper() != e]
            main_rows.extend(add)

    write(target, main_rows)
    for e, a, b, was_upsert in out:
        if was_upsert:
            print("[merge] exp=%-3s upsert: %d rows updated, %d appended" % (e, a, b))
        else:
            print("[merge] exp=%-3s replaced %4d rows with %4d rows" % (e, a, b))
    print("[ok] %s now has %d rows" % (target, len(main_rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
