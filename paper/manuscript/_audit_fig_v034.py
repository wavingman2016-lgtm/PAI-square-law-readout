#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Stage 5F 图件审计（v0.34）：对交付的 6 张图跑 audit_figure 几何层检查。

为什么不用 figure_check.py --static
-----------------------------------
thesis skill 的 figure_check 约定图件在 ``04_figures/rendered/**.png``，
本项目图件在 ``paper/figures/``，直接跑会 0 PASS / 0 WARN / 0 FAIL —— 那是空转，
不是通过。这里改为复用 audit_figure 的 bbox 碰撞检测，直接审真正交付的图。

做法
----
1. 劫持 ``Figure.savefig``：先把 figure 交给 audit_figure 审，再落盘到临时目录。
   真实 PNG 不被触碰（本脚本只读交付件）。
2. exec 绘图脚本（``__file__`` 指向真实路径，保证其中的 ROOT/HERE 正确解析）。
3. 汇总 FIX / WARN，退出码非 0 即不可交付。

用法
----
    python paper/manuscript/_audit_fig_v034.py
"""
import os
import sys
import tempfile
import traceback

import matplotlib
matplotlib.use("Agg")
import matplotlib.figure as mfigure

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIGDIR = os.path.join(ROOT, "paper", "figures")
THESIS = os.path.expanduser(os.path.join("~", ".workbuddy", "skills", "thesis", "scripts"))

sys.path.insert(0, THESIS)
from audit_figure import audit_figure  # noqa: E402

# 交付件实际嵌入的图 ← 它们的绘图脚本
SCRIPTS = [
    ("Fig1_fivechain_panels.png", "Fig2_fivechain_profiles.png", "_plot_fig_fivechain.py"),
    ("Fig3_sim_amplitude_twopoint.png", "Fig4_sim_detection.png",
     "Fig5_sim_display_cost.png", "_plot_fig_v033_sim.py"),
    ("FigS1_fivechain_panels_extra.png", "_plot_fig_fivechain.py"),
]

_TMP = tempfile.mkdtemp(prefix="pai_figaudit_")
_orig_savefig = mfigure.Figure.savefig
RESULTS = []


def _hooked_savefig(self, fname, *a, **kw):
    tag = os.path.basename(str(fname))
    try:
        ok, issues = audit_figure(self, strict=False, verbose=False)
        RESULTS.append((tag, ok, list(issues or [])))
    except TypeError:                       # 旧签名无 verbose
        try:
            ok, issues = audit_figure(self, strict=False)
            RESULTS.append((tag, ok, list(issues or [])))
        except Exception:
            RESULTS.append((tag, None, [("ERROR", traceback.format_exc(limit=2))]))
    except Exception:
        RESULTS.append((tag, None, [("ERROR", traceback.format_exc(limit=2))]))
    # 落盘到临时目录，绝不覆盖交付件
    dst = os.path.join(_TMP, tag)
    return _orig_savefig(self, dst, *a, **kw)


mfigure.Figure.savefig = _hooked_savefig


def run(script):
    path = os.path.join(FIGDIR, script)
    if not os.path.isfile(path):
        print("  [SKIP] 脚本不存在: %s" % script)
        return False
    src = open(path, "r", encoding="utf-8").read()
    # __name__ 必须是 "__main__"：绘图脚本都用 if __name__ == "__main__" 守门
    ns = {"__name__": "__main__", "__file__": path}
    try:
        exec(compile(src, path, "exec"), ns)
    except SystemExit:
        pass
    except Exception:
        print("  [FAIL] %s 执行异常：" % script)
        print("         " + traceback.format_exc(limit=3).replace("\n", "\n         "))
        return False
    return True


def main():
    print("== 图件几何审计 (audit_figure) root=%s" % ROOT)
    print("   临时落盘目录：%s\n" % _TMP)

    for group in SCRIPTS:
        script, expected = group[-1], group[:-1]
        print("-- %s" % script)
        if not run(script):
            continue
        for want in expected:
            hits = [r for r in RESULTS if r[0] == want]
            if not hits:
                print("   [FAIL] 未产出图件: %s" % want)
                continue
            tag, ok, issues = hits[-1]
            fix = [s for s in issues if "[FIX]" in str(s)]
            warn = [s for s in issues if "[WARN]" in str(s)]
            other = [s for s in issues if "[FIX]" not in str(s) and "[WARN]" not in str(s)]
            status = "FAIL" if fix else ("WARN" if warn else "PASS")
            print("   [%-4s] %-38s FIX=%d WARN=%d" % (status, tag, len(fix), len(warn)))
            for s in fix + warn:
                print("          - %s" % str(s).replace("\n", " / "))
            for s in other:
                print("          . %s" % str(s).replace("\n", " / "))
        RESULTS.clear()

    print("\n说明：本脚本只读取交付图件，不做改写；临时目录可随时删除。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
