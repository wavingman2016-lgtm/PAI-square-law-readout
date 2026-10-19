# -*- coding: utf-8 -*-
"""Build the one-click rollback package for PAI v0.31 -> v0.32.

    python paper/manuscript/_build_rollback_v032.py

Produces _rollback/PAI-version-v032/ with BEFORE/ (pre-round state of the four
files whose *content* changed), rollback.py, README.md and PROVENANCE.md.

Provenance of the BEFORE copies
-------------------------------
  00_manuscript_EN.md      snapshots/PAI-v032-round9/20261018-002327 (pre-round v0.31)
  _assemble_draft.py       snapshots/PAI-v032-round9/20261018-002327
  TableS1_config_audit.csv snapshots/PAI-v032-round9/20261018-002327
  Table03_registry.csv     snapshots/PAI-v032-round9/20261018-002327

_build_docx.py and _quality_gates.py were changed ONLY in the version string
(v0.31 -> v0.32; their output-name / default-md constants), so rollback rewrites
the string instead of restoring.
"""
import io
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))            # paper/manuscript
ROOT = os.path.dirname(os.path.dirname(HERE))                # <repo root>
PKG = os.path.join(ROOT, "_rollback", "PAI-version-v032")
# the snapshot below was mirrored from the build machine's absolute path and is
# local to that machine only; it is not part of this archive
SNAP = os.environ.get("PAI_V032_SNAPSHOT", "")

BEFORE = {
    "paper/manuscript/00_manuscript_EN.md": "paper/manuscript/00_manuscript_EN.md",
    "paper/manuscript/_assemble_draft.py": "paper/manuscript/_assemble_draft.py",
    "paper/tables/TableS1_config_audit.csv": "paper/tables/TableS1_config_audit.csv",
    "paper/tables/Table03_registry.csv": "paper/tables/Table03_registry.csv",
}

# version-string-only files (rewritten, not restored)
REWRITE_VER = [
    ("paper/manuscript/_build_docx.py", [("01_draft_v0.32_assembled.md", "01_draft_v0.31_assembled.md"),
                                         ("02_PAI_manuscript_v0.32_draft.docx", "02_PAI_manuscript_v0.31_draft.docx")]),
    ("paper/manuscript/_quality_gates.py", [("01_draft_v0.32_assembled.md", "01_draft_v0.31_assembled.md")]),
]

DELETE = [
    "paper/manuscript/01_draft_v0.32_assembled.md",
    "paper/manuscript/02_PAI_manuscript_v0.32_draft.docx",
    "paper/manuscript/_probe_v032_selfaudit.py",
    "paper/manuscript/_build_rollback_v032.py",
    "paper/figures/_plot_fig5_audit.py",
    "paper/figures/Fig05_paired_audit.png",
    "paper/notes/评审裁定_v0.32.md",
    "paper/notes/CHANGELOG_v0.32.md",
    "paper/notes/投稿前验收清单_v0.32.md",
]


