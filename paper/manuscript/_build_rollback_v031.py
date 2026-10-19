# -*- coding: utf-8 -*-
"""Build the one-click rollback package for PAI v0.30 -> v0.31.

    python paper/manuscript/_build_rollback_v031.py

Produces _rollback/PAI-version-v031/ with
  BEFORE/     the pre-round (v0.30) state of every file this round MODIFIED
  rollback.py one-click restore (--dry-run to preview)
  README.md   what changed, what to do
  PROVENANCE.md  where every BEFORE copy came from (fhist version / snapshot)

Provenance of the BEFORE copies
-------------------------------
  00_manuscript_EN.md      fhist @v3   10-17 19:43   status header says "draft v0.30"
  _assemble_draft.py       fhist @v1   10-17 21:25   still writes "Core evidence" and
                                                     OUT = 01_draft_v0.30_assembled.md
  TableS1_config_audit.csv fhist @v1   10-17 23:16   still says "Nx raised 601 -> 1501"
  _build_docx.py           on-disk copy (audit only) -- this round changed NOTHING but the
                                                     version string (v0.30 -> v0.31; the file
                                                     is byte-size identical to its v0.18-era
                                                     history entry, 28379 B), so rollback
                                                     rewrites the string instead of restoring.

Idempotent: re-running overwrites the package in place.
"""
import io
import os
import shutil
import subprocess
import sys

