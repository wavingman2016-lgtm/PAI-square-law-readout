#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""构建 v0.37 回滚包（_rollback/PAI-version-v037/）。

与 v0.36 包的关系
-----------------
v0.36 包的 `pin_v036/` 是 v0.36 定版那一刻的源文件快照，因此本包同样提供
**源级**双向回退：

    pin_v037/    v0.37 定版（本轮结束态）
    to_v036/     v0.36 的交付件 + 源文件快照（从 v0.36 包搬入）

本轮无新增数据文件；`TS3_detection_thresholds.csv` 已在 v0.36 引入。

用法
----
    python paper/manuscript/_build_rollback_v037.py
"""
import hashlib
import io
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_root(start):
    d = start
    for _ in range(8):
        if os.path.isdir(os.path.join(d, "paper", "manuscript")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("找不到项目根（应含 paper/manuscript）")


ROOT = _find_root(HERE)
PKG = os.path.join(ROOT, "_rollback", "PAI-version-v037")
OLD = os.path.join(ROOT, "_rollback", "PAI-version-v036", "pin_v036")

# v0.37 定版：本轮改写的源文件 + 图件 + 交付件 + 记录
PIN = [
    "paper/manuscript/00_manuscript_EN.md",
    "paper/manuscript/_assemble_draft_v033.py",
    "paper/manuscript/_assemble_supp_v033.py",
    "paper/manuscript/_build_docx.py",
    "paper/manuscript/_round.py",
    "paper/manuscript/_probe_v033_selfaudit.py",
    "paper/manuscript/_probe_v033_numbers.py",
    "paper/manuscript/_audit_fig_v034.py",
    "paper/manuscript/number_ignore.json",
    "paper/manuscript/claim_graph.yaml",
    "paper/manuscript/_build_rollback_v036.py",
    "paper/manuscript/_build_rollback_v037.py",
    "paper/tables/_build_v033_tables.py",
    "paper/tables/TL_literature.csv",
    "paper/tables/TC_claim_scope.csv",
    "paper/tables/T3_sim_summary.csv",
    "paper/tables/TS2_sim_detail.csv",
    "paper/tables/TS3_detection_thresholds.csv",
    "paper/figures/_plot_fig_v033_sim.py",
    "paper/figures/_plot_fig_fivechain.py",
    "paper/figures/Fig1_fivechain_panels.png",
    "paper/figures/Fig2_fivechain_profiles.png",
    "paper/figures/Fig3_sim_amplitude_twopoint.png",
    "paper/figures/Fig4_sim_detection.png",
    "paper/figures/Fig5_sim_display_cost.png",
    "paper/figures/FigS1_fivechain_panels_extra.png",
    "paper/notes/CHANGELOG_v0.36.md",
    "paper/notes/CHANGELOG_v0.37.md",
    "paper/notes/Table1_v036_refcheck.md",
    # v0.37 交付件
    "paper/manuscript/01_draft_v0.37_assembled.md",
    "paper/manuscript/02_PAI_manuscript_v0.37_draft.docx",
    "paper/manuscript/03_supplementary_v0.37.md",
    "paper/manuscript/04_PAI_supplementary_v0.37.docx",
]

# v0.36 交付件：本轮未覆盖，原样收进包里
TO_V36_DELIV = [
    "paper/manuscript/01_draft_v0.36_assembled.md",
    "paper/manuscript/02_PAI_manuscript_v0.36_draft.docx",
    "paper/manuscript/03_supplementary_v0.36.md",
    "paper/manuscript/04_PAI_supplementary_v0.36.docx",
]


def sha(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def put(rel, sub):
    src = os.path.join(ROOT, rel)
    if not os.path.isfile(src):
        print("  MISS %s" % rel)
        return None
    dst = os.path.join(PKG, sub, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    if sha(src) != sha(dst):
        raise SystemExit("复制校验失败：%s" % rel)
    return {"path": rel, "bytes": os.path.getsize(src), "sha256": sha(src)}


def put_from(src, rel, sub):
    if not os.path.isfile(src):
        print("  MISS(OLD) %s" % src)
        return None
    dst = os.path.join(PKG, sub, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    if sha(src) != sha(dst):
        raise SystemExit("复制校验失败：%s" % src)
    return {"path": rel, "bytes": os.path.getsize(src), "sha256": sha(src)}


def main():
    # 只清两个数据子目录；BEFORE.md / rollback.py 是手写件，必须保留
    for sub in ("pin_v037", "to_v036"):
        d = os.path.join(PKG, sub)
        if os.path.isdir(d):
            shutil.rmtree(d)
    os.makedirs(PKG, exist_ok=True)

    manifest = {"version": "v0.37",
                "pin_v037": [], "to_v036_deliv": [], "to_v036_src": []}

    for rel in PIN:
        e = put(rel, "pin_v037")
        if e:
            manifest["pin_v037"].append(e)
    for rel in TO_V36_DELIV:
        e = put(rel, "to_v036")
        if e:
            manifest["to_v036_deliv"].append(e)

    # 从 v0.36 包搬源文件快照
    if os.path.isdir(OLD):
        for dirpath, _dn, fns in os.walk(OLD):
            for fn in fns:
                src = os.path.join(dirpath, fn)
                rel = os.path.relpath(src, OLD).replace("\\", "/")
                e = put_from(src, rel, os.path.join("to_v036", "src"))
                if e:
                    manifest["to_v036_src"].append(e)
    else:
        print("  !! 未找到 v0.36 源快照：%s" % OLD)

    with io.open(os.path.join(PKG, "MANIFEST.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    print("== 回滚包 %s" % PKG)
    print("   pin_v037      : %d 个文件（v0.37 定版）" % len(manifest["pin_v037"]))
    print("   to_v036 deliv : %d 个文件（v0.36 交付件）" % len(manifest["to_v036_deliv"]))
    print("   to_v036 src   : %d 个文件（v0.36 源快照）" % len(manifest["to_v036_src"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
