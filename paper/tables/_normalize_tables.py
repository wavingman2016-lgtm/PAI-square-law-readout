#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一次性表规范化：英文化 + 生成「可读视图」。

背景
----
1. 若干源 CSV 的自由文本单元格里含**中文**（`subject` / `cfg_used` / 窗口名），
   会被渲染进 DOCX 正文 —— 投稿阻断级（常驻检查器 C1）。
2. `Table03`（20 列）/ `Table02`（23 列）把**内部溯源列**与**机器精度浮点**
   直接倒进了正文，评审不可读。
3. `Table01`（文献对比）的最后一列是一条**起草注**，不该进正文表。

设计
----
* **原始 CSV 仍是单一真相源**：本脚本只做「译文」与「消除错位」，不删数据。
* **正文只读「可读视图」**（`*_readable.csv`），与 `TableS1_audit_readable.csv`
  同一模式 —— 装配脚本指向视图，正文不手工抄数。
* 输出一律走 `csv.writer`（自动加引号），从此不再出现未转义逗号导致的列错位。

用法::
    python _normalize_tables.py --check   # 只报告，不写
    python _normalize_tables.py           # 落盘
"""
import argparse
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CJK = re.compile(r"[\u4e00-\u9fff]")

# ------------------------------------------------------------------ 译文表
# 逐值精确映射（避免子串替换误伤）。键是**原文逐字**。
CELL_MAP = {
    # --- Table03 subject ---
    "单根细长钨丝（点状吸收体）": "single thin tungsten wire (point-like absorber)",
    "两根并排细钨丝（双点）": "two parallel thin tungsten wires (double point)",
    "X 形交叉长丝（线状）": "X-shaped crossed filament (line target)",
    "交叉线状结构（V 形；32 通道旋转扫描，物体身份未证实）":
        "crossed filament (V-shaped; 32-channel rotational scan, target identity not confirmed)",
    "旋转 200 步（无历史归档，本轮首次判定）":
        "rotational scan, 200 steps (no archived history; first adjudication here)",
    "环形/管状仿体（静态重复采集 1440 次，非旋转；32 通道）":
        "ring / tube phantom (static, 1440 repeats, non-rotational; 32 channels)",
    # --- FigS2 window ---
    "全范围（基线）": "full range (baseline)",
    "窄细节窗": "narrow-detail window",
    "平衡窗（legacy 默认）": "balanced window (legacy default)",
    "宽动态窗": "wide-dynamic-range window",
    "★分位数自适应（推荐）": "quantile-adaptive (recommended)",
    "分位数自适应（推荐）": "quantile-adaptive (recommended)",
    # --- FigS2 dataset ---
    "W1 · 单丝（点）": "W1 · single wire (point)",
    "W3 · X 形线（长丝）": "W3 · X-shaped crossed filament",
    # --- TableS1 softFail 判据句 ---
    "Q4 目标填满/超出成像视场（放大 FOV 或裁剪 ROI 后复评）":
        "Q4 target fills or exceeds the field of view (re-assess after enlarging the FOV or cropping the ROI)",
    "Q8 标称-实测中心频率不一致（首要怀疑配置，而非方法）":
        "Q8 nominal-measured band-centre mismatch (suspect the configuration first, not the method)",
}

# 逐单元格的子串替换（用于 `validated_config` 这类模板句）
SUB_MAP = [
    ("默认：", "default: "),
    ("默认", "default"),
    ("实测带中心", "measured band centre"),
    ("实测", "measured"),
]


def translate(s):
    s = s.strip()
    if s in CELL_MAP:
        return CELL_MAP[s]
    for a, b in SUB_MAP:
        s = s.replace(a, b)
    return s


def read_rows(p):
    with io.open(p, encoding="utf-8-sig", newline="") as fh:
        return [r for r in csv.reader(fh) if any(c.strip() for c in r)]


def write_rows(p, rows):
    with io.open(p, "w", encoding="utf-8-sig", newline="") as fh:
        csv.writer(fh).writerows(rows)


def num(x, sig=4):
    """机器精度浮点 -> sig 位有效数字（评审可读）。非数字原样返回。"""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return x
    if v == 0:
        return "0"
    return "%g" % float("%.*g" % (sig, v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只报告，不写盘")
    args = ap.parse_args()
    check = args.check
    rep = []

    # ---------------------------------------------------- 1) 源 CSV 英文化
    targets = ["Table03_registry.csv", "Table02_ablation_summary.csv",
               "TableS1_config_audit.csv", "FigS2_windowing_table.csv"]
    for fn in targets:
        p = os.path.join(HERE, fn)
        if not os.path.exists(p):
            rep.append("MISSING %s" % fn)
            continue
        rows = read_rows(p)
        n = 0
        for r in rows:
            for i, c in enumerate(r):
                if CJK.search(c):
                    r[i] = translate(c)
                    n += 1
        still = sum(len(CJK.findall(c)) for r in rows for c in r)
        rep.append("%-34s 译 %2d 格；残留中文 %d" % (fn, n, still))
        if not check and n:
            write_rows(p, rows)

    # ------------------------------------------- 2) Table03 可读视图（9 列）
    rows = read_rows(os.path.join(HERE, "Table03_registry.csv"))
    h = rows[0]
    idx = {k: h.index(k) for k in h}
    out = [["id", "dataset", "target", "geometry", "verified configuration",
            "verdict", "dCNR", "dgCNR", "native-domain DR diff. (dB)"]]
    for r in rows[1:]:
        geom = "%s, R = %s mm, %s steps, fs = %s MHz" % (
            r[idx["array"]], r[idx["radius_mm"]], r[idx["rateorsteps"]], r[idx["sample_fs_MHz"]])
        out.append([r[idx["id"]], r[idx["data"]], r[idx["subject"]], geom,
                    r[idx["validated_config"]], r[idx["verdict"]],
                    r[idx["dCNR"]], r[idx["dgCNR"]], r[idx["DR_gain_dB"]]])
    rep.append("Table03_registry_readable.csv      %d 行 x %d 列（原 20 列）" % (len(out), len(out[0])))
    if not check:
        write_rows(os.path.join(HERE, "Table03_registry_readable.csv"), out)

    # ------------------------------- 3) Table02 可读视图（转置：13 行 x 7 列）
    rows = read_rows(os.path.join(HERE, "Table02_ablation_summary.csv"))
    h = rows[0]
    ids = [r[0] for r in rows[1:]]
    body = {r[0]: r for r in rows[1:]}
    c = {k: h.index(k) for k in h}
    METRICS = [
        ("verified configuration", "cfg_used", None),
        ("f0 (MHz)", "f0_used_MHz", None),
        ("apparent width aFWHM (mm) — D1 linear envelope", "aFWHM_D1", 3),
        ("apparent width aFWHM (mm) — D1² squared envelope (Hilbert)", "aFWHM_D1sq", 3),
        ("apparent width aFWHM (mm) — D2′ squared envelope (Hilbert-free, this work)", "aFWHM_D2p", 3),
        ("apparent width aFWHM (mm) — D2 bare square", "aFWHM_D2", 3),
        ("gCNR — D1", "gCNR_D1", 4),
        ("gCNR — D1²", "gCNR_D1sq", 4),
        ("gCNR — D2′ (this work)", "gCNR_D2p", 4),
        ("gCNR — D2", "gCNR_D2", 4),
        ("ΔgCNR (D2′ − D1²)  Hilbert-free equivalence", "dgCNR_D2p_vs_D1sq", 4),
        ("ΔgCNR (D2′ − D2)   band-limiting is necessary", "dgCNR_D2p_vs_D2", 4),
    ]
    out = [["quantity"] + ids]
    for label, col, sig in METRICS:
        row = [label]
        for i in ids:
            v = body[i][c[col]] if col in c and c[col] < len(body[i]) else ""
            row.append(v if sig is None else num(v, sig))
        out.append(row)
    rep.append("Table02_ablation_readable.csv      %d 行 x %d 列（原 23 列；CNR 列移出）" % (len(out), len(out[0])))
    if not check:
        write_rows(os.path.join(HERE, "Table02_ablation_readable.csv"), out)

    # ------------------------- 4) Table01：删起草注列 + 表头改可读英文词组
    p5 = os.path.join(HERE, "Table01_literature_comparison.csv")
    rows = read_rows(p5)
    h = rows[0]
    drop = "position_ours"
    HEAD = {
        "id": "id",
        "family": "method family",
        "representative_work": "representative work",
        "per_channel_operation": "operation applied per channel",
        "analytic_signal_required": "analytic signal required?",
        "geometric_compensation": "geometric compensation",
        "output_domain": "output domain",
        "reported_metrics": "metrics reported there",
        "ref_keys": "ref. key",
    }
    keep = [k for k in h if k != drop]
    out = [[HEAD.get(k, k) for k in keep]]
    for r in rows[1:]:
        out.append([r[h.index(k)] for k in keep])
    moved = [r[h.index(drop)] for r in rows[1:]] if drop in h else []
    rep.append("Table01_literature_comparison.csv  删 %r 列（%d 条起草注需改写进正文）" % (drop, len(moved)))
    if not check:
        write_rows(p5, out)
        # ⚠ 幂等性：`position_ours` 列第一次已删除，此后 `moved` 恒为空。
        #   若无条件重写，第二次运行就会把**已有存档清空**（实测事故：11 条起草注
        #   被覆盖成只剩标题）。故仅在真有内容搬出时才写，否则保持不动。
        if moved:
            with io.open(os.path.join(HERE, "_Table01_moved_notes.md"), "w",
                         encoding="utf-8", newline="\n") as fh:
                fh.write("# Table 1 删掉的 `position_ours` 起草注（待改写进 §1.2 正文）\n\n")
                for r, m in zip(rows[1:], moved):
                    fh.write("- **%s** (%s) — %s\n" % (r[0], r[2], m))
        else:
            rep.append("_Table01_moved_notes.md          保持不动（无列可搬，避免清空存档）")

    # ------------------- 5) Table S2 可读视图（3 列，4~7 位有效数字）
    # 源 `FigS1_equiv_table.csv` 是 `pipeline/study/pa_supp_equiv.m` 输出
    # `results/supp/S1_equiv_table.csv`（9 列）的**入库副本**（只取前 5 列），
    # **保持原样**：本目录不手工改数、不改机器精度。
    # ⚠ 无脚本生成该副本 ⇒ **重跑 `pa_supp_equiv.m` 后必须重新复制**，否则二者
    # 静默分叉。（2026-10-16 核对：入库副本前 5 列与源逐位一致，印刷表数值未受影响。）
    # 读者视图只保留三列并压到可读位数。
    # 源里的 `oneMinusRelSE_vs_img2` = 1 − ||I_E^consist − I_M²||²/||I_M²||²，是一个
    # **正文未解释**的辅助量，且 W1 上为 −0.565（负值来自 I_M² 的背景偏置，而非几何
    # 失配，Pearson 仍为 0.99999）—— 放进读者表会被误读成"失配"，故不展示。
    p_equiv = os.path.join(HERE, "FigS1_equiv_table.csv")
    rows = read_rows(p_equiv)
    if rows:
        h = rows[0]
        c = {k: h.index(k) for k in h}
        out = [["dataset", "worst-case relative residual", "relative L2 error",
                "Pearson correlation"]]
        for r in rows[1:]:
            out.append([r[c["spec"]], num(r[c["relmax"]], 3), num(r[c["relL2"]], 3),
                        num(r[c["pearson"]], 7)])
        rep.append("FigS1_equiv_readable.csv            %d 行 x %d 列（原 5 列；去掉未解释列）"
                   % (len(out), len(out[0])))
        if not check:
            write_rows(os.path.join(HERE, "FigS1_equiv_readable.csv"), out)

    print("=== _normalize_tables.py %s ===" % ("(check)" if check else "(written)"))
    for x in rep:
        print("  " + x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
