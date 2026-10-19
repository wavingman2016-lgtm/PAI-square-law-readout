# -*- coding: utf-8 -*-
"""
Fig. 1 — Schematic: one shared pre-processing chain, three detection arms.

Produces paper/figures/Fig01_schematic.png (and results/figs/Fig01_schematic.png).

Revision (v0.19) — implements the reviewer's Fig. 1 points
----------------------------------------------------------
Reviewer points addressed (from `论文稿图表优化与审稿意见.docx`, Fig. 1 section):

* "Panel (a) 左下角两个圆角矩形悬空放置，没有箭头与主干流程相连"
  → the two floating boxes are **removed**. The pre-conditions are folded onto the
    top chain (a brace over the DC-removal and band-pass stages, labelled
    "mandatory preconditions for squaring: β = B/f0 < 1"); the shared grid becomes
    a **base plate running under the three arm branches**.
* "副标题中的 (F1–F4 enforced) 在读者尚未读到 §3 时属于不知所云的缩写"
  → the internal code is **removed** from the subtitle.
* "Panel (b) 像幻灯片讲义：大段纯文字加一行公式，缺乏视觉化的图形支撑"
  → panel (b) is redrawn as a short text column plus two sketches:
      (i)  detector geometry & spherical spreading (R, element distance
           d_m = ||r - r_m||, p ∝ 1/d_m);
      (ii) spectrum after squaring (baseband [0, B] vs the double-frequency band
           [2 f1, 2 f2], separated by the low-pass cut-off) — the visual reading of β < 1.
* "留白过多，结构松散"
  → the three arms are laid out side by side under the chain instead of stacked,
    so the panel has no empty quadrant.

Design notes
------------
* Journal figure: white background, dark text, vector-friendly layout.
* The ONLY inter-arm difference is the detection operator (and its matched
  geometric compensation) — the visual counterpart of manuscript §2.1 (three
  estimators, one kernel) and §2.4 (single compensation rule).
* Schematic only — no fabricated data: every symbol is the one defined in the
  manuscript, and the two sketches are drawn from the geometry/spectrum
  definitions, never from a measurement.
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Arc, Polygon

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["mathtext.fontset"] = "dejavusans"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = [os.path.join(ROOT, "paper", "figures", "Fig01_schematic.png"),
       os.path.join(ROOT, "results", "figs", "Fig01_schematic.png")]

INK, GREY = "#1a1a1a", "#5f6b76"
C_C, C_M, C_E = "#2f6db5", "#b5732f", "#b52f3d"
BOX, EDGE = "#f4f6f8", "#9aa5b1"
PLATE, PLATE_E = "#eceff3", "#c3ccd6"

fig = plt.figure(figsize=(11.0, 7.2), dpi=300)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 110)
ax.set_ylim(-25, 72)
ax.axis("off")


def box(x, y, w, h, text, fc=BOX, ec=EDGE, fs=9.0, tc=INK, lw=1.0, rad=0.6, z=2):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle=f"round,pad=0.25,rounding_size={rad}",
                                linewidth=lw, edgecolor=ec, facecolor=fc, zorder=z))
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs, color=tc, zorder=z + 1, linespacing=1.35)


def arrow(x1, y1, x2, y2, color=GREY, lw=1.4, rad=0.0, z=1):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=11, linewidth=lw, color=color,
                                 zorder=z, connectionstyle=f"arc3,rad={rad}"))


def line(xs, ys, color=GREY, lw=1.2, z=1, ls="-"):
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, zorder=z, solid_joinstyle="round")


def brace(x0, x1, yb, h, color=GREY, lw=1.1):
    """Curly brace spanning [x0, x1]; tips touch yb, peak reaches yb+h."""
    xm = 0.5 * (x0 + x1)
    line([x0, x0, xm - 1.4, xm, xm + 1.4, x1, x1],
         [yb, yb + 0.5 * h, yb + 0.5 * h, yb + h, yb + 0.5 * h, yb + 0.5 * h, yb],
         color=color, lw=lw, z=3)


# ================================================================== panel (a)
ax.text(3.0, 70.4, "(a)  One shared pre-processing chain", fontsize=12,
        fontweight="bold", color=INK)
ax.text(3.0, 67.8,
        "the three arms differ only in the detection operator and its matched compensation",
        fontsize=8.8, color=GREY)

Y0, H = 56.0, 5.6
CY = Y0 + H / 2
box(3.0, Y0, 31.0, H, "Raw channel data   $x_m(t),\\; m=1\\ldots M$", fs=9.0)
arrow(34.0, CY, 37.0, CY)
box(37.0, Y0, 31.0, H, "Per-channel DC removal", fs=9.0)
arrow(68.0, CY, 71.0, CY)
box(71.0, Y0, 31.0, H, "Zero-phase band-pass", fs=9.0)

# pre-conditions folded onto the chain, under one brace
brace(37.0, 102.0, Y0 + H + 0.9, 2.4, lw=1.3)
ax.text(69.5, Y0 + H + 3.9, r"mandatory preconditions for squaring:   $\beta=B/f_0<1$",
        ha="center", va="bottom", fontsize=8.4, color=GREY)
ax.text(71.0, Y0 - 1.6, r"set from the $\mathbf{measured}$ centre, not the nominal $f_0$",
        ha="left", fontsize=7.4, color=GREY, style="italic")

# node and fan-out bus
node = (104.0, CY)
ax.plot([node[0]], [node[1]], marker="o", ms=3.8, color=INK, zorder=5)
BUSY = 52.0
line([104.0, 104.0], [CY, BUSY], color=GREY, lw=1.3)
line([104.0, 19.0], [BUSY, BUSY], color=GREY, lw=1.3)

# shared base plate under the three branches
PLX0, PLY0, PLX1, PLY1 = 1.0, 33.2, 109.6, 47.8
ax.add_patch(FancyBboxPatch((PLX0, PLY0), PLX1 - PLX0, PLY1 - PLY0,
                            boxstyle="round,pad=0.2,rounding_size=0.8",
                            linewidth=1.0, edgecolor=PLATE_E, facecolor=PLATE, zorder=0.5))
ax.text(0.5 * (PLX0 + PLX1), 34.5,
        r"shared reconstruction grid $\cdot$ field of view $\cdot$ pixel pitch $\cdot$ kernel"
        "   —   identical for the three arms",
        ha="center", va="center", fontsize=8.2, color=GREY, zorder=1)

arms = [
    (C_C, 2.0, 34.0, 19.0, "Arm C  —  coherent back-projection",
     r"$z_m=\mathcal{H}\{x_m\}$" + "   →   " + r"$I_C=\left|\sum_m g_m z_m\right|$",
     r"compensation $g_m=d_m/R$   $\cdot$   domain: pressure amplitude"),
    (C_M, 38.0, 34.0, 55.0, "Arm M  —  envelope stacking",
     r"$z_m=\mathcal{H}\{x_m\}$" + "   →   " + r"$I_M=\sum_m g_m\,|z_m|$",
     r"compensation $g_m=d_m/R$   $\cdot$   domain: pressure amplitude"),
    (C_E, 74.0, 34.0, 91.0, "Arm E  —  squared envelope (this work)",
     r"$\mathrm{LPF}\{x_m^2\}=\frac{1}{2}|z_m|^2$" + "   →   " + r"$I_E=\sum_m (g_m\,|z_m|)^2$",
     r"compensation $g_m=d_m/R$   $\cdot$   domain: acoustic energy density"),
]
AY0, AH = 36.0, 10.0
for col, ax0, aw, acx, title, expr, sub in arms:
    arrow(acx, BUSY, acx, AY0 + AH, color=col, lw=1.3)
    box(ax0, AY0, aw, AH, "", fc="#ffffff", ec=col, lw=1.5, z=2)
    ax.text(acx, AY0 + 7.4, title, fontsize=8.8, color=col, fontweight="bold",
            ha="center", va="center", zorder=3)
    ax.text(acx, AY0 + 4.9, expr, fontsize=9.0, color=INK, ha="center", va="center", zorder=3)
    ax.text(acx, AY0 + 2.2, sub, fontsize=7.3, color=GREY, ha="center", va="center", zorder=3)

# ================================================================== panel (b)
ax.plot([0.8, 109.2], [26.6, 26.6], lw=0.8, color="#d7dde3", zorder=0)
ax.text(3.0, 24.2, "(b)  Why a single geometric compensation rule suffices",
        fontsize=12, fontweight="bold", color=INK)

# ----- left: the argument ------------------------------------------------------
ax.text(3.0, 21.0,
        r"$g_m=d_m/R$ restores the $1/r$ decay of pressure; the energy estimator",
        fontsize=8.8, color=INK)
ax.text(3.0, 18.5,
        r"needs $g_m^2$ and inherits it automatically, because $p\propto 1/r\;\Rightarrow\;p^2\propto 1/r^2$:",
        fontsize=8.8, color=INK)
ax.text(3.0, 13.6, r"$\sum_m (g_m|z_m|)^2 \;\equiv\; \sum_m g_m^2\,|z_m|^2$",
        fontsize=12.5, color=C_E)
ax.text(3.0, 10.1, r"(algebraically identical; measured Pearson 0.999996)",
        fontsize=8.2, color=GREY)
ax.text(3.0, 7.8,
        r"$\Rightarrow$ the alternative $r^2$ form is a numerical convenience, not a second model.",
        fontsize=8.8, color=INK)
ax.text(3.0, 4.8,
        r"Hilbert-free equivalence:  $\mathrm{LPF}\{x^2\}=\frac{1}{2}|z|^2$,  valid whenever $\beta=B/f_0<1$.",
        fontsize=8.8, color="#2f7a3c")

# ----- inset (i): geometry & spherical spreading -------------------------------
ax.text(55.0, 20.6, "(i)  geometry  &  spherical spreading", fontsize=8.4, color=GREY)

cx, cy, R = 63.5, 3.6, 9.5
ax.add_patch(Arc((cx, cy), 2 * R, 2 * R, angle=0, theta1=0, theta2=180,
                 linewidth=1.1, color=INK, zorder=3))
line([cx - R, cx + R], [cy, cy], color=GREY, lw=0.8, ls=(0, (4, 3)), z=1)

angs = np.linspace(15, 165, 7)
ax.plot(cx + R * np.cos(np.radians(angs)), cy + R * np.sin(np.radians(angs)),
        ls="none", marker="o", ms=3.0, color=INK, zorder=4)

th = np.radians(30)
xm_, ym_ = cx + R * np.cos(th), cy + R * np.sin(th)
rx_, ry_ = cx, 11.0                                        # reconstruction point r
line([cx, xm_], [cy, ym_], color=GREY, lw=1.0, z=2)               # radius R
line([xm_, rx_], [ym_, ry_], color=C_E, lw=1.3, z=4)              # element -> r
ax.plot([rx_], [ry_], marker="o", ms=4.0, color=C_E, zorder=5)
ax.text(67.2, 5.7, r"$R$", fontsize=8.6, color=GREY)
ax.text(66.2, 10.15, r"$d_m=\Vert r-r_m\Vert$", fontsize=8.2, color=C_E)
ax.text(rx_ - 0.6, ry_ + 0.55, r"$r$", fontsize=8.6, color=C_E, ha="right")
ax.text(xm_ + 0.45, ym_ - 0.55, r"$r_m$", fontsize=8.2, color=INK)
ax.text(55.0, 1.35, r"spherical spreading $p\propto 1/d_m$", fontsize=8.0, color=GREY)

# ----- inset (ii): spectrum after squaring -------------------------------------
ax.text(83.0, 20.6, "(ii)  spectrum after squaring", fontsize=8.4, color=GREY)

ox, oy, xmax, ymax = 84.0, 4.2, 108.0, 16.4
line([ox, xmax], [oy, oy], color=INK, lw=1.0, z=2)
line([ox, ox], [oy, ymax], color=INK, lw=1.0, z=2)

ax.add_patch(Polygon([[86.0, oy], [89.0, 14.0], [92.0, oy]], closed=True,
                     facecolor="#cfd9e6", edgecolor=C_C, lw=1.1, zorder=3))
ax.add_patch(Polygon([[97.5, oy], [101.5, 10.2], [105.5, oy]], closed=True,
                     facecolor="#f0dcc8", edgecolor=C_M, lw=1.1, zorder=3))
line([94.8, 94.8], [oy, ymax + 0.2], color=C_E, lw=1.1, ls=(0, (4, 3)), z=4)

ax.text(89.0, 14.5, r"base band $[0,B]$", fontsize=7.5, color=C_C, ha="center")
ax.text(102.0, 11.4, r"double band $[2f_1,2f_2]$", fontsize=7.2, color=C_M, ha="center")
ax.text(94.3, 11.4, "LPF cut-off", fontsize=7.0, color=C_E, rotation=90,
        ha="center", va="center")
ax.text(ox - 0.4, ymax + 0.9, r"$|X^2(f)|$", fontsize=8.2, color=INK, ha="left")
ax.text(xmax, oy - 2.4, "frequency →", fontsize=7.6, color=GREY, ha="right")

# ================================================================== panel (c)
GREEN = "#2f7a3c"
RED   = "#b03a2e"


def chain(y, steps, tag, tagcol):
    """Draw one horizontal operator chain; steps = [(label, kind), ...]."""
    x = 3.0
    for i, (lab, kind) in enumerate(steps):
        w = 12.5 if kind == "io" else 11.0
        fc = {"io": "#ffffff", "op": BOX, "hilb": "#e8eef7", "lp": "#eef7ee"}[kind]
        ec = {"io": EDGE, "op": tagcol, "hilb": "#3b6ea5", "lp": GREEN}[kind]
        box(x, y, w, 4.4, lab, fc=fc, ec=ec, fs=7.6, lw=1.1, rad=0.5, z=3)
        x += w
        if i < len(steps) - 1:
            arrow(x + 0.3, y + 2.2, x + 3.7, y + 2.2, color=GREY, lw=1.1, z=3)
            x += 4.2
    ax.text(x + 1.6, y + 2.2, tag, fontsize=7.2, color=tagcol, va="center")


ax.plot([0.8, 109.2], [-1.6, -1.6], lw=0.8, color="#d7dde3", zorder=0)
ax.text(3.0, -4.6,
        "(c)  One estimator, two equivalent realizations — and the bare square, which is not one of them",
        fontsize=11.0, fontweight="bold", color=INK)
ax.text(3.0, -6.4,
        r"rows 1–2 give the same image ($\mathrm{LPF}\{x^2\}=\frac{1}{2}|z|^2$ for $\beta<1$; the global factor $\frac{1}{2}$"
        r" is absorbed by normalisation)  —  the band-limiting of row 2 is mandatory; omitting it is row 3.",
        fontsize=8.0, color=GREY)

chain(-11.8,
      [(r"$x_m(t)$", "io"),
       (r"Hilbert, $|\cdot|$", "hilb"),
       (r"$\times\,g_m$", "op"),
       (r"$(\;)^2$", "op"),
       (r"$\sum_m$", "op")],
      r"envelope route  (production default)", GREEN)

chain(-17.2,
      [(r"$x_m(t)$", "io"),
       (r"$(\;)^2$", "op"),
       (r"LPF", "lp"),
       (r"$\times\,g_m^2$", "op"),
       (r"$\sum_m$", "op")],
      r"square-and-low-pass route  (Hilbert-free realization)", GREEN)

chain(-22.6,
      [(r"$x_m(t)$", "io"),
       (r"$(\;)^2$", "op"),
       (r"$\sum_m$", "op")],
      r"bare square: the $2f_0$ term is retained — split peak, spurious dark bands  (counter-example, NOT this work)",
      RED)

for p in OUT:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fig.savefig(p, dpi=300, facecolor="white", bbox_inches="tight", pad_inches=0.08)
    print("wrote", p)
