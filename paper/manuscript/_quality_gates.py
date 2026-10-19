#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""常驻质量检查器 —— 每次构建后自动跑（round_throughput 杠杆 4）。

用法::

    python _quality_gates.py                # 默认检查 01_draft_v0.34_assembled.md
    python _quality_gates.py --md <path>    # 指定装配稿

退出码：0 = 无 FAIL；1 = 有 FAIL。

设计约定
--------
* **判定器（本文件）跨轮不变**；每轮变化的只有稿件本身与其期望值。
* **FAIL = 阻断交付**（投稿阻断级）；**WARN = 只报不拦**。
  分档理由见 `round_throughput.md` §6「按文件分档」——一刀切禁某个模式会
  把真问题淹掉。
* 一次性实验的产出是一个结论；常驻检查器的产出是**这一类问题从此不再发生**。
  故以下每一项都对应一次真实事故：

  ====== ==================================================== ======
  编号   检查                                                  档位
  ====== ==================================================== ======
  C1     DOCX 正文区间（`## Title` 起）出现中文字符               FAIL
  C2     markdown 表块缺 `|---|` 分隔行（被切断的碎片）           FAIL
  C3     源 CSV 各行列数不一致（渲染后错位）                      FAIL
  C4     正文 `![](…figures/X.png)` 引用的图文件不存在            FAIL
  C5     绘图脚本的字符串字面量里含中文（会画进图里）             WARN
  C6     绘图脚本里硬编码旧图号（`Fig. 10` / `图 11`）            WARN
  C7a    正文残留占位符 `[TODO]` / `[deferred]` / `TBD`           FAIL
  C7b    正文含符号/emoji（🟢🟡★ 等）                            WARN
  C7c    正文含内部文档路径（`docs/` `notes/` `pipeline/`）        WARN
  C7d    正文含产物路径（`results/…`）                            WARN
  ====== ==================================================== ======
