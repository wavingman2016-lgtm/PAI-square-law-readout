"""Five-chain panels and profiles (v0.33): Fig. 1, Fig. 2 and Fig. S1.

Reads results/fivechain/fivechain_data.mat (written by pa_study_fivechain_data.m)
and produces:
  Fig1_fivechain_panels.png     W1/W2 x C,M,EH,EL,SQ
  Fig2_fivechain_profiles.png   lateral profiles, five chains
"""
import os
import numpy as np
import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAT = os.path.join(ROOT, "results", "fivechain", "fivechain_data.mat")
OUT = os.path.dirname(__file__)

ARMS = ["C", "M", "EH", "EL", "SQ"]
LABEL = {"C": "C  coherent", "M": "M  envelope stacking",
         "EH": "EH  Hilbert sq. env.", "EL": "EL  square-lowpass",
         "SQ": "SQ  bare square"}


def load():
    f = h5py.File(MAT, "r")
    patches, prof = {}, {}
    for ds in f["patches"].keys():
        patches[ds] = {a: np.array(f["patches"][ds][a]).T for a in ARMS}
    for ds in f["profiles"].keys():
        g = f["profiles"][ds]
        d = {"x": np.array(g["x"]).ravel(), "y": np.array(g["y"]).ravel()}
        d["lat"] = {a: np.array(g["lat"][a]).ravel() for a in ARMS}
        d["axi"] = {a: np.array(g["axi"][a]).ravel() for a in ARMS}
        d["x0"] = float(np.array(g["x0"]).ravel()[0])
        d["y0"] = float(np.array(g["y0"]).ravel()[0])
        prof[ds] = d
    f.close()
    return patches, prof


def main():
    patches, prof = load()
    plt.rcParams.update({"font.size": 8, "axes.linewidth": 0.7,
                         "xtick.labelsize": 7, "ytick.labelsize": 7})

    # ---------------- panels ----------------
    rows = [ds for ds in ["W1", "W2"] if ds in patches]
    fig, axes = plt.subplots(len(rows), 5, figsize=(7.2, 1.55 * len(rows) + 0.5))
    if len(rows) == 1:
        axes = axes[None, :]
    for i, ds in enumerate(rows):
        for j, a in enumerate(ARMS):
            ax = axes[i, j]
            im = patches[ds][a]
            vlo, vhi = np.percentile(im, [1.0, 99.5])
            if vhi <= vlo:
                vlo, vhi = 0.0, max(im.max(), 1e-12)
            ax.imshow(im, cmap="gray", vmin=vlo, vmax=vhi,
                      interpolation="nearest", origin="lower")
            ax.set_xticks([]); ax.set_yticks([])
            if i == 0:
                ax.set_title(LABEL[a], fontsize=7)
            if j == 0:
                ax.set_ylabel(ds, fontsize=8)
    fig.suptitle("Five chains on the same raw recordings (each panel normalised to its own maximum)",
                 fontsize=8, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    p1 = os.path.join(OUT, "Fig1_fivechain_panels.png")
    fig.savefig(p1, dpi=300)
    plt.close(fig)

    # ---------------- profiles ----------------
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    colors = {"C": "#1f77b4", "M": "#2ca02c", "EH": "#ff7f0e",
              "EL": "#d62728", "SQ": "#7f7f7f"}
    for ds, ax in zip(["W1", "W2"], axes):
        if ds not in prof:
            continue
        d = prof[ds]
        x = d["x"] - d["x0"]
        for a in ARMS:
            y = d["lat"][a]
            y = y / (y.max() + 1e-12)
            ax.plot(x, y, lw=0.9, color=colors[a], label=a)
        ax.set_xlim(-3, 3)
        ax.set_xlabel("lateral offset from C peak (mm)")
        ax.set_ylabel("normalised amplitude")
        ax.set_title(ds, fontsize=8)
        ax.grid(alpha=0.25, lw=0.4)
    # 五链图例两面板共用一条，放到画布顶部：轴内会被 W1 的峰顶到
    # （audit_figure 的规则是图例不得落在 ax.patch 内）。
    h, lb = axes[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))
    fig.legend(h, lb, loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=5,
               frameon=False, fontsize=6.5, handlelength=1.5, columnspacing=2.0)
    p2 = os.path.join(OUT, "Fig2_fivechain_profiles.png")
    fig.savefig(p2, dpi=300)
    plt.close(fig)

    # ---------------- supplementary panels: W3-W6 ----------------
    extra = [ds for ds in ["W3", "W4", "W5", "W6"] if ds in patches]
    if extra:
        fig, axes = plt.subplots(len(extra), 5,
                                 figsize=(7.2, 1.35 * len(extra) + 0.45))
        if len(extra) == 1:
            axes = axes[None, :]
        for i, ds in enumerate(extra):
            for j, a in enumerate(ARMS):
                ax = axes[i, j]
                im = patches[ds][a]
                vlo, vhi = np.percentile(im, [1.0, 99.5])
                if vhi <= vlo:
                    vlo, vhi = 0.0, max(im.max(), 1e-12)
                ax.imshow(im, cmap="gray", vmin=vlo, vmax=vhi,
                          interpolation="nearest", origin="lower")
                ax.set_xticks([]); ax.set_yticks([])
                if i == 0:
                    ax.set_title(LABEL[a], fontsize=7)
                if j == 0:
                    ax.set_ylabel(ds, fontsize=8)
        fig.suptitle("Supplementary: five chains on W3-W6 "
                     "(each panel normalised to its own maximum)", fontsize=8, y=0.997)
        fig.tight_layout(rect=[0, 0, 1, 0.955])
        p3 = os.path.join(OUT, "FigS1_fivechain_panels_extra.png")
        fig.savefig(p3, dpi=300)
        plt.close(fig)
        print("wrote", p3)

    print("wrote", p1)
    print("wrote", p2)


if __name__ == "__main__":
    main()
