#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一轮修订的**单一入口** —— 一条命令跑完整条链路，在第一个失败处停下。

为什么要有这个文件
------------------
在此之前，完成"一轮"需要在十几个终端里手敲一序列命令（规范化表 → 装配 → 构建
DOCX → 跑检查器），每一步都要**记得**而不是**声明**。漏掉一步不会报错，只会让
产物与预期悄悄发散 —— 这正是本项目反复吃亏的地方（母本 nary 审计假绿、表被切成
碎片、图注指向旧文件）。

本脚本把"一轮"变成一个**文件 + 一条命令**：``python _round.py``。

链路（失败即停，退出码 = 该步退出码）
--------------------------------------
  1. ``_normalize_tables.py``   表英文化 + 生成可读视图（幂等）
  2. ``_assemble_draft.py``     母本 → 装配稿（图表按锚点内联）
  3. ``_build_docx.py``         LaTeX→OMML → DOCX（内含五道守卫）
  4. ``_quality_gates.py``      常驻检查器 C1–C7（FAIL 即非零退出）

用法::

    python _round.py                 # 跑全链
    python _round.py --dry           # 只打印计划，不执行
    python _round.py --from build    # 从某一步续跑（norm|build|assemble|docx|gates）
    python _round.py --skip-tables   # 表未改动时跳过第 1 步

零第三方依赖（stdlib only）。
"""
import argparse
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
PAPER = os.path.dirname(HERE)
TBL = os.path.join(PAPER, "tables")

# (阶段名, 工作目录, 脚本名, 说明)
STEPS = [
    ("tables", TBL, "_build_v033_tables.py",
     "由 results/*.csv 生成 T1–T5 / TS1–TS2（数值唯一入口）"),
    ("norm", TBL, "_normalize_tables.py",
     "表英文化 + 可读视图（幂等，可跳过）"),
    ("assemble", HERE, "_assemble_draft_v033.py",
     "母本 → 装配稿（v0.33 锚点内联）"),
    ("docx", HERE, "_build_docx.py",
     "装配稿 → DOCX（五道守卫：nary空/LaTeX泄漏/幂等/断表/数学失败）"),
    ("supp", HERE, "_assemble_supp_v033.py",
     "补充材料独立成稿（Table S1–S4，与主稿同一渲染器）"),
    ("gates", HERE, "_quality_gates.py",
     "常驻检查器 C1–C7（FAIL 阻断）"),
]
ORDER = [s[0] for s in STEPS]


def _run(name, cwd, script, desc, dry):
    print("\n" + "=" * 68)
    print("[%s] %s" % (name, desc))
    print("=" * 68)
    cmd = [PY, os.path.join(cwd, script)]
    if dry:
        print("  (dry) 将运行: %s  @ %s" % (" ".join(cmd), cwd))
        return 0
    t0 = os.times().elapsed
    p = subprocess.run(cmd, cwd=cwd)
    print("  -> 退出码 %d  (%.1f s)" % (p.returncode, os.times().elapsed - t0))
    return p.returncode


def main():
    ap = argparse.ArgumentParser(description="一轮修订的单一入口")
    ap.add_argument("--dry", action="store_true", help="只打印计划")
    ap.add_argument("--from", dest="frm", default="tables", choices=ORDER,
                    help="从该阶段开始（默认 tables）")
    ap.add_argument("--skip-tables", action="store_true",
                    help="跳过表规范化（表未改动时）")
    args = ap.parse_args()

    steps = list(STEPS)
    if args.skip_tables:
        steps = [s for s in steps if s[0] != "norm"]
    start = ORDER.index(args.frm)
    steps = [s for s in steps if ORDER.index(s[0]) >= start]

    print("PAI 修订轮：%d 步%s" % (len(steps), "（dry-run）" if args.dry else ""))
    for name, cwd, script, desc in steps:
        rc = _run(name, cwd, script, desc, args.dry)
        if rc != 0:
            print("\n!!! 阶段 %r 失败（退出码 %d），链路停止。" % (name, rc))
            print("    其余阶段未运行 —— 这是**刻意的**：产物必须来自同一次全绿。")
            return rc

    print("\n" + "=" * 68)
    print("全链通过：表 → 装配稿 → DOCX → 检查器 均无 FAIL。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
