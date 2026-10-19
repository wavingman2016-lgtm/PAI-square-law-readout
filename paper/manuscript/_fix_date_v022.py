#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P08 修复：把 v0.22 交付件里误写的日期 2026-10-22 一律改回真实日期 2026-10-16。

背景：本轮 v0.21 → v0.22 与 v0.21 交付**同日**（系统日期 2026-10-16），
      稿内却写成了 2026-10-22（相差 6 天）。属事实错误，须统一更正。

用法：
    python _fix_date_v022.py --dry-run
    python _fix_date_v022.py
"""
import argparse
import io
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

TARGETS = [
    "paper/manuscript/00_manuscript_EN.md",
    "paper/manuscript/_assemble_draft.py",
    "paper/manuscript/_cite_insert.py",
    "paper/README.md",
    "paper/notes/CHANGELOG_v0.22.md",
    "paper/notes/可复现材料清单_v0.22.md",
    "paper/notes/应对方案与修订结果对比_v0.22.md",
    "paper/notes/投稿前验收清单_v0.22.md",
    "paper/notes/版本规则与版本号.md",
    "_rollback/PAI-version-v022/README.md",
    "_rollback/PAI-version-v022/PROVENANCE.md",
    ".workbuddy/memory/MEMORY.md",
    ".workbuddy/memory/参考_详细事实.md",
]

OLD = "2026-10-22"
NEW = "2026-10-16"
# MEMORY.md 头部版本标签同步（v2026-10-22k2 -> v2026-10-16j）
MEM_OLD = "v2026-10-22k2"
MEM_NEW = "v2026-10-16j"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    total = 0
    for rel in TARGETS:
        p = os.path.join(ROOT, rel)
        if not os.path.isfile(p):
            print("  [missing] %s" % rel)
            continue
        s = io.open(p, encoding="utf-8", newline="").read()
        n = s.count(OLD)
        m = s.count(MEM_OLD)
        if n == 0 and m == 0:
            print("  [clean ] %s" % rel)
            continue
        t = s.replace(OLD, NEW).replace(MEM_OLD, MEM_NEW)
        total += n + m
        print("  [fix   ] %-58s %d 处" % (rel, n + m))
        if not a.dry_run:
            io.open(p, "w", encoding="utf-8", newline="").write(t)
    print("\n%s：共 %d 处" % ("DRY-RUN" if a.dry_run else "已改", total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
