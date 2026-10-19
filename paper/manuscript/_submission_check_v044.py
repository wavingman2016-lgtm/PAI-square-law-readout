#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_submission_check_v044.py — 投稿前自查一条命令（thesis Stage 5F + Stage 6）。

把四类检查串起来，任一失败即非零退出：

  1. 构建闸门      `_round.py`（tables → norm → assemble → docx → supp → gates）
  2. 数字对账      thesis/scripts/number_check.py（带 number_ignore.json 台账）
  3. 论点依赖      thesis/scripts/claim_check.py（claim_graph.yaml 锚点是否还活着）
  4. 五个数值探针  selfaudit / numbers / bootstrap / novelty / v044

为什么单列一条命令：这些检查此前分散在五个脚本 + 两次手敲命令里，
"跑了没有"只能靠记忆。Stage 5E 的说法是——审计产出报告不算完，
产出**决定**才算完。

用法：
    python paper/manuscript/_submission_check_v044.py            # 全跑
    python paper/manuscript/_submission_check_v044.py --no-build # 跳过重构建
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILL = os.path.join(os.path.expanduser("~"), ".workbuddy", "skills", "thesis", "scripts")
MS = "paper/manuscript/01_draft_v0.44_assembled.md"
LEDGER = "paper/manuscript/number_ignore.json"
GRAPH = "paper/manuscript/claim_graph.yaml"

PROBES = [
    "paper/manuscript/_probe_v033_selfaudit.py",
    "paper/manuscript/_probe_v033_numbers.py",
    "paper/manuscript/_probe_v041_bootstrap.py",
    "paper/manuscript/_probe_v042_novelty.py",
    "paper/manuscript/_probe_v044_round.py",
]


def run(cmd, label, cwd=ROOT):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or ""), label


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-build", action="store_true", help="跳过 _round.py 重构建")
    args = ap.parse_args()

    results = []
    py = sys.executable

    if not args.no_build:
        rc, out, lb = run([py, "paper/manuscript/_round.py"], "构建闸门")
        ok = rc == 0 and "ALL CLEAN" in out
        results.append((lb, ok, "退出码 %d, %s" % (rc, "ALL CLEAN" if "ALL CLEAN" in out else "gates 未全绿")))

    nc = os.path.join(SKILL, "number_check.py")
    if os.path.exists(nc):
        rc, out, lb = run([py, nc, "--manuscript", MS,
                           "--data", "results/**/*.csv", "--data", "results/**/*.json",
                           "--data", "paper/tables/*.csv", "--root", ".", "--ignore", LEDGER,
                           "--max-show", "10", "--report", "unsourced"], "数字对账")
        m = re.search(r"未追溯 (\d+)", out)
        bad = int(m.group(1)) if m else -1
        dm = re.search(r"(\d+) 个派生值算术成立", out)
        results.append((lb, bad == 0, "未追溯 %d，派生失配 %s"
                        % (bad, "0" if "deriv_mismatch" not in out else "见输出")))
    else:
        results.append(("数字对账", False, "找不到 %s" % nc))

    cc = os.path.join(SKILL, "claim_check.py")
    if os.path.exists(cc):
        rc, out, lb = run([py, cc, "--graph", GRAPH, "--manuscript", MS, "--root", "."], "论点依赖")
        m = re.search(r"(\d+) FAIL / (\d+) WARN", out)
        f, w = (int(m.group(1)), int(m.group(2))) if m else (-1, -1)
        results.append((lb, f == 0 and w == 0, "%d FAIL / %d WARN" % (f, w)))
    else:
        results.append(("论点依赖", False, "找不到 %s" % cc))

    for p in PROBES:
        rc, out, lb = run([py, p], os.path.basename(p))
        ok = "VERDICT: PASS" in out and rc == 0
        m = re.search(r"^checked (\d+) items?[:\s]+OK (\d+)", out, re.M)
        detail = ("checked %s" % m.group(1)) if m else ("PASS" if ok else "见输出")
        results.append((lb, ok, detail))

    print("\n=== 投稿前自查 ===")
    width = max(len(x[0]) for x in results) + 2
    for lb, ok, detail in results:
        print("  %-4s %-*s %s" % ("PASS" if ok else "FAIL", width, lb, detail))
    nbad = sum(1 for _, ok, _ in results if not ok)
    print("\nVERDICT: %s（%d 项，失败 %d）"
          % ("PASS" if nbad == 0 else "FAIL", len(results), nbad))
    return 0 if nbad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