"""
import argparse
import ast
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.dirname(HERE)
FIGDIR = os.path.join(PAPER, "figures")
TBLDIR = os.path.join(PAPER, "tables")

CJK = re.compile(r"[\u4e00-\u9fff]")
IMG = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
# 绘图脚本里硬编码的旧图号：`Fig. 10` / `Fig 11` / `图 11` / `Fig.10(b)`
STALE_NUM = re.compile(r"(?:Fig(?:ure)?\.?\s*\d+|图\s*\d+)")

fails, warns = [], []


def fail(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


def _cjk_slices(s):
    """返回 (中文片段, 上下文) 列表。"""
    out = []
    for m in CJK.finditer(s):
        a = max(0, m.start() - 18)
        b = min(len(s), m.end() + 18)
        out.append(s[a:b].replace("\n", " "))
    return out


# ---------------------------------------------------------------- C1
def c1_body_cjk(md_path):
    """正文区间内的中文字符（表格单元格与外文正文一视同仁）。"""
    lines = io.open(md_path, encoding="utf-8").read().split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith("## Title")), 0)
    hits = []
    for i in range(start, len(lines)):
        if CJK.search(lines[i]):
            hits.append((i, lines[i].strip()))
    if hits:
        total = sum(len(CJK.findall(l)) for _, l in hits)
        fail("C1 正文含中文字符 %d 个，分布在 %d 行" % (total, len(hits)))
        for i, s in hits[:12]:
            fails.append("      L%-5d %s" % (i, s[:110]))
        if len(hits) > 12:
            fails.append("      … 另有 %d 行" % (len(hits) - 12))
    return len(hits)


# ---------------------------------------------------------------- C2
def c2_split_tables(md_path):
    """markdown 表块缺 `|---|` 分隔行 = 被插入内容切成了碎片。"""
    lines = io.open(md_path, encoding="utf-8").read().split("\n")
    blocks, cur = [], []
    for l in lines:
        if l.strip().startswith("|"):
            cur.append(l)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    bad = []
    for b in blocks:
        has_sep = any(re.fullmatch(r"\|(?:\s*:?-{3,}:?\s*\|)+", x.strip()) for x in b)
        if not has_sep:
            bad.append(b)
    if bad:
        fail("C2 缺分隔行的表块 %d 个（被切断的碎片）" % len(bad))
        for b in bad[:6]:
            fails.append("      首格 %r  (%d 行)" % ((b[0].split("|")[1].strip() if "|" in b[0] else "")[:40], len(b)))
    return len(blocks), len(bad)


# ---------------------------------------------------------------- C3
def c3_ragged_csv():
    """源 CSV 各行列数不一致 -> 渲染进 DOCX 后列错位。"""
    bad = []
    if not os.path.isdir(TBLDIR):
        return 0
    for fn in sorted(os.listdir(TBLDIR)):
        if not fn.lower().endswith(".csv"):
            continue
        p = os.path.join(TBLDIR, fn)
        with io.open(p, encoding="utf-8-sig") as fh:
            rows = [r for r in csv.reader(fh) if any(c.strip() for c in r)]
        if len(rows) < 2:
            continue
        n0 = len(rows[0])
        ragged = [(k + 1, len(r)) for k, r in enumerate(rows) if len(r) != n0]
        if ragged:
            bad.append((fn, n0, ragged[:5]))
    if bad:
        fail("C3 源 CSV 列数不齐（%d 个文件）" % len(bad))
        for fn, n0, rg in bad:
            fails.append("      %-40s 表头 %d 列；异常行 %s" % (fn, n0, rg))
    return len(bad)


# ---------------------------------------------------------------- C4
def c4_missing_figures(md_path):
    """正文引用的图文件必须存在。"""
    md = io.open(md_path, encoding="utf-8").read()
    missing, seen = [], set()
    for m in IMG.finditer(md):
        rel = m.group(1)
        if rel in seen:
            continue
        seen.add(rel)
        p = os.path.normpath(os.path.join(HERE, rel))
        if not os.path.exists(p):
            missing.append(rel)
    if missing:
        fail("C4 正文引用的图文件缺失 %d 个" % len(missing))
        for r in missing:
            fails.append("      %s" % r)
    return len(seen), len(missing)


# ---------------------------------------------------------------- C5 / C6
def _string_literals(src):
    """AST 抽出**会被画进图里**的字符串字面量。

    排除 docstring —— 注释与文档串不渲染，把它们算进来只会制造误报，
    而误报会把真问题淹掉（`round_throughput.md` §6）。文件名（`.png`/`.pdf`）
    也排除：`Fig02_identity_crossterm.png` 是路径，不是图内标题。
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    doc = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                doc.add(id(body[0].value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc:
            s = node.value.strip()
            if s.lower().endswith((".png", ".pdf", ".svg")):
                continue
            out.append((node.lineno, node.value))
    return out


def _figure_scripts():
    """会画进正式图的脚本：paper/figures/_plot_*.py + pipeline/study/_*.py。"""
    out = []
    for d in (FIGDIR, os.path.join(PAPER, "pipeline", "study")):
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".py") and (fn.startswith("_plot") or fn.startswith("_fig")
                                       or fn.startswith("_window")):
                out.append(os.path.join(d, fn))
    return out


def c5_script_cjk():
    """绘图脚本的字符串字面量含中文 -> 会渲染进图里。"""
    bad = []
    for p in _figure_scripts():
        src = io.open(p, encoding="utf-8", errors="replace").read()
        for ln, s in _string_literals(src):
            if CJK.search(s):
                bad.append((os.path.basename(p), ln, s.strip()[:70]))
    if bad:
        warn("C5 绘图脚本字符串含中文 %d 处（会画进图里）" % len(bad))
        for f, ln, s in bad[:12]:
            warns.append("      %-26s L%-4d %r" % (f, ln, s))
        if len(bad) > 12:
            warns.append("      … 另有 %d 处" % (len(bad) - 12))
    return len(bad)


def c6_stale_fignum():
    """绘图脚本里硬编码的**旧**图号（重编号后会与正文不符）。

    白名单规则（否则误报会淹掉真信号——实测 5 条 WARN 里 5 条是误报）：
      * 脚本**自身编号**由文件名推出（`_plot_fig3_resolution.py` -> 3），
        出现该号的 `Fig. N` 是**正确**标注，不算旧号；
      * 若一串数字是**文件/目录路径的一部分**（如 3D-PACT 数据目录 `Fig. 2/`），
        与稿件图号无关，跳过；
      * 只报"与自身编号不符"的 `Fig. N`，以及中文「图 N」（此前抓到 Fig.5 的
        `Fig.10(b)` 与 Fig.8 的「图 11」正是这一类）。
    """
    bad = []
    for p in _figure_scripts():
        base = os.path.basename(p)
        m = re.search(r"fig(\d+)", base, re.I)
        own = int(m.group(1)) if m else None
        src = io.open(p, encoding="utf-8", errors="replace").read()
        for ln, s in _string_literals(src):
            for mm in STALE_NUM.finditer(s):
                tok = mm.group(0)
                # 路径上下文（前后紧邻 / 或 .png/.h5 等）-> 与图号无关
                a = s[max(0, mm.start() - 1):mm.start()]
                b = s[mm.end():mm.end() + 5]
                if a in "/\\" or b.startswith(("/", "\\", ".png", ".mat", ".hdf5")):
                    continue
                num = re.search(r"(\d+)", tok)
                if num and own is not None and int(num.group(1)) == own and "图" not in tok:
                    continue                      # 与自身编号一致 = 正确标注
                if "图" in tok or (num and own is not None and int(num.group(1)) != own):
                    bad.append((base, ln, tok, s.strip()[:60]))
    if bad:
        warn("C6 绘图脚本标注了与自身编号不符的图号 %d 处（重编号后需同步）" % len(bad))
        for f, ln, tok, s in bad[:12]:
            warns.append("      %-26s L%-4d %r  in %r" % (f, ln, tok, s))
        if len(bad) > 12:
            warns.append("      … 另有 %d 处" % (len(bad) - 12))
    return len(bad)


# ---------------------------------------------------------------- C7
# 占位符：裸方括号形式 `[TODO]` **以及**带说明的 `[TODO: …]`（后者曾漏检）、
# 全角方括号、以及裸 TBD。`[file missing]` 由装配脚本在解析失败时写入。
PLACEHOLDER = re.compile(r"[\[【](?:TODO|deferred|file missing|TBD)\b[^\]】]*[\]】]|\bTBD\b")
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2705\u26AA\u26AB\u2b50\u2605\u2606]")
INTPATH = re.compile(r"\b(?:docs|notes|pipeline)/[A-Za-z0-9_§.\-]*")
ARTPATH = re.compile(r"\bresults/[A-Za-z0-9_./*\-]*")

