#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""构建 v0.42 回滚包（_rollback/PAI-version-v042/）。

结构
----
    pin_v042/   v0.42 定版：本轮源文件 + 交付件 + 表 + 图 + 记录 + PDF 校样
    to_v041/    v0.41 定版：从上一包的 pin_v041 逐字节搬运（源级快照）
    rollback.py --list / --verify / --restore
    REVERSAL_v042.md  本轮改动逐条反查表（手写，非本脚本生成）

由来
----
v0.41 的 pin_v041 与磁盘上的 v0.41 源文件逐字节一致（v0.41 包 --verify = 0 差异），
而本轮编辑直接覆盖了那些文件。所以"上一版"只能从 pin_v041 搬运，不能从磁盘取。

用法
----
    python paper/manuscript/_build_rollback_v042.py
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
PKG = os.path.join(ROOT, "_rollback", "PAI-version-v042")
PREV = os.path.join(ROOT, "_rollback", "PAI-version-v041", "pin_v041")

# ---------------------------------------------------------------- v0.42 定版
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
    "paper/manuscript/_probe_v041_bootstrap.py",
    "paper/manuscript/_probe_v042_novelty.py",
    "paper/manuscript/_audit_fig_v034.py",
    "paper/manuscript/number_ignore.json",
    "paper/manuscript/claim_graph.yaml",
    # 本轮的母本修改器与打包器（一次性，但保留以便复算）
    "paper/manuscript/_apply_v042_mother.py",
    "paper/manuscript/_build_rollback_v042.py",
    # 分析脚本与归档
    "paper/analysis/_bootstrap_a50_v041.py",
    "paper/analysis/_refcheck_v042.py",
    "results/study_detection_bootstrap.json",
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
    "paper/tables/TS4_detection_bootstrap.csv",
    # 图（脚本 + 六件 PNG + 补充图）
    "paper/figures/_plot_fig_v033_sim.py",
    "paper/figures/_plot_fig_fivechain.py",
    "paper/figures/Fig1_fivechain_panels.png",
    "paper/figures/Fig2_fivechain_profiles.png",
    "paper/figures/Fig3_sim_amplitude_twopoint.png",
    "paper/figures/Fig4_sim_detection.png",
    "paper/figures/Fig5_sim_display_cost.png",
    "paper/figures/FigS1_fivechain_panels_extra.png",
    # 记录
    "paper/notes/CHANGELOG_v0.41.md",
    "paper/notes/CHANGELOG_v0.42.md",
    "paper/notes/Table1_v036_refcheck.md",
    "paper/notes/版本规则与版本号.md",
    # v0.42 交付件
    "paper/manuscript/01_draft_v0.42_assembled.md",
    "paper/manuscript/02_PAI_manuscript_v0.42_draft.docx",
    "paper/manuscript/03_supplementary_v0.42.md",
    "paper/manuscript/04_PAI_supplementary_v0.42.docx",
    # PDF 校样
    "_proof/PAI_v042_proof.pdf",
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
    for sub in ("pin_v042", "to_v041"):
        d = os.path.join(PKG, sub)
        if os.path.isdir(d):
            shutil.rmtree(d)

    manifest = {"version": "v0.42", "pin_v042": [], "to_v041": []}

    for rel in PIN:
        e = put(rel, "pin_v042")
        if e:
            manifest["pin_v042"].append(e)

    n_prev = 0
    if os.path.isdir(PREV):
        for dirpath, _dn, fns in os.walk(PREV):
            for fn in fns:
                src = os.path.join(dirpath, fn)
                rel = os.path.relpath(src, PREV).replace("\\", "/")
                dst = os.path.join(PKG, "to_v041", rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                if sha(src) != sha(dst):
                    raise SystemExit("复制校验失败：%s" % rel)
                manifest["to_v041"].append(
                    {"path": rel, "bytes": os.path.getsize(src), "sha256": sha(src)})
                n_prev += 1
    else:
        print("  !! 未找到 v0.41 定版：%s" % PREV)

    # rollback.py：执行器逻辑与版本无关，标签硬编码，复制后按序改写。
    # 先抬 pin，再抬 to，避免后一条命中前一条刚生成的新串。
    rb_src = os.path.join(ROOT, "_rollback", "PAI-version-v041", "rollback.py")
    if os.path.isfile(rb_src):
        rb_dst = os.path.join(PKG, "rollback.py")
        txt = io.open(rb_src, "r", encoding="utf-8").read()
        txt = (txt.replace("pin_v041", "pin_v042")
                  .replace("to_v040", "to_v041")
                  .replace("v0.41 定版", "v0.42 定版")
                  .replace("v0.40 定版", "v0.41 定版")
                  .replace("v0.41 回滚包执行器", "v0.42 回滚包执行器")
                  .replace("v0.40 回滚包执行器", "v0.41 回滚包执行器"))
        io.open(rb_dst, "w", encoding="utf-8", newline="\n").write(txt)

    with io.open(os.path.join(PKG, "MANIFEST.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    print("== 回滚包 %s" % PKG)
    print("   pin_v042 : %d 个文件（v0.42 定版）" % len(manifest["pin_v042"]))
    print("   to_v041  : %d 个文件（v0.41 定版，逐字节）" % len(manifest["to_v041"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
