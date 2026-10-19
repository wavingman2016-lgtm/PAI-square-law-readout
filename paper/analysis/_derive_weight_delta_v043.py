#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_derive_weight_delta_v043.py — 从权重敏感性归档导出"相对 M 的配对差"。

为什么需要
----------
§4.4 引用六个配对差（W2/W3/W5 × 三种权重），它们是 `gCNR(arm) - gCNR(M)`，
不是归档 CSV 里的任何单元格，因此数字溯源检查判为"找不到出处"。
本脚本把差值**作为归档正式导出**，并在表头写清公式 —— 而不是把它们
加进豁免台账（台账的规矩是"不能复现的才进"）。

输入：results/fivechain/fivechain_weight_sensitivity.csv（只读）
输出：results/fivechain/fivechain_weight_sensitivity_delta.csv
"""
import io
import os
import csv

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "results", "fivechain", "fivechain_weight_sensitivity.csv")
OUT = os.path.join(ROOT, "results", "fivechain", "fivechain_weight_sensitivity_delta.csv")

ARMS = ("EL2", "EL1", "EL0")
# 正文只引可测数据集；W1/W4/W6 饱和（gCNR=1.0000，差为 0），一并导出以便对账
DATASETS = ("W1", "W2", "W3", "W4", "W5", "W6")


def main():
    val = {}
    with io.open(SRC, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if row["metric"] == "gcnr2d":
                val[(row["dataset"], row["arm"])] = float(row["value"])

    rows = []
    for ds in DATASETS:
        if (ds, "M") not in val:
            continue
        base = val[(ds, "M")]
        for a in ARMS:
            if (ds, a) not in val:
                continue
            d = val[(ds, a)] - base
            rows.append({"dataset": ds, "arm": a, "metric": "gcnr2d_delta_vs_M",
                         # value = 正文引用的报告精度（4 位小数）；value_full = 原值
                         "value": "%.4f" % d,
                         "value_full": "%.8f" % d,
                         "unit": "1",
                         "formula": "gCNR(%s) - gCNR(M)" % a})

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        w = csv.DictWriter(fh, fieldnames=["dataset", "arm", "metric", "value",
                                           "value_full", "unit", "formula"])
        w.writeheader()
        w.writerows(rows)

    print("wrote %s (%d rows)" % (os.path.relpath(OUT, ROOT), len(rows)))
    for ds in ("W2", "W3", "W5"):
        got = ["%+.4f" % float(r["value"]) for r in rows if r["dataset"] == ds]
        print("  %s: %s" % (ds, " ".join(got)))


if __name__ == "__main__":
    main()