# 用户明确**延后**的投稿区块 —— 其中的 `[TODO: …]` 是占位符的正当用法，不算缺陷。
# 判据：**作者会消费它 ∧ 只在投稿期消费 ⇒ 不进 C7a 的 FAIL 集**。
DEFERRED_REGIONS = [
    (r"(?ms)^## Declarations\b.*?(?=^## References\b)",
     "Declarations（署名/伦理/资助/CRediT/AI 声明）"),
    (r"(?m)^.*\*\*(?:Authors|Corresponding author)\*\*.*$",
     "Title 区作者行"),
]


def c7_scaffolding(md_path):
    """内部脚手架泄漏：占位符（FAIL）、emoji、内部路径（WARN）。

    两处刻意的设计：

    * **延后区间掩码**。`## Declarations`（署名 / 伦理 / 资助 / CRediT / AI 声明）
      是用户明确**延后**的投稿区块，其中 `[TODO: …]` 是**占位符的正当用法**
      （等作者填），不是缺陷。故在 C7a 检测前把它整体掩掉，只在末行打印提示。
      判据：**作者会消费它 ∧ 只在投稿期消费 ⇒ 不算稿件缺陷**。
    * `results/…` 单列为 WARN 而非 FAIL —— 稿件 §4 有一句**故意**点名已发布产物
      （"copied from the released artifacts"），那是数据可得性声明，是否保留属作者
      裁定，不由检查器代决。
    """
    text = io.open(md_path, encoding="utf-8").read()
    start = next((i for i, l in enumerate(text.split("\n")) if l.startswith("## Title")), 0)
    body = "\n".join(text.split("\n")[start:])

    # 掩掉延后区块（用户明确延后的投稿块；其中 `[TODO: …]` 是占位符的正当用法）
    masked, notes = body, []
    for rx, label in DEFERRED_REGIONS:
        def _blank(m):
            n = len(PLACEHOLDER.findall(m.group(0)))
            if n:
                notes.append("%s 掩掉占位符 %d 处（延后，不阻断）" % (label, n))
            return "\n" * m.group(0).count("\n")
        masked = re.sub(rx, _blank, masked)

    ph = PLACEHOLDER.findall(masked)
    if ph:
        fail("C7a 正文残留占位符 %d 处: %s" % (len(ph), ", ".join(sorted(set(ph)))))
        for mm in PLACEHOLDER.finditer(masked):
            a = max(0, mm.start() - 55)
            fails.append("      …%s…" % masked[a:mm.end() + 55].replace("\n", " "))
    elif notes:
        print("C7a  占位符仅出现在延后区间内（已掩码）：%s" % "; ".join(notes))

    em = EMOJI.findall(masked)
    if em:
        warn("C7b 正文含符号/emoji %d 处: %s" % (len(em), " ".join(sorted(set(em)))))

    ip = INTPATH.findall(masked)
    if ip:
        warn("C7c 正文含内部文档路径 %d 处: %s" % (len(ip), ", ".join(sorted(set(ip))[:8])))

    ap = ARTPATH.findall(masked)
    if ap:
        warn("C7d 正文含产物路径 %d 处（§4 的已发布产物声明可能是有意的）: %s"
             % (len(ap), ", ".join(sorted(set(ap))[:6])))
    return len(ph), len(em), len(ip), len(ap)


