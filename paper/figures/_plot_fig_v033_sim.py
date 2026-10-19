#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Figures 3-5 of v0.33, from results/fivechain/fivechain_sim.csv.

Fig3_sim_amplitude_twopoint.png  (a) amplitude ladder  (b) dip at 1:1  (c) dip at 4:1
Fig4_sim_detection.png           (a) Pd vs amplitude  (b) Pd difference from C
Fig5_sim_display_cost.png        (a) window rules     (b) timing decomposition
"""
import csv
import io
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CSV = os.path.join(ROOT, "results", "fivechain", "fivechain_sim.csv")

ARMS = ["C", "M", "EH", "EL", "SQ"]
COL = {"C": "#1f77b4", "M": "#2ca02c", "EH": "#ff7f0e", "EL": "#d62728", "SQ": "#7f7f7f"}
MK = {"C": "o", "M": "s", "EH": "^", "EL": "D", "SQ": "v"}


def load():
    d = {}
    with io.open(CSV, "r", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            try:
                v = float(r["value"])
            except (ValueError, KeyError):
                v = np.nan
            d[(r["exp"], r["arm"], r["condition"], r["metric"])] = v
    return d


def g(d, exp, arm, cond, metric):
    return d.get((exp, arm, cond, metric), np.nan)


def fig3(d):
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.45))

    # (a) amplitude ladder
    amps = [0.25, 0.5, 1.0, 2.0, 4.0]
    ax = axes[0]
    for a in ARMS:
        y = [g(d, "A", a, "a=%.2f" % x, "peak") for x in amps]
        ax.plot(amps, y, marker=MK[a], ms=3.2, lw=0.9, color=COL[a], label=a)
    ax.set_xscale("log"); ax.set_yscale("log")
    # 显式刻度：log 轴的自动标签在这个窄面板里会叠成 "3x10^-1 1.0^1 1.0^2 ..." 的乱码。
    ax.set_xticks(amps)
    ax.set_xticklabels(["0.25", "0.5", "1", "2", "4"])
    ax.minorticks_off()
    ax.set_xlabel("input amplitude $a$ (rel.)")
    ax.set_ylabel("peak value (a.u.)")
    ax.set_title("(a) amplitude ladder", fontsize=8)
    ax.grid(alpha=0.25, lw=0.4, which="both")

    # (b),(c) dip vs separation
    ds = [0.40, 0.50, 0.60, 0.80, 1.00, 1.50, 2.00]
    for ax, ratio, tag in ((axes[1], "1:1", "(b) dip, 1:1"), (axes[2], "4:1", "(c) dip, 4:1")):
        for a in ARMS:
            y, e = [], []
            for x in ds:
                cond = "r=%s,d=%.2fmm" % (ratio, x)
                y.append(g(d, "B", a, cond, "dip"))
                e.append(g(d, "B", a, cond, "dip_sd"))
            y = np.array(y); e = np.array(e)
            ax.errorbar(ds, y, yerr=e, marker=MK[a], ms=2.8, lw=0.9,
                        color=COL[a], label=a, capsize=1.2, elinewidth=0.6)
        ax.axhline(0.05, ls=":", lw=0.7, color="0.4")
        ax.axhline(0.20, ls="--", lw=0.7, color="0.4")
        ax.set_xlabel("separation (mm)")
        ax.set_ylabel("dip depth")
        ax.set_title(tag, fontsize=8)
        ax.set_ylim(-0.03, 1.0)
        ax.grid(alpha=0.25, lw=0.4)
    axes[2].text(1.55, 0.06, "5%", fontsize=5.5, color="0.35")
    axes[2].text(1.55, 0.22, "20%", fontsize=5.5, color="0.35")

    # 一条图例统管三个面板：轴内图例在 (a) 的对数坐标里必然压到曲线，
    # 且三个面板共用同一组五链，重复三次没有信息增益。
    h, lb = axes[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))
    fig.legend(h, lb, loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=5,
               frameon=False, fontsize=6.5, handlelength=1.5, columnspacing=2.0)
    p = os.path.join(HERE, "Fig3_sim_amplitude_twopoint.png")
    fig.savefig(p, dpi=300); plt.close(fig)
    print("wrote", p)


def _amp_axis(d):
    """检测轴的 (标签, 数值) 对，按数值升序。

    标签一律取 CSV 里的原样字符串。不要在这里用 "a=%.2f" % x 重新拼——0.005 会被
    写成 a=0.01，与真正的 a=0.01 撞成同一个键（MATLAB 侧踩过一次，这里不再重复）。
    """
    labels = sorted({k[2][2:] for k in d
                     if k[0] == "C" and k[3] == "Pd_fpr5" and k[2].startswith("a=")},
                    key=float)
    return labels, [float(s) for s in labels]


def fig4(d):
    labels, amps = _amp_axis(d)
    if not labels:
        print("Fig4: no C-block data, skipped")   # 控制台提示，不进图；用英文免触发 C5
        return
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.5))
    for a in ARMS:
        y = [g(d, "C", a, "a=" + s, "Pd_fpr5") for s in labels]
        e = [g(d, "C", a, "a=" + s, "Pd_sd") for s in labels]
        axes[0].errorbar(amps, y, yerr=e, marker=MK[a], ms=3.2, lw=0.9,
                         color=COL[a], label=a, capsize=1.4, elinewidth=0.6)
        a50 = g(d, "C", a, "all", "a50")
        if a50 == a50:
            axes[0].plot([a50], [0.5], marker="|", ms=8, color=COL[a], mew=1.2)
    axes[0].axhline(0.5, ls=":", lw=0.7, color="0.4")
    axes[0].set_xscale("log")
    axes[0].set_xlabel("target amplitude $a$ (rel.)")
    axes[0].set_ylabel("$P_d$ at 5% false-alarm rate")
    axes[0].set_title("(a) detection at a fixed false-alarm rate", fontsize=8)
    axes[0].set_ylim(-0.03, 1.05)
    axes[0].grid(alpha=0.25, lw=0.4, which="both")

    base = [g(d, "C", "C", "a=" + s, "Pd_fpr5") for s in labels]
    for a in ARMS:
        y = [g(d, "C", a, "a=" + s, "Pd_fpr5") - b for s, b in zip(labels, base)]
        axes[1].plot(amps, y, marker=MK[a], ms=3.0, lw=0.9, color=COL[a], label=a)
    axes[1].axhline(0, lw=0.7, color="0.3")
    axes[1].set_xscale("log")
    # 0.02 以上五链一律 Pd=1.00：逐点画出来只会在右侧摊出一片平台，
    # 把有信息的 2e-4–1e-2 压成一条竖线。收窄横轴，平台用文字说明。
    for ax in axes:
        ax.set_xlim(1.4e-4, 2.6e-2)
    axes[0].text(0.98, 0.06, "all chains $P_d=1.00$\nfor $a\\geq0.02$",
                 transform=axes[0].transAxes, ha="right", va="bottom",
                 fontsize=5.2, color="0.3", linespacing=1.3)
    axes[1].set_xlabel("target amplitude $a$ (rel.)")
    axes[1].set_ylabel("$\\Delta P_d$ vs coherent")
    axes[1].set_title("(b) difference from the coherent baseline", fontsize=8)
    axes[1].grid(alpha=0.25, lw=0.4, which="both")

    h, lb = axes[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))
    fig.legend(h, lb, loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=5,
               frameon=False, fontsize=6.5, handlelength=1.5, columnspacing=2.0)
    p = os.path.join(HERE, "Fig4_sim_detection.png")
    fig.savefig(p, dpi=300); plt.close(fig)
    print("wrote", p)


def fig5(d):
    """Fig. 5 — display and cost.

    v0.45: same data, same bar widths and same axis ticks as v0.44; only the
    canvas, the spacing and the annotation layer change.  The per-bar
    "sat x% / blk y%" micro-labels are replaced by one note in the empty
    upper-left quadrant, so nothing is set at 4 pt any more.
    """
    plt.rcParams.update({
        "font.size": 8.6,
        "axes.labelsize": 9.6,
        "axes.titlesize": 9.8,
        "xtick.labelsize": 8.6,
        "ytick.labelsize": 8.6,
        "legend.fontsize": 7.0,
    })
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.72),
                             gridspec_kw={"wspace": 0.30})

    # (a) window rules ---------------------------------------------------
    rules = ["fixed", "percentile", "dual"]
    arms = ["M", "EH", "EL"]
    w = 0.26
    ax = axes[0]
    roles = {"M": "M envelope", "EH": "EH sq. env.", "EL": "EL sq.-lowpass"}
    sat_non, blk_non = [], []
    for i, a in enumerate(arms):
        vals = []
        for r in rules:
            cond = "r=4:1,d=1.0mm,%s" % r
            vals.append(g(d, "D", a, cond, "weak_display_contrast"))
            s_ = g(d, "D", a, cond, "saturated_frac")
            b_ = g(d, "D", a, cond, "black_frac")
            if r != "fixed":
                if s_ == s_:
                    sat_non.append(s_)
                if b_ == b_:
                    blk_non.append(b_)
        x = np.arange(len(rules)) + (i - 1) * w
        ax.bar(x, vals, width=w * 0.92, color=COL[a], alpha=0.85, label=roles[a])

    ax.set_xticks(np.arange(len(rules)))
    ax.set_xticklabels(["fixed\n(WL .15/WW .70)", "percentile\n(1-99%)",
                        "dual\n(median split)"])
    ax.set_ylabel("weak-target display contrast", labelpad=8)
    ax.set_ylim(0, 1.28)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_title("(a) window rule, 4:1 targets at 1.0 mm", pad=10)
    ax.grid(alpha=0.25, lw=0.5, axis="y")
    ax.tick_params(axis="y", pad=6, length=3.5)
    ax.tick_params(axis="x", pad=4, length=0)

    # One note instead of three micro-labels per group; sits in the empty
    # band 0.75-1.0 where no bar reaches (tallest is 0.37).
    note = ("Note: fixed window sat 100%% / blk 0%%;\n"
            "non-fixed rules sat %d%% / blk %d-%d%%." %
            (round(100 * min(sat_non)), round(100 * min(blk_non)),
             round(100 * max(blk_non))))
    ax.text(0.025, 0.965, note, transform=ax.transAxes, ha="left", va="top",
            fontsize=7.4, color="0.15", linespacing=1.65)

    # (b) timing decomposition -------------------------------------------
    ax = axes[1]
    stages = [("tPre", "pre-processing"), ("tHilbert", "Hilbert"),
              ("tEnv", "envelope $|z|$"), ("tEnv2", "squared env. $|z|^2$"),
              ("tSquare", "square $x^2$"), ("tLPF", "low-pass"),
              ("tBP_real", "BP (real)"), ("tBP_complex", "BP (complex)")]
    chains = {
        "C": ["tPre", "tHilbert", "tBP_complex"],
        "M": ["tPre", "tHilbert", "tEnv", "tBP_real"],
        "EH": ["tPre", "tHilbert", "tEnv2", "tBP_real"],
        "EL": ["tPre", "tSquare", "tLPF", "tBP_real"],
    }
    sval = {k: g(d, "E", "all", "timing", k) for k, _ in stages}
    palette = {"tPre": "#cccccc", "tHilbert": "#1f77b4", "tEnv": "#2ca02c",
               "tEnv2": "#98df8a", "tSquare": "#d62728", "tLPF": "#ff9896",
               "tBP_real": "#7f7f7f", "tBP_complex": "#ff7f0e"}
    names = list(chains.keys())
    bottom = np.zeros(len(names))
    for k, lab in stages:
        vals = np.array([sval.get(k, np.nan) if k in chains[c] else 0.0 for c in names])
        vals = np.nan_to_num(vals)
        ax.bar(names, vals, bottom=bottom, color=palette[k], label=lab, width=0.62)
        bottom += vals
    ax.set_ylabel("time per pass (s)", labelpad=8)
    ax.set_title("(b) end-to-end time decomposition", pad=10)
    ax.grid(alpha=0.25, lw=0.5, axis="y")
    ax.tick_params(axis="y", pad=6, length=3.5)
    ax.tick_params(axis="x", pad=4, length=0)

    r_e2e = g(d, "E", "EL", "timing", "ratio_EL_over_M")
    r_env = g(d, "E", "EL", "timing", "env_stage_ratio_EL_over_M")
    sh = g(d, "E", "EL", "timing", "bp_share_of_e2e")
    if r_e2e == r_e2e and r_env == r_env:
        txt = ("EL/M, end-to-end  %.3f\nEL/M, detection only  %.3f" % (r_e2e, r_env)
               + ("\nBP share of EL total  %.0f%%" % (100 * sh) if sh == sh else ""))
        # Moved to the empty upper-right corner and given a light frame so it
        # never sits on a grid line or on the EL bar.
        ax.text(0.972, 0.965, txt, transform=ax.transAxes, fontsize=7.4,
                va="top", ha="right", color="0.12", linespacing=1.75,
                bbox=dict(boxstyle="round,pad=0.45", facecolor="white",
                          edgecolor="0.65", linewidth=0.6, alpha=0.92))

    # Legends: same entries, more air between rows and columns.
    h1, l1 = axes[0].get_legend_handles_labels()
    h2, l2 = axes[1].get_legend_handles_labels()
    # tight_layout does not reserve room for figure-level legends, so the
    # margins are set explicitly: the top band holds the two legend blocks and
    # the panel titles are drawn below it.
    fig.subplots_adjust(left=0.098, right=0.985, bottom=0.125, top=0.795,
                        wspace=0.30)
    fig.legend(h1, l1, loc="upper left", bbox_to_anchor=(0.006, 0.995), ncol=3,
               frameon=False, fontsize=7.2, handlelength=1.6,
               columnspacing=2.2, handletextpad=0.7)
    fig.legend(h2, l2, loc="upper right", bbox_to_anchor=(0.994, 0.995), ncol=4,
               frameon=False, fontsize=6.8, handlelength=1.6,
               columnspacing=1.9, handletextpad=0.6, labelspacing=1.2)
    p = os.path.join(HERE, "Fig5_sim_display_cost.png")
    fig.savefig(p, dpi=300); plt.close(fig)
    print("wrote", p)


def main():
    if not os.path.exists(CSV):
        print("missing %s" % CSV)
        return 1
    d = load()
    print("loaded %d keys" % len(d))
    fig3(d)
    fig4(d)
    fig5(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