def _find_root(start):
    """Locate the project root by walking up until paper/manuscript exists.

    Needed because the package keeps a copy of this builder (build_rollback.py)
    and that copy must still resolve to the real project root, not to
    _rollback/PAI-version-v031.
    """
    d = os.path.dirname(os.path.abspath(start))
    while True:
        if os.path.isdir(os.path.join(d, "paper", "manuscript")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise SystemExit("cannot locate project root from %s" % start)
        d = parent


ROOT = _find_root(__file__)                                  # <repo root>
HERE = os.path.join(ROOT, "paper", "manuscript")
PKG = os.path.join(ROOT, "_rollback", "PAI-version-v031")
FHIST = os.path.join(os.path.expanduser("~"), ".workbuddy", "tools", "fhist.py")  # external helper, not shipped

PY = sys.executable

# rel path -> (source kind, locator)
BEFORE = {
    "paper/manuscript/00_manuscript_EN.md": ("fhist", "3"),
    "paper/manuscript/_assemble_draft.py": ("fhist", "1"),
    "paper/tables/TableS1_config_audit.csv": ("fhist", "1"),
    "paper/manuscript/_build_docx.py": ("disk", None),       # audit copy; rollback rewrites
}

# v0.31 additions, relative to ROOT. Deliberately NOT deleted: the analysis
# scripts under pipeline/study and their archived outputs under results/ -- an
# archive must not lose provenance just because a draft is rolled back.
DELETE = [
    "paper/manuscript/01_draft_v0.31_assembled.md",
    "paper/manuscript/02_PAI_manuscript_v0.31_draft.docx",
    "paper/manuscript/_probe_v031_selfaudit.py",
    "paper/manuscript/_probe_v031_carriers.py",
    "paper/manuscript/_diag_v031.py",
    "paper/tables/TableS6_estimator_sensitivity.csv",
    "paper/tables/TableS7_ring_audit.csv",
    "paper/notes/CHANGELOG_v0.31.md",
    "paper/notes/投稿前验收清单_v0.31.md",
    "paper/notes/评审裁定_v0.31.md",
    "paper/notes/_review_round8_raw.md",
    "paper/figures/_plot_figS4_roi_audit.py",
    "paper/figures/FigS4_roi_audit.png",
    "paper/manuscript/_build_rollback_v031.py",
]


def grab(rel, kind, loc):
    """Return the text of the pre-round version of `rel`."""
    if kind == "disk":
        with io.open(os.path.join(ROOT, rel.replace("/", os.sep)), encoding="utf-8") as f:
            return f.read()
    out = subprocess.check_output(
        [PY, FHIST, "show", os.path.join(ROOT, rel.replace("/", os.sep)), "--v", loc],
        stderr=subprocess.STDOUT)
    txt = out.decode("utf-8", "replace")
    # fhist prefixes a banner line; strip it
    marker = "===== "
    if txt.startswith(marker):
        txt = txt.split("\n", 1)[1]
    return txt


SELF = os.path.abspath(__file__)


def main():
    # read our own source BEFORE wiping the package: when this builder is the
    # in-package copy (build_rollback.py), rmtree(PKG) would delete it
    self_text = io.open(SELF, encoding="utf-8").read() if os.path.exists(SELF) else None

    if os.path.isdir(PKG):
        shutil.rmtree(PKG)
    os.makedirs(PKG)

    print("PAI rollback package  v0.31 -> v0.30")
    for rel, (kind, loc) in BEFORE.items():
        dst = os.path.join(PKG, "BEFORE", rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        txt = grab(rel, kind, loc)
        with io.open(dst, "w", encoding="utf-8", newline="") as f:
            f.write(txt)
        print("  BEFORE  %-48s %7d B  (%s)" % (rel, len(txt.encode("utf-8")),
                                               "fhist v" + loc if kind == "fhist" else "on-disk"))

    # sanity assertions -- a rollback package that restores the wrong thing is
    # worse than no package at all
    ms = io.open(os.path.join(PKG, "BEFORE", "paper", "manuscript",
                              "00_manuscript_EN.md"), encoding="utf-8").read()
    ad = io.open(os.path.join(PKG, "BEFORE", "paper", "manuscript",
                              "_assemble_draft.py"), encoding="utf-8").read()
    t1 = io.open(os.path.join(PKG, "BEFORE", "paper", "tables",
                              "TableS1_config_audit.csv"), encoding="utf-8").read()
    assert "draft **v0.30**" in ms, "BEFORE master is not the v0.30 state"
    assert "v0.31 changelog" not in ms, "BEFORE master already carries v0.31 changelog"
    assert "Core evidence" in ad, "BEFORE assembler is not the v0.30 state"
    assert "01_draft_v0.30_assembled.md" in ad, "BEFORE assembler lost the v0.30 output name"
    assert "Nx raised 601 -> 1501" in t1, "BEFORE TableS1 lost the pre-fix grid wording"
    print("  assertions on BEFORE content: all 5 OK")

    with io.open(os.path.join(PKG, "rollback.py"), "w", encoding="utf-8") as f:
        f.write(ROLLBACK_PY)
    # keep a copy of the builder inside the package: rollback.py deletes the live
    # one, and without this the package could never be rebuilt after a rollback
    if self_text:
        with io.open(os.path.join(PKG, "build_rollback.py"), "w",
                     encoding="utf-8", newline="") as f:
            f.write(self_text)
    with io.open(os.path.join(PKG, "README.md"), "w", encoding="utf-8") as f:
        f.write(README)
    with io.open(os.path.join(PKG, "PROVENANCE.md"), "w", encoding="utf-8") as f:
        f.write(PROV)

    print("  wrote rollback.py / README.md / PROVENANCE.md")
    print("\npackage: %s" % PKG)


ROLLBACK_PY = '''# -*- coding: utf-8 -*-
"""PAI v0.31 -> v0.30 one-click rollback.

Restores the three files this round modified to their v0.30-final state, rewrites
the version string in _build_docx.py, and deletes the v0.31-only artifacts.

    python rollback.py --dry-run    # list the actions, change nothing
    python rollback.py              # execute (idempotent)

NOT deleted on purpose: the analysis scripts under pipeline/study/ and their
archived outputs under results/ (planB_sensitivity.*, planB_roi_audit.*,
e4c_perconfig.*).  An archive must not lose provenance because a draft is rolled
back; delete those by hand if you really want to.

After rolling back, rebuild the v0.30 deliverables with
    python paper/manuscript/_round.py
"""
import io
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))       # _rollback/PAI-version-v031
ROOT = os.path.dirname(os.path.dirname(HERE))            # <repo root>

RESTORE = [
    "paper/manuscript/00_manuscript_EN.md",
    "paper/manuscript/_assemble_draft.py",
    "paper/tables/TableS1_config_audit.csv",
]

# _build_docx.py differs from its v0.30 state ONLY in the version string
# (same byte length, 28379 B, as its pre-v0.31 history entry), so it is
# rewritten instead of restored.
REWRITE_VER = "paper/manuscript/_build_docx.py"

DELETE = %r

dry = "--dry-run" in sys.argv
acts = len(RESTORE) + 1 + len(DELETE)
print("PAI rollback v0.31 -> v0.30  (%%d actions)%%s" %% (acts, "  [DRY RUN]" if dry else ""))

for rel in RESTORE:
    src = os.path.join(HERE, "BEFORE", rel.replace("/", os.sep))
    dst = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(src):
        print("  MISSING BEFORE  %%s" %% rel)
        continue
    print("  restore   %%s" %% rel)
    if not dry:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

dst = os.path.join(ROOT, REWRITE_VER.replace("/", os.sep))
if os.path.exists(dst):
    txt = io.open(dst, encoding="utf-8").read()
    n = txt.count("v0.31")
    print("  rewrite   %%s   (%%d occurrence(s) v0.31 -> v0.30)" %% (REWRITE_VER, n))
    if not dry:
        io.open(dst, "w", encoding="utf-8", newline="").write(txt.replace("v0.31", "v0.30"))
else:
    print("  MISSING   %%s" %% REWRITE_VER)

for rel in DELETE:
    dst = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(dst):
        print("  absent    %%s" %% rel)
        continue
    print("  delete    %%s" %% rel)
    if not dry:
        os.remove(dst)

print("\\n%%s" %% ("dry run complete; nothing written" if dry
                else "done. now re-run: python paper/manuscript/_round.py"))
''' % (DELETE,)


README = """# PAI v0.31 —— 回滚包

把 v0.31（第八轮评审处置）退回 v0.30（第七轮后版本）。

## 用法

```bat
python _rollback\\PAI-version-v031\\rollback.py --dry-run   :: 只看动作，不写盘
python _rollback\\PAI-version-v031\\rollback.py             :: 执行（幂等）
python paper\\manuscript\\_round.py                          :: 重建 v0.30 交付件
```

## 回滚做了什么

| 动作 | 对象 |
|---|---|
| **恢复** | `paper/manuscript/00_manuscript_EN.md`、`paper/manuscript/_assemble_draft.py`、`paper/tables/TableS1_config_audit.csv` |
| **改写** | `paper/manuscript/_build_docx.py` 中的版本串（`v0.31` → `v0.30`，4 处：docstring 两行 + `MD`/`DOCX` 两个常量） |
| **删除** | v0.31 交付件、两个 v0.31 探针、`_diag_v031.py`、Table S6 / Table S7 CSV、Fig. S4 图与绘图脚本、本轮四份笔记、本打包脚本 |

包内另存一份 `build_rollback.py`（打包脚本自身的副本），因为回滚会删掉工作树里的
`paper/manuscript/_build_rollback_v031.py`——留此副本，回滚后仍可重建本包。

## 故意不删

- `pipeline/study/` 下本轮新写的分析脚本（`pa_planB_sensitivity.py`、`pa_planB_roi_audit.py`、`pa_e4c_perconfig.py`、`pa_w5_freqchain.py`、`pa_export_tables_s6s7.py`）
- `results/` 下本轮产物（`planB_sensitivity.*`、`planB_roi_audit.*`、`e4c_perconfig.*`）

理由：**归档不能因为草稿回退而丢失溯源**。若确需清除，请手工删除并在笔记中登记。

## 为什么 `_build_docx.py` 是"改写"而不是"恢复"

本轮只把其中的版本串从 `v0.30` 改成 `v0.31`，文件字节数与其 v0.18 时代的历史条目**完全相同**（28379 B），
说明该文件在 v0.19–v0.31 之间除版本串外从未改动。历史里没有 v0.30 时刻的快照，
因此回滚用一次**可审计的字符串替换**代替恢复，并在 `PROVENANCE.md` 中记录这一判断依据。

## 回滚后

`_round.py` 的输出名来自 `_assemble_draft.py` 与 `_build_docx.py`（项目铁律：升级轮必须先改这三处）。
回滚把两处都改回 v0.30，故重跑 `_round.py` 会重新生成
`01_draft_v0.30_assembled.md` 与 `02_PAI_manuscript_v0.30_draft.docx`。
"""

PROV = """# PAI v0.31 回滚包 —— BEFORE 溯源

| 文件 | 来源 | 定位 | 校验 |
|---|---|---|---|
| `paper/manuscript/00_manuscript_EN.md` | WorkBuddy 文件历史 | blobKey `9290fef82c5b024d` **@v3**（2026-10-17 19:43，203277 B） | 状态头为 `draft **v0.30**`；不含 `v0.31 changelog` |
| `paper/manuscript/_assemble_draft.py` | WorkBuddy 文件历史 | blobKey `174efe8b58d4a617` **@v1**（2026-10-17 21:25，41219 B） | 仍含 `Core evidence`；`OUT = 01_draft_v0.30_assembled.md` |
| `paper/tables/TableS1_config_audit.csv` | WorkBuddy 文件历史 | blobKey `79cf16bd7ed95738` **@v1**（2026-10-17 23:16，3452 B） | 仍为 `Nx raised 601 -> 1501` |
| `paper/manuscript/_build_docx.py` | 盘上当前副本（**仅供审计**） | 28379 B | 回滚时不恢复此副本，而是把 `v0.31` 串改回 `v0.30` |

## 时间线（用于确认 v0.30 的收尾时刻）

| 时刻 | 事件 |
|---|---|
| 10-17 19:04–19:16 | v0.30 评审裁定 / 验收清单 / CHANGELOG / 回滚包写就 |
| 10-17 19:16 | `02_PAI_manuscript_v0.30_draft.docx` 生成（v0.30 收尾） |
| 10-17 19:43 | 母本 fhist v3（v0.30 状态，本轮 BEFORE 取自此处） |
| 10-17 19:54–21:18 | **本轮**新写 5 个分析脚本（`pa_planB_sensitivity.py` 19:54、`pa_e4c_perconfig.py` 20:17、`pa_planB_roi_audit.py` 20:30、`pa_w5_freqchain.py` 20:51、`pa_export_tables_s6s7.py` 21:18） |
| 10-17 21:25 | 装配脚本 fhist v1（本轮 BEFORE 取自此处） |
| 10-17 22:28 起 | 母本正文层改写（fhist v4+） |

⚠️ **本包建立时发现的一处不实表述（已三处同步更正）**：初稿的母本状态头、`评审裁定_v0.31.md` §0
与 `CHANGELOG_v0.31.md` 都写过"评审要求的两类数据类工作在 v0.30 归档中**已存在**、本轮仅引用"。
上表时间戳证明这些分析（及其产物 CSV）是**本轮新写新跑**的。准确口径为
「**无新实验（无新仿真 / 无新采集 / 未重跑 MATLAB）、有新分析代码**」。
"""


if __name__ == "__main__":
    main()