# ---------------------------------------------------------------- main
def _latest_assembled():
    """Return the highest-version assembled draft present in this directory.

    Hard-coding the filename here makes every later round silently re-check the
    previous version, which is worse than not checking at all: the gates report
    PASS on a file the reader will never see. The version is therefore discovered
    from the directory listing, and the resolved path is printed at run time.
    """
    import glob
    import re as _re
    cands = glob.glob(os.path.join(HERE, "01_draft_v*_assembled.md"))

    def _key(path):
        m = _re.search(r"v(\d+)\.(\d+)", os.path.basename(path))
        return (int(m.group(1)), int(m.group(2))) if m else (-1, -1)

    if not cands:
        return os.path.join(HERE, "01_draft_v0.34_assembled.md")
    return max(cands, key=_key)


def main():
    ap = argparse.ArgumentParser(description="常驻质量检查器")
    ap.add_argument("--md", default=_latest_assembled())
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.md):
        print("MISSING assembled draft: %s" % args.md)
        return 2

    print("=== 常驻质量检查器 ===")
    print("装配稿: %s" % os.path.relpath(args.md, PAPER))

    n1 = c1_body_cjk(args.md)
    nblocks, n2 = c2_split_tables(args.md)
    n3 = c3_ragged_csv()
    nref, n4 = c4_missing_figures(args.md)
    n5 = c5_script_cjk()
    n6 = c6_stale_fignum()
    p7a, p7b, p7c, p7d = c7_scaffolding(args.md)

    print("C1 正文中文行      : %d" % n1)
    print("C2 markdown 表块   : %d (缺分隔行 %d)" % (nblocks, n2))
    print("C3 列数不齐 CSV    : %d" % n3)
    print("C4 引用的图文件    : %d (缺失 %d)" % (nref, n4))
    print("C5 脚本串含中文    : %d" % n5)
    print("C6 脚本硬编码图号  : %d" % n6)
    print("C7 脚手架 占位符%d / emoji%d / 内部路径%d / 产物路径%d" % (p7a, p7b, p7c, p7d))
    print()
    if fails:
        print("--- FAIL (%d) ---" % len(fails))
        for m in fails:
            print(m)
    if warns:
        print("--- WARN (%d) ---" % len(warns))
        for m in warns:
            print(m)
    if not fails and not warns:
        print("ALL CLEAN")
    elif not fails:
        print("PASS (仅 WARN，不阻断)")
    print()
    print("VERDICT: %s" % ("FAIL" if fails else "PASS"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
