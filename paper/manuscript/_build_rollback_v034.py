#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""构建 v0.34 回滚包（_rollback/PAI-version-v034/）。

为什么用"复制 + 哈希清单"而不是逆操作
------------------------------------
v0.33.1 那轮用的是逐条逆操作（每处字符串替换反向执行并断言命中次数）。本轮不适用：

  * 改动面是全文级的（术语统一、摘要重写、文献整体重编号、两张表进出），
    不是十几个可枚举的替换；
  * `~/.workbuddy/file-history/` 里没有干净的 v0.33 源文件快照 —— 实测各版本
    时间与版本号不单调，且本轮最新的内容尚未入历史（当前装配脚本含 `"TL"` 键，
    历史里 3 个版本全部没有）。

因此本包分两层，各自精确：
  pin_v034/     当前 v0.34 源码与图件的字节级定版 —— 后续任何改动可整体退回这里
  to_v033/      v0.33 的四个交付件（装配稿 md / 主稿 docx / 补充 md / 补充 docx），
                本轮从未覆盖它们，字节级就是 v0.33 原样

用法
----
    python paper/manuscript/_build_rollback_v034.py
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
PKG = os.path.join(ROOT, "_rollback", "PAI-version-v034")

# v0.34 定版：本轮新增或改写的源文件与图件
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
    "paper/tables/_build_v033_tables.py",
    "paper/figures/_plot_fig_v033_sim.py",
    "paper/figures/_plot_fig_fivechain.py",
    "paper/figures/Fig2_fivechain_profiles.png",
    "paper/figures/Fig3_sim_amplitude_twopoint.png",
    "paper/figures/Fig4_sim_detection.png",
    "paper/figures/Fig5_sim_display_cost.png",
    # v0.34 交付件
    "paper/manuscript/01_draft_v0.34_assembled.md",
    "paper/manuscript/02_PAI_manuscript_v0.34_draft.docx",
    "paper/manuscript/03_supplementary_v0.34.md",
    "paper/manuscript/04_PAI_supplementary_v0.34.docx",
]

# v0.33 交付件：本轮未覆盖，原样收进包里
TO_V33 = [
    "paper/manuscript/01_draft_v0.33_assembled.md",
    "paper/manuscript/02_PAI_manuscript_v0.33_draft.docx",
    "paper/manuscript/03_supplementary_v0.33.md",
    "paper/manuscript/04_PAI_supplementary_v0.33.docx",
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
    # 只清两个数据子目录：BEFORE.md / rollback.py 是手写件，删了包就不可用
    # （v0.31 踩过一次：rmtree(PKG) 把包内自己的脚本删掉）。
    for sub in ("pin_v034", "to_v033"):
        d = os.path.join(PKG, sub)
        if os.path.isdir(d):
            shutil.rmtree(d)
    os.makedirs(PKG, exist_ok=True)

    manifest = {"version": "v0.34", "pin_v034": [], "to_v033": []}
    for rel in PIN:
        e = put(rel, "pin_v034")
        if e:
            manifest["pin_v034"].append(e)
    for rel in TO_V33:
        e = put(rel, "to_v033")
        if e:
            manifest["to_v033"].append(e)

    with io.open(os.path.join(PKG, "MANIFEST.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    print("== 回滚包 %s" % PKG)
    print("   pin_v034 : %d 个文件（v0.34 定版）" % len(manifest["pin_v034"]))
    print("   to_v033  : %d 个文件（v0.33 交付件）" % len(manifest["to_v033"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
