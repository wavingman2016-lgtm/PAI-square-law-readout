#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""构建 v0.39 回滚包（_rollback/PAI-version-v039/）。

结构
----
    pin_v039/   v0.39 定版：本轮源文件 + 交付件 + 表 + 图 + 记录
    to_v037/    v0.37 定版：整份搬运，是逐字节的上一冻结件（33 个文件）
    rollback.py --list / --verify / --restore
    REVERSAL_v039.md  本轮改动逐条反查表（手写，非本脚本生成）

不提供 to_v038/
---------------
v0.38 是评审读到的那一版，但在升版前被同名重建覆盖，磁盘上已无原始字节。
写一个名为 to_v038 的目录会让回退者误以为拿到了评审版本，因此改为提供
反查表。`to_v037/` 的字节完整性由 MANIFEST 的 sha256 保证。

用法
----
    python paper/manuscript/_build_rollback_v039.py
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
PKG = os.path.join(ROOT, "_rollback", "PAI-version-v039")
V37 = os.path.join(ROOT, "_rollback", "PAI-version-v037", "pin_v037")

# ---------------------------------------------------------------- v0.39 定版
PIN = [
    # 母本与管线
    "paper/manuscript/00_manuscript_EN.md",
    "paper/manuscript/_assemble_draft_v033.py",
    "paper/manuscript/_assemble_supp_v033.py",
    "paper/manuscript/_build_docx.py",
    "paper/manuscript/_round.py",
    "paper/manuscript/_quality_gates.py",
    "paper/manuscript/_probe_v033_selfaudit.py",
    "paper/manuscript/_probe_v033_numbers.py",
    "paper/manuscript/_audit_fig_v034.py",
    "paper/manuscript/number_ignore.json",
    "paper/manuscript/claim_graph.yaml",
    "paper/manuscript/_build_rollback_v039.py",
    # 表（生成器 + 生成物）
    "paper/tables/_build_v033_tables.py",
    "paper/tables/TL_literature.csv",
    "paper/tables/T1_chains.csv",
    "paper/tables/T2_datasets.csv",
    "paper/tables/T3_sim_summary.csv",
    "paper/tables/T4_morphology.csv",
    "paper/tables/T5_detection.csv",
    "paper/tables/TC_claim_scope.csv",
    "paper/tables/TS1_equivalence.csv",
    "paper/tables/TS2_sim_detail.csv",
    "paper/tables/TS3_detection_thresholds.csv",
    # 图（脚本 + 六件 PNG）
    "paper/figures/_plot_fig_v033_sim.py",
    "paper/figures/_plot_fig_fivechain.py",
    "paper/figures/Fig1_fivechain_panels.png",
    "paper/figures/Fig2_fivechain_profiles.png",
    "paper/figures/Fig3_sim_amplitude_twopoint.png",
    "paper/figures/Fig4_sim_detection.png",
    "paper/figures/Fig5_sim_display_cost.png",
    "paper/figures/FigS1_fivechain_panels_extra.png",
    # 记录
    "paper/notes/CHANGELOG_v0.37.md",
    "paper/notes/CHANGELOG_v0.39.md",
    "paper/notes/Table1_v036_refcheck.md",
    "paper/notes/版本规则与版本号.md",
    # v0.39 交付件
    "paper/manuscript/01_draft_v0.39_assembled.md",
    "paper/manuscript/02_PAI_manuscript_v0.39_draft.docx",
    "paper/manuscript/03_supplementary_v0.39.md",
    "paper/manuscript/04_PAI_supplementary_v0.39.docx",
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


def main():
    os.makedirs(PKG, exist_ok=True)
    for sub in ("pin_v039", "to_v037"):
        d = os.path.join(PKG, sub)
        if os.path.isdir(d):
            shutil.rmtree(d)

    manifest = {"version": "v0.39", "pin_v039": [], "to_v037": []}

    for rel in PIN:
        e = put(rel, "pin_v039")
        if e:
            manifest["pin_v039"].append(e)

    if os.path.isdir(V37):
        for dirpath, _dn, fns in os.walk(V37):
            for fn in fns:
                src = os.path.join(dirpath, fn)
                rel = os.path.relpath(src, V37).replace("\\", "/")
                dst = os.path.join(PKG, "to_v037", rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                if sha(src) != sha(dst):
                    raise SystemExit("复制校验失败：%s" % rel)
                manifest["to_v037"].append(
                    {"path": rel, "bytes": os.path.getsize(src), "sha256": sha(src)})
    else:
        print("  !! 未找到 v0.37 定版：%s" % V37)

    with io.open(os.path.join(PKG, "MANIFEST.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    print("== 回滚包 %s" % PKG)
    print("   pin_v039 : %d 个文件（v0.39 定版）" % len(manifest["pin_v039"]))
    print("   to_v037  : %d 个文件（v0.37 定版，逐字节）" % len(manifest["to_v037"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
