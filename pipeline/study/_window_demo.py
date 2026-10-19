# -*- coding: utf-8 -*-
"""窗口技术演示 + 展示效果量化（只读；渲染属显示域）。
从统一管线产出的能量图（IM/sqlaw）出发：
  ① 量化「显示完整性 / 视觉清晰度 / 可读性」；
  ② 对照 legacy 固定窗 vs 分位数自适应窗；
  ③ 输出可直接进 Supplement 的图与表。
"""
import h5py, numpy as np, matplotlib, csv
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
for _f in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"):
    try:
        fm.fontManager.addfont(_f)
    except Exception:
        pass
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

CASES = [("W1 · 单丝（点）", "results/wire/W1_single/W1_results.mat"),
         ("W3 · X 形线（长丝）", "results/recheck/W3_fov60/W3_results.mat")]

FIXED = [("全范围（基线）", 0.50, 1.00),
         ("窄细节窗", 0.25, 0.50),
         ("平衡窗（legacy 默认）", 0.40, 0.50),
         ("宽动态窗", 0.35, 0.80)]


def load_energy(mat):
    with h5py.File(mat, "r") as f:
        IE = np.array(f["IM"]["sqlaw"]).T
        ax = np.array(f["axRow"]).ravel()
        mc = f["Mcol"]["sqlaw"]
        gcnr, cnr = float(mc["gCNR"][0, 0]), float(mc["CNR"][0, 0])
    IE = IE - min(IE.min(), 0)
    return IE / IE.max(), ax, gcnr, cnr


def win_metrics(IE, WL, WW, label):
    """三项展示指标（+两项辅助）。全部定义在数据域的分位数上，因而可跨数据集迁移。"""
    lo, hi = WL - WW / 2, WL + WW / 2
    p50, p90, p99, p999 = np.percentile(IE, [50, 90, 99, 99.9])
    struct = IE >= p99                       # 结构像素（能量前 1%）
    bg = IE < p50                            # 背景像素（后 50%）
    # ① 显示完整性：结构未被裁掉/饱和的比例
    structure_visible = float(np.mean((struct & (IE >= lo)) ) / max(np.mean(struct), 1e-9))
    # ② 视觉清晰度：有效位深增益（8-bit 下落在窗内的灰阶数 / 全量程灰阶数）
    bitgain = 1.0 / WW
    # ③ 可读性：信息区间 [p50,p99.9] 落在窗内的比例
    a, b = max(p50, lo), min(p999, hi)
    readable = float(max(0.0, b - a) / max(p999 - p50, 1e-9))
    # 辅助：背景裁除率（越高 = 背景越干净，但过高会丢失弱结构）
    bg_removed = float(np.mean((bg & (IE < lo))) / max(np.mean(bg), 1e-9))
    return dict(window=label, WL=round(WL, 3), WW=round(WW, 3),
                lo=round(lo, 4), hi=round(hi, 4),
                structure_visible=round(structure_visible, 4),
                bitdepth_gain=round(bitgain, 3),
                readable_frac=round(readable, 4),
                bg_removed=round(bg_removed, 4),
                clipped_black_frac=round(float(np.mean(IE < lo)), 4))


def adaptive_window(IE):
    """分位数自适应：下界 = p50，上界 = p99.9 → 50% 像素在窗内、全部结构落入窗内。"""
    p50, p999 = np.percentile(IE, [50, 99.9])
    lo, hi = p50, p999
    return (lo + hi) / 2, (hi - lo)


def main():
    rows, figs = [], {}
    print("=" * 100)
    for tag, mat in CASES:
        IE, ax, gcnr, cnr = load_energy(mat)
        figs[tag] = (IE, ax, gcnr, cnr)
        print("\n### %s   数据域 gCNR=%.4f  CNR=%.3f" % (tag, gcnr, cnr))
        for name, WL, WW in FIXED:
            m = win_metrics(IE, WL, WW, name); m.update(dataset=tag); rows.append(m)
            print("  %-22s WL=%.2f WW=%.2f | 结构可见 %5.1f%% | 位深增益 %4.2fx | 信息保留 %5.1f%% | 背景裁除 %5.1f%%"
                  % (name, WL, WW, 100 * m["structure_visible"], m["bitdepth_gain"],
                     100 * m["readable_frac"], 100 * m["bg_removed"]))
        WL, WW = adaptive_window(IE)
        m = win_metrics(IE, WL, WW, "★分位数自适应（推荐）"); m.update(dataset=tag); rows.append(m)
        print("  %-22s WL=%.2f WW=%.2f | 结构可见 %5.1f%% | 位深增益 %4.2fx | 信息保留 %5.1f%% | 背景裁除 %5.1f%%"
              % ("★分位数自适应（推荐）", WL, WW, 100 * m["structure_visible"], m["bitdepth_gain"],
                 100 * m["readable_frac"], 100 * m["bg_removed"]))
    print("=" * 100)

    with open("results/supp/window_table.csv", "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("saved results/supp/window_table.csv")

    # ---- 渲染：全范围 / 窄细节 / legacy 平衡 / 宽动态 / 推荐 ----
    tag = "W3 · X 形线（长丝）"
    IE, ax, gcnr, cnr = figs[tag]
    aWL, aWW = adaptive_window(IE)
    panels = FIXED + [("★分位数自适应（推荐）", aWL, aWW)]
    fig, axs = plt.subplots(1, 5, figsize=(23.5, 5.0))
    for a, (name, WL, WW) in zip(axs, panels):
        u = np.clip((IE - (WL - WW / 2)) / WW, 0, 1)
        a.imshow(u, cmap="inferno", vmin=0, vmax=1, extent=[ax[0], ax[-1], ax[-1], ax[0]])
        blk = 100 * np.mean(IE < WL - WW / 2)
        a.set_title("%s\nWL=%.3f, WW=%.3f  [%.3f, %.3f]\n裁黑 %.1f%%"
                    % (name, WL, WW, WL - WW / 2, WL + WW / 2, blk),
                    fontsize=10, fontweight="bold",
                    color=("#c0392b" if blk > 50 else "black"))
        a.set_xlabel("x (mm)"); a.set_ylabel("y (mm)")
    fig.suptitle("图 11 · 窗口技术演示（统一管线重出，Arm E 能量图；data4, FOV=60 mm）\n"
                 "同一张数据域图像、五档 CT 式窗：gCNR=%.4f 与 CNR=%.1f 在各档**相同**（指标在数据域算）；"
                 "前三档为 legacy 固定值，末档为分位数自适应" % (gcnr, cnr),
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig("results/supp/S2_windowing.png", dpi=125)
    print("saved results/supp/S2_windowing.png")


if __name__ == "__main__":
    main()
