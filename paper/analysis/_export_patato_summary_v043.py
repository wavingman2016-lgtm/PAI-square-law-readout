#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_export_patato_summary_v043.py — 把在体 (PATATO) 的汇总量从 .mat 导成 CSV。

为什么需要
----------
§4.6 引用的六个在体数值（gCNR 0.6066 / 0.9045 / 0.3134、配对差 -0.2979 / +0.2932、
Pearson 0.9992）此前只存在于 `results/study_patato/patato_check.mat`（v7.3 HDF5）。
二进制归档无法被数字溯源检查读取，等于这些数字在归档里"不存在"。

本脚本只做**搬运**：读 .mat，按原值写 CSV，不做任何重算或取舍。
零改动原 .mat；输出可 diff、可 grep。
"""
import io
import os
import csv

import h5py
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAT = os.path.join(ROOT, "results", "study_patato", "patato_check.mat")
OUT = os.path.join(ROOT, "results", "study_patato", "patato_summary.csv")


def deref(fh, ref):
    """MATLAB 把字符串存成 char 码数组（v7.3 下经 #refs# 间接引用）。

    注意不能用 `ravel()[0]` —— 那只会取到首字母的字符码（'coh' -> 99）。
    """
    try:
        v = np.array(fh[ref][()]).ravel()
        if v.dtype.kind in ("u", "i"):
            return "".join(chr(int(c)) for c in v if int(c) > 0)
        if v.dtype.kind in ("S", "U"):
            return "".join(x.decode("utf-8", "replace") if isinstance(x, bytes) else str(x)
                           for x in v)
        return str(v)
    except Exception:
        return "?"


def main():
    with h5py.File(MAT, "r") as fh:
        names = [deref(fh, r) for r in np.array(fh["metrics/names"][()]).ravel()]
        gcnr = np.array(fh["metrics/gCNR"][()]).ravel().astype(float)
        cnr = np.array(fh["metrics/CNR"][()]).ravel().astype(float)
        pearson = float(np.array(fh["band/pearson_sqlaw"][()]).ravel()[0])
        amp_ratio = float(np.array(fh["band/amp_ratio_sqlaw"][()]).ravel()[0])
        cfg = {k: float(np.array(fh["cfg/" + k][()]).ravel()[0])
               for k in ("FOV", "R", "fs", "f0", "Nx", "WL", "WW")}

    if not (len(names) == len(gcnr) == len(cnr)):
        raise SystemExit("length mismatch: names %d gCNR %d CNR %d"
                         % (len(names), len(gcnr), len(cnr)))

    rows = []
    for nm, g, c in zip(names, gcnr, cnr):
        rows.append({"chain": nm, "quantity": "gCNR", "value": "%.8f" % g, "unit": "1"})
        rows.append({"chain": nm, "quantity": "CNR", "value": "%.8f" % c, "unit": "1"})
    rows.append({"chain": "EL", "quantity": "pearson_vs_EH", "value": "%.8f" % pearson, "unit": "1"})
    rows.append({"chain": "EL", "quantity": "amp_ratio_vs_EH", "value": "%.8f" % amp_ratio, "unit": "1"})
    for k, v in cfg.items():
        rows.append({"chain": "all", "quantity": "cfg_" + k, "value": "%.8g" % v, "unit": "-"})

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        w = csv.DictWriter(fh, fieldnames=["chain", "quantity", "value", "unit"])
        w.writeheader()
        w.writerows(rows)

    print("wrote %s (%d rows)" % (os.path.relpath(OUT, ROOT), len(rows)))
    print("chains: %s" % ", ".join(names))
    print("gCNR  : %s" % ", ".join("%.6f" % g for g in gcnr))


if __name__ == "__main__":
    main()