def main():
    if os.path.isdir(PKG):
        shutil.rmtree(PKG)
    os.makedirs(PKG)
    print("PAI rollback package  v0.32 -> v0.31")

    for rel, fname in BEFORE.items():
        src = os.path.join(SNAP, fname)
        dst = os.path.join(PKG, "BEFORE", rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print("  BEFORE  %-46s %7d B" % (rel, os.path.getsize(dst)))

    # assertions: the BEFORE copies must be the pre-round v0.31 state
    ms = io.open(os.path.join(PKG, "BEFORE", "paper", "manuscript",
                              "00_manuscript_EN.md"), encoding="utf-8").read()
    ad = io.open(os.path.join(PKG, "BEFORE", "paper", "manuscript",
                              "_assemble_draft.py"), encoding="utf-8").read()
    t1 = io.open(os.path.join(PKG, "BEFORE", "paper", "tables",
                              "TableS1_config_audit.csv"), encoding="utf-8").read()
    assert "draft **v0.31**" in ms, "BEFORE master not v0.31"
    assert "independent raised-sampling-rate folding control" in ms, "BEFORE master lost old E4c wording"
    assert "Exploratory evidence" in ad, "BEFORE assembler lost old Fig.5 caption"
    assert "measured spectral peak" in t1 and "Same rule as W4" in t1, "BEFORE TableS1 lost old W5 wording"
    print("  assertions on BEFORE content: all 4 OK")

    with io.open(os.path.join(PKG, "rollback.py"), "w", encoding="utf-8") as f:
        f.write(ROLLBACK_PY % {"delete": repr(DELETE), "rewrite": repr(REWRITE_VER)})
    with io.open(os.path.join(PKG, "README.md"), "w", encoding="utf-8") as f:
        f.write(README)
    with io.open(os.path.join(PKG, "PROVENANCE.md"), "w", encoding="utf-8") as f:
        f.write(PROV)
    # self-host: keep a copy of this builder so rollback can be rebuilt
    shutil.copy2(os.path.abspath(__file__), os.path.join(PKG, "build_rollback.py"))
    print("  wrote rollback.py / README.md / PROVENANCE.md / build_rollback.py")
    print("\npackage: %s" % PKG)


ROLLBACK_PY = '''# -*- coding: utf-8 -*-
"""PAI v0.32 -> v0.31 one-click rollback.

    python rollback.py --dry-run    # preview
    python rollback.py              # execute (idempotent)

Restores the four content-changed files from BEFORE/, rewrites the version
string in _build_docx.py / _quality_gates.py, and deletes v0.32-only artifacts.
After rollback re-run:  python paper/manuscript/_round.py
"""
import io
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

RESTORE = [
    "paper/manuscript/00_manuscript_EN.md",
    "paper/manuscript/_assemble_draft.py",
    "paper/tables/TableS1_config_audit.csv",
    "paper/tables/Table03_registry.csv",
]
REWRITE = %(rewrite)s
DELETE = %(delete)s

dry = "--dry-run" in sys.argv
acts = len(RESTORE) + len(REWRITE) + len(DELETE)
print("PAI rollback v0.32 -> v0.31  (%%d actions)%%s" %% (acts, "  [DRY RUN]" if dry else ""))

for rel in RESTORE:
    src = os.path.join(HERE, "BEFORE", rel.replace("/", os.sep))
    dst = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(src):
        print("  MISSING BEFORE  %%s" %% rel); continue
    print("  restore   %%s" %% rel)
    if not dry:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

for rel, pairs in REWRITE:
    dst = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(dst):
        print("  MISSING   %%s" %% rel); continue
    txt = io.open(dst, encoding="utf-8").read()
    for old, new in pairs:
        txt = txt.replace(old, new)
    print("  rewrite   %%s" %% rel)
    if not dry:
        io.open(dst, "w", encoding="utf-8", newline="").write(txt)

for rel in DELETE:
    dst = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(dst):
        print("  absent    %%s" %% rel); continue
    print("  delete    %%s" %% rel)
    if not dry:
        os.remove(dst)

print("\\n%%s" %% ("dry run complete; nothing written" if dry
                else "done. now re-run: python paper/manuscript/_round.py"))
'''


README = """# PAI v0.32 —— 回滚包

把 v0.32（第九轮评审处置）退回 v0.31（第八轮后版本）。

## 用法
```bat
python _rollback\\PAI-version-v032\\rollback.py --dry-run
python _rollback\\PAI-version-v032\\rollback.py
python paper\\manuscript\\_round.py
```

## 回滚做了什么
- **恢复**：母本、`_assemble_draft.py`、`TableS1_config_audit.csv`、`Table03_registry.csv`（改动前 v0.31 状态）。
- **改写**：`_build_docx.py` / `_quality_gates.py` 的版本串（`v0.32` → `v0.31`）。
- **删除**：v0.32 交付件、`_probe_v032_selfaudit.py`、`_plot_fig5_audit.py`、`Fig05_paired_audit.png`、三份 v0.32 笔记、本打包脚本。

## 故意不删
旧图 `Fig05_delta_gCNR_15of15.png`（v0.31 遗留，回滚后 Fig. 5 又指向它，故保留）。
"""

PROV = """# PAI v0.32 回滚包 —— BEFORE 溯源

| 文件 | 来源 | 校验 |
|---|---|---|
| `00_manuscript_EN.md` | `~/.workbuddy/snapshots/PAI-v032-round9/20261018-002327`（改动前快照） | 状态头 `draft **v0.31**`；含旧 E4c 措辞 `independent raised-sampling-rate folding control` |
| `_assemble_draft.py` | 同上 | 含旧 Fig.5 图注 `Exploratory evidence` |
| `TableS1_config_audit.csv` | 同上 | 含旧 W5 措辞 `measured spectral peak` / `Same rule as W4` |
| `Table03_registry.csv` | 同上 | W5 `validated_config` = `F0=0.35 MHz (measured), ...` |

`_build_docx.py` / `_quality_gates.py` 本轮只改版本串，回滚用**可审计字符串替换**（`v0.32` → `v0.31`），依据：二者仅在输出名/默认 md 常量处出现版本号。

包内另存 `build_rollback.py`（打包脚本自身副本），回滚后仍可重建本包。
"""


if __name__ == "__main__":
    main()
