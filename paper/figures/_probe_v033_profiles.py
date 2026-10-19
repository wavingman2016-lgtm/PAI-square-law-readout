# -*- coding: utf-8 -*-
"""从 fivechain_data.mat 复算剖面/图块类指标，并落盘为可追溯的 CSV。

为什么单独写这个脚本
====================
正文 §4.2 引用了两类数字，它们既不在 registry 也不在任何表里：

  (i) W2 在 ±3 mm 处的裙边高度（占各自最大值的百分比）—— 来自 lateral profile；
 (ii) W5 整幅 18 mm 视场内归一化图块的中位数 —— 来自 2D patch，**不是**剖面中位数。

第二类曾差点被误判为"写错"：用剖面中位数复算是 0.895/0.713/0.713/0.242，
而正文写 0.905/0.832/0.832/0.363。换成 2D patch 中位数后逐位复现。
把口径与数值一起固化到 CSV，下一轮就不必再凭记忆重建这条链。

用法：python paper/figures/_probe_v033_profiles.py
输出：results/fivechain/profile_metrics.csv
"""
import csv
import os
import sys

import h5py
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MAT = os.path.join(ROOT, "results", "fivechain", "fivechain_data.mat")
OUT = os.path.join(ROOT, "results", "fivechain", "profile_metrics.csv")

ARMS = ["C", "M", "EH", "EL", "SQ"]
DATASETS = ["W1", "W2", "W3", "W4", "W5", "W6"]


def main():
    if not os.path.isfile(MAT):
        print("找不到 %s" % MAT)
        return 2

    rows = []
    with h5py.File(MAT, "r") as f:
        for ds in DATASETS:
            if "profiles" not in f or ds not in f["profiles"]:
                continue
            for plane in ("lat", "axi"):
                g = f["profiles"][ds][plane]
                x = f["profiles"][ds]["x"][:, 0]
                i = int(np.argmax(g["C"][0, :]))
                px = x[i]
                for arm in ARMS:
                    v = g[arm][0, :]
                    vmax = v.max()
                    for off, tag in ((-3.0, "minus3mm"), (3.0, "plus3mm")):
                        j = int(np.argmin(np.abs(x - (px + off))))
                        rows.append([ds, plane, arm,
                                     "skirt_%s_pct_of_max" % tag,
                                     "%.4f" % (100.0 * v[j] / vmax)])
            if "patches" in f and ds in f["patches"]:
                p = f["patches"][ds]
                for arm in ARMS:
                    v = p[arm][()]
                    rows.append([ds, "patch2d", arm, "patch_median_norm",
                                 "%.4f" % float(np.median(v / v.max()))])

            # 峰值位置（供 §4.2 说明"剖面沿几何中心而非各链自身最大值"）
            for arm in ARMS:
                g = f["profiles"][ds]["lat"]
                x = f["profiles"][ds]["x"][:, 0]
                rows.append([ds, "lat", arm, "profile_peak_x_mm",
                             "%.4f" % float(x[int(np.argmax(g[arm][0, :]))])])

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["dataset", "plane", "arm", "metric", "value"])
        w.writerows(rows)
    print("写出 %s（%d 行）" % (os.path.relpath(OUT, ROOT), len(rows)))

    # 自检：正文引用的四个 W5 图块中位数与 W2 裙边必须复现
    def get(ds, plane, arm, metric):
        for r in rows:
            if r[0] == ds and r[1] == plane and r[2] == arm and r[3] == metric:
                return float(r[4])
        return None

    checks = [
        ("W5 patch median M", 0.905, get("W5", "patch2d", "M", "patch_median_norm"), 3),
        ("W5 patch median EH", 0.832, get("W5", "patch2d", "EH", "patch_median_norm"), 3),
        ("W5 patch median EL", 0.832, get("W5", "patch2d", "EL", "patch_median_norm"), 3),
        ("W5 patch median C", 0.363, get("W5", "patch2d", "C", "patch_median_norm"), 3),
        ("W2 skirt M at -3 mm", 36.1, get("W2", "lat", "M", "skirt_minus3mm_pct_of_max"), 1),
        ("W2 skirt M at +3 mm", 43.6, get("W2", "lat", "M", "skirt_plus3mm_pct_of_max"), 1),
        ("W2 skirt EL at -3 mm", 13.4, get("W2", "lat", "EL", "skirt_minus3mm_pct_of_max"), 1),
        ("W2 skirt EL at +3 mm", 28.1, get("W2", "lat", "EL", "skirt_plus3mm_pct_of_max"), 1),
        ("W2 skirt C at -3 mm", 2.6, get("W2", "lat", "C", "skirt_minus3mm_pct_of_max"), 1),
        ("W2 skirt C at +3 mm", 3.6, get("W2", "lat", "C", "skirt_plus3mm_pct_of_max"), 1),
    ]
    bad = 0
    print("\n=== 自检：正文引用值 vs 复算值 ===")
    for name, want, got, dec in checks:
        if got is None:
            print("  MISSING  %-26s" % name)
            bad += 1
            continue
        ok = round(got, dec) == round(want, dec)
        print("  %-7s %-26s want %-8s got %.4f" % ("OK" if ok else "FAIL", name, want, got))
        if not ok:
            bad += 1
    print("\nVERDICT:", "PASS" if bad == 0 else "FAIL")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
