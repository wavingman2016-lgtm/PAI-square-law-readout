# -*- coding: utf-8 -*-
"""Build the journal-style DOCX from the assembled markdown draft.

Input : paper/manuscript/01_draft_v0.48_assembled.md
Output: paper/manuscript/02_PAI_manuscript_v0.48_draft.docx

Math route : LaTeX -> latex2mathml -> MathML -> MML2OMML.XSL -> OMML (native, editable)
Layout     : A4, 2.5 cm margins, Times New Roman 11 pt, justified; figure captions below
             the figure, table captions above the table.

Run with --dry to only dry-run the mathematics (no file is written).
"""
import io
import os
import re
import sys
import zipfile

from lxml import etree
import latex2mathml.converter as l2m
from PIL import Image
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement, parse_xml

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, "01_draft_v0.48_assembled.md")
DOCX = os.path.join(HERE, "02_PAI_manuscript_v0.48_draft.docx")
XSL_PATH = r"C:\Program Files\Microsoft Office\root\Office16\MML2OMML.XSL"
XSLT = etree.XSLT(etree.parse(XSL_PATH))

MML = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"

stats = {"math": 0, "math_fail": [], "figs": 0, "tables": 0, "nary": 0, "nary_empty": 0,
         "non_idem": [], "tex_leak": []}
issues = []


# --------------------------------------------------------------------------- math
# latex2mathml 不解析 "<尺寸命令><定界符命令>" 的组合：它把定界符的命令名**原样**写进
# <mo>，于是 Word 里显示字面 "\lvert" 而不是竖线。实测 8×12 种组合**全部**失败。
# 其中竖线可以保留尺寸（\bigl| 可用），其余定界符只能退化为不带尺寸的命令本身。
_SIZE_DELIM = re.compile(
    r"\\(bigl|Bigl|biggl|Biggl|bigr|Bigr|biggr|Biggr)"
    r"\\(lvert|rvert|vert|lVert|rVert|Vert|lbrace|rbrace|langle|rangle|lfloor|rfloor)")
_DELIM_FALLBACK = {"lVert": r"\|", "rVert": r"\|", "Vert": r"\|",
                   "lbrace": r"\{", "rbrace": r"\}",
                   "langle": r"\langle", "rangle": r"\rangle",
                   "lfloor": r"\lfloor", "rfloor": r"\rfloor"}


def _fix_size_delim(m):
    size, d = m.group(1), m.group(2)
    if d in ("lvert", "rvert", "vert"):     # 竖线：保留尺寸，换成字面 '|'
        return "\\%s|" % size
    return _DELIM_FALLBACK[d]               # 其余：丢掉尺寸，保留可解析的命令


def sanitize(s):
    """latex2mathml / MML2OMML.XSL work-arounds (see md-to-journal-docx skill)."""
    # operator names that would come out italic
    for op in ("min", "max", "lim", "arg", "sup", "inf", "gcd", "det", "dim", "ker", "Pr"):
        s = re.sub(r"\\%s(?![a-zA-Z])" % op, r"\\mathrm{%s}" % op, s)
    s = s.replace(r"\tfrac", r"\frac")
    s = _SIZE_DELIM.sub(_fix_size_delim, s)          # \bigl\lvert -> \bigl|  等
    return s


def _match_brace(s, j):
    """返回与 s[j]=="{" 配对的右花括号下标；用深度计数，支持嵌套 {..} / \frac{}{}。"""
    depth = 0
    for k in range(j, len(s)):
        c = s[k]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return k
    return -1


def _match_delim(s, j, close):
    """返回与 s[j]（'(' / '['）配对的 close 下标；深度计数，支持嵌套。"""
    depth = 0
    for k in range(j, len(s)):
        if s[k] in "([{":
            depth += 1
        elif s[k] in ")]}":
            depth -= 1
            if depth == 0:
                return k if s[k] == close else -1
    return -1


_NARY = re.compile(r"\\(sum|int|prod|oint|bigcup|bigcap)(?![a-zA-Z])")


def _consume_operand(s, j, n):
    """吃下一个“裸操作数”（无花括号、无前导反斜杠命令），返回结束下标。

    操作数由若干“原子”组成，原子之间可有空格：
      原子 := 字母数字串 [ _ / ^ 脚本 ]*      （v_m、v_n^{*}、g_m^2）
            | {...} 平衡花括号块
            | |...| 成对竖线（**无配对则视为结束**，不吞掉孤立闭竖线）
    遇到无法归属的字符（, ) + - = 等）即停止。
    """
    k = j
    ate = False
    while k < n:
        c = s[k]
        if c == " ":
            p = k
            while p < n and s[p] == " ":
                p += 1
            if p < n and (s[p].isalnum() or s[p] in "{|"):
                k = p
                continue
            break
        if c == "{":
            m = _match_brace(s, k)
            if m < 0:
                break
            k, ate = m + 1, True
            continue
        if c == "|":
            q = k + 1
            while q < n and s[q] != "|":
                q += 1
            if q >= n:                 # 孤立闭竖线（开竖线在 nary 之前）=> 不属于本操作数
                break
            k, ate = q + 1, True
            continue
        if c.isalnum():
            k += 1
            ate = True
            while k < n and s[k] in "_^":
                if k + 1 < n and s[k + 1] == "{":
                    m = _match_brace(s, k + 1)
                    if m < 0:
                        break
                    k = m + 1
                elif k + 1 < n and s[k + 1].isalnum():
                    k += 2
                else:
                    break
            continue
        break
    return k if ate else j


def _absorb_scripts(s, k, n):
    """把紧跟的 _{} / ^{} 或 _x / ^x 上下标并入，返回新的结束下标。

    这一步是必需的：latex2mathml 会把 ``{|v_m|}^2`` 编译成
    ``<msup><mrow>|v_m|</mrow><mn>2</mn></msup>``，而 MML2OMML.XSL **不认**
    msup 作为 nary 的操作数 => 仍然输出空的 <m:e></m:e>。把幂号收进花括号
    （``{|v_m|^2}`` -> ``<mrow>|v_m|^2</mrow>``）才会被识别。
    """
    while k < n and s[k] in "_^":
        if k + 1 < n and s[k + 1] == "{":
            m = _match_brace(s, k + 1)
            if m < 0:
                break
            k = m + 1
        elif k + 1 < n and s[k + 1].isalnum():
            k += 2
        else:
            break
    return k


def brace_nary(s):
    """Group the operand of \\sum / \\int / \\prod so MML2OMML.XSL does not emit <m:e></m:e>.

    NOTE the operator gate is ``(?![a-zA-Z])`` and **not** ``\\b``: in Python ``_`` is a
    word character, so ``\\b`` never matches in ``\\sum_m`` / ``\\sum_{...}`` and the whole
    transform silently became a no-op.
    """
    out = []
    i, n = 0, len(s)
    while i < n:
        m = _NARY.match(s, i)
        if not m:
            out.append(s[i])
            i += 1
            continue
        out.append(m.group(0))
        j = m.end()                       # match 已锚定在 i，end() 即绝对下标
        # consume _{} / ^{} / _x / ^x
        while j < n and s[j] in "_^":
            if j + 1 < n and s[j + 1] == "{":
                k = _match_brace(s, j)
                if k < 0:
                    break
                out.append(s[j:k + 1])
                j = k + 1
            else:
                out.append(s[j:j + 2])
                j += 2
        if j >= n:
            i = j
            continue
        # 脚本与操作数之间的空白：原样输出、**不并入花括号**。否则
        # "\sum_m {a_m}" 会先落进“裸操作数”分支，把已经花括号化的内容再包一层，
        # 变成 "{{\lvert a_m\rvert}}"（非幂等，且多一层无意义分组）。
        sp = j
        while sp < n and s[sp] == " ":
            sp += 1
        if sp > j and sp < n:
            out.append(s[j:sp])
            j = sp
        if s[j] == "{":                                   # already braced
            k = _match_brace(s, j)
            if k < 0:
                out.append(s[j:]); j = n; i = j; continue
            end = _absorb_scripts(s, k + 1, n)
            if end > k + 1:                               # 尾随幂号必须收进花括号内
                out.append("{" + s[j + 1:k] + s[k + 1:end] + "}")
            else:
                out.append(s[j:end])
            j = end
        elif s[j] == "\\":                                # \bigl( ... \bigr) etc.
            # 操作数可能是一整串带括号的内容，例如
            #   \sum_m \bigl(g_m\lvert z_m\rvert\bigr)^2
            # 这里必须把**平衡的括号串整体**（含 \bigl/\bigr 等命令）吃掉，
            # 只取命令名会把剩余的 "(...)" 留在 nary 之外 =>
            # MML2OMML.XSL 生成空的 <m:e></m:e>，Word 里显示为空框。
            m2 = re.match(r"\\[a-zA-Z]+", s[j:])
            if not m2:                                    # 孤立的反斜杠，原样输出
                out.append(s[j]); j += 1; i = j; continue
            op_start = j
            j += m2.end()
            if j < n and s[j] == "{":
                k = _match_brace(s, j)
                if k < 0:
                    out.append(s[j:]); j = n; i = j; continue
                j = k + 1
            # 吃掉紧随其后的平衡括号串（含嵌套）
            while j < n and s[j] in "([{":
                close = {"(": ")", "[": "]", "{": "}"}[s[j]]
                k = _match_delim(s, j, close)
                if k < 0:
                    break
                j = k + 1
            while j < n and s[j] in "^_":                  # 后置上下标
                if j + 1 < n and s[j + 1] == "{":
                    k = _match_brace(s, j)
                    if k < 0:
                        break
                    j = k + 1
                else:
                    j += 2
            # 若整段已被 {…} 覆盖（k+1 处的 '}' 就是配对花括号）则不重复包裹
            if s[op_start:op_start + 1] != "{":
                out.append("{" + s[op_start:j] + "}")
            else:
                out.append(s[op_start:j])
        else:
            # **裸操作数**（既无花括号也无前导反斜杠命令），例如
            #   \sum_m v_m            \sum_m|v_m|^2          \sum_{m\neq n}v_m v_n^{*}
            # 必须吃掉**整条 token 串**（变量 + 上下标 + 幂 + 乘积项）。
            # 只包一个字符会把其余部分留在 nary 之外 => MML2OMML.XSL 生成空的
            # <m:e></m:e>，Word 里显示为空框。
            k = _consume_operand(s, j, n)
            if k <= j:                       # 一个原子都吃不到（如 "\sum_m,"）=> 原样
                out.append(s[j])
                j += 1
            else:
                k = _absorb_scripts(s, k, n)         # 尾随上下标并进操作数
                st = j                       # 跳过的前导空格留在花括号**外面**
                while st < k and s[st] == " ":
                    st += 1
                out.append(s[j:st] + "{" + s[st:k] + "}")
                j = k
        i = j
    return "".join(out)


def math_omml(latex):
    s = brace_nary(sanitize(latex))
    dom = etree.fromstring(l2m.convert(s).encode("utf-8"))
    root = XSLT(dom).getroot()
    # 通用泄漏守卫：OMML 的数学文本里**不应出现反斜杠**。latex2mathml 遇到它不支持的
    # 命令时会（悄悄）把命令名原样写进 <mo>/<mi>，Word 就显示成字面 LaTeX ——
    # 例如 "\bigl\lvert" 变成 <mo>\lvert</mo>。这里统一捕获，这类问题不能静默通过。
    for t in root.iter(MML + "t"):
        if t.text and "\\" in t.text:
            stats["tex_leak"].append((latex[:60], t.text.strip()[:30]))
    return root


def add_math(par, latex, display=False):
    try:
        root = math_omml(latex)
    except Exception as e:                                # noqa: BLE001
        stats["math_fail"].append((latex[:70], "%s: %s" % (type(e).__name__, e)))
        par.add_run(latex)
        return
    par._p.append(parse_xml(etree.tostring(root, encoding="unicode")))
    stats["math"] += 1


# --------------------------------------------------------------------- inline text
TOK = re.compile(r"(\$\$[^$]+\$\$|\$[^$]+\$|`[^`]+`|\*\*.*?\*\*|~~.*?~~|\*.*?\*)")


def add_styled(par, text, bold=False, italic=False, strike=False):
    for tok in TOK.split(text):
        if not tok:
            continue
        if tok.startswith("$$") and tok.endswith("$$") and len(tok) > 4:
            add_math(par, tok[2:-2])
        elif tok.startswith("$") and tok.endswith("$") and len(tok) > 2:
            add_math(par, tok[1:-1])
        elif tok.startswith("`") and tok.endswith("`") and len(tok) > 2:
            r = par.add_run(tok[1:-1])
            r.font.name = "Consolas"
            r.font.size = Pt(10)
        elif tok.startswith("**") and tok.endswith("**") and len(tok) > 4:
            add_styled(par, tok[2:-2], bold=True, italic=italic, strike=strike)
        elif tok.startswith("~~") and tok.endswith("~~") and len(tok) > 4:
            add_styled(par, tok[2:-2], bold=bold, italic=italic, strike=True)
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            add_styled(par, tok[1:-1], bold=bold, italic=True, strike=strike)
        else:
            r = par.add_run(tok)
            r.bold = bold or None
            r.italic = italic or None
            if strike:
                r.font.strike = True


def para(doc, text, size=11, bold=False, italic=False, align="just",
         space_after=6, space_before=0, indent=0.0, color=None, keep=False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    pf.line_spacing = 1.15
    if indent:
        pf.left_indent = Cm(indent)
    p.alignment = {"just": WD_ALIGN_PARAGRAPH.JUSTIFY, "left": WD_ALIGN_PARAGRAPH.LEFT,
                   "center": WD_ALIGN_PARAGRAPH.CENTER}[align]
    if keep:
        pf.keep_with_next = True
    add_styled(p, text)
    for r in p.runs:
        r.font.size = Pt(size)
        if bold:
            r.bold = True
        if italic:
            r.italic = True
        if color:
            r.font.color.rgb = RGBColor(*color)
    return p


# --------------------------------------------------------------------------- tables
def split_row(line):
    """Split a markdown table row on '|' that is not inside $...$ and not escaped."""
    cells, buf, depth, i = [], "", 0, 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            buf += line[i:i + 2]
            i += 2
            continue
        if c == "$":
            depth ^= 1
        if c == "|" and depth == 0:
            cells.append(buf)
            buf = ""
        else:
            buf += c
        i += 1
    cells.append(buf)
    return [c.strip() for c in cells]


def add_table(doc, rows):
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    t = doc.add_table(rows=len(rows), cols=ncol)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = True                      # let Word fit the text width
    fsz = Pt(8) if ncol <= 10 else Pt(6.5) if ncol <= 20 else Pt(5.5)
    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row):
            c = t.cell(ri, ci)
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.line_spacing = 1.0
            txt = cell.replace("\\|", "|")
            add_styled(p, txt)
            for r in p.runs:
                r.font.size = fsz
                if ri == 0:
                    r.bold = True
    # repeat header row across pages
    tr = t.rows[0]._tr
    trPr = tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)
    stats["tables"] += 1
    return t


def is_caption(line):
    return bool(re.match(r"^\*\*(Fig\.|Table )", line))


# ----------------------------------------------------------------------------- main

def _normalize_zip(path, stamp=(2026, 10, 18, 0, 0, 0)):
    """Rewrite the docx archive with fixed entry timestamps.

    python-docx stamps every zip entry with the wall-clock time at save, so two
    byte-identical documents produce different files and any hash manifest
    (the rollback package) reports a spurious CHANGED.  Normalising the stamp
    makes the build reproducible; only the archive metadata changes, the
    package contents are copied through untouched.
    """
    tmp = path + ".tmpzip"
    with zipfile.ZipFile(path) as zin, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            zi = zipfile.ZipInfo(it.filename, date_time=stamp)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = it.external_attr
            zi.internal_attr = it.internal_attr
            zi.create_system = it.create_system
            zout.writestr(zi, zin.read(it.filename))
    os.replace(tmp, path)


def build(dry=False):
    md = io.open(MD, encoding="utf-8").read()

    # ---- math dry-run ----
    exprs = set()
    for m in re.finditer(r"\$\$(.+?)\$\$", md, flags=re.S):
        exprs.add(("D", m.group(1)))
    for m in re.finditer(r"\$([^$\n]+)\$", md):
        exprs.add(("I", m.group(1)))
    for kind, e in sorted(exprs):
        try:
            b1 = brace_nary(sanitize(e))
            if brace_nary(b1) != b1:                      # 幂等回归探针
                stats["non_idem"].append(e[:70])
            root = math_omml(e)
            for nary in root.findall(".//" + MML + "nary"):
                stats["nary"] += 1
                ee = nary.find(MML + "e")
                if ee is None or not "".join(ee.itertext()).strip():
                    stats["nary_empty"] += 1
        except Exception as ex:                           # noqa: BLE001
            stats["math_fail"].append((e[:70], "%s: %s" % (type(ex).__name__, ex)))
    print("math expressions: %d  (display %d / inline %d)"
          % (len(exprs), sum(1 for k, _ in exprs if k == "D"), sum(1 for k, _ in exprs if k == "I")))
    print("nary operators  : %d   empty-operand: %d" % (stats["nary"], stats["nary_empty"]))
    if stats["tex_leak"]:
        uniq = sorted(set(lk for _, lk in stats["tex_leak"]))
        print("RAW LaTeX LEAKED INTO MATH TEXT (%d hits, %d distinct): %s"
              % (len(stats["tex_leak"]), len(uniq), ", ".join(repr(u) for u in uniq)))
    if stats["non_idem"]:
        print("NON-IDEMPOTENT brace_nary (%d):" % len(stats["non_idem"]))
        for e in stats["non_idem"][:10]:
            print("   ", e)
    if stats["math_fail"]:
        print("FAILED (%d):" % len(stats["math_fail"]))
        for e, err in stats["math_fail"][:25]:
            print("   ", e, "->", err)
    if dry:
        return 0 if (not stats["math_fail"] and stats["nary_empty"] == 0
                     and not stats["tex_leak"] and not stats["non_idem"]) else 1

    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    for a in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(sec, a, Cm(2.5))

    lines = md.split("\n")
    # skip the file header and the status/changelog blockquote: start at '## Title'
    i = next(k for k, l in enumerate(lines) if l.startswith("## Title"))

    tbl_buf = []
    tbl_sep = [False]        # 本表是否见过 "|---|" 分隔行（见下 esp. 断表守卫）

    def flush_table():
        if tbl_buf:
            # 断表守卫：合法的 markdown 表**必须有** "|---|" 分隔行。没有分隔行意味着
            # 这张表是被插进来的内容**切成碎片**了 —— Word 里会变成好几个独立的表，
            # 而且后续片段的第一行数据会被当作表头加粗。这里显式报警。
            if not tbl_sep[0]:
                issues.append("markdown table with no separator row (%d rows) -- a split table? "
                              "first cell: %r" % (len(tbl_buf),
                                                  (tbl_buf[0][0] if tbl_buf[0] else "")[:40]))
            add_table(doc, tbl_buf)
            del tbl_buf[:]
            tbl_sep[0] = False

    # ---------------------------------------------------------- block parser
    # Source lines are hard-wrapped: consecutive lines of the same kind are
    # merged into ONE paragraph so that emphasis and inline math straddling a
    # line break survive into the DOCX (e.g. "**no `TODO: verify`" / "marker
    # remains**" across a hard wrap used to leak literal asterisks).
    P_MODE, Q_MODE, L_MODE, N_MODE = "p", "q", "l", "n"
    blk = {"mode": N_MODE, "buf": [], "kind": None}   # kind: bullet | num

    def blk_flush():
        if blk["mode"] == P_MODE and blk["buf"]:
            para(doc, " ".join(blk["buf"]))
        elif blk["mode"] == Q_MODE and blk["buf"]:
            para(doc, " ".join(blk["buf"]), size=9.5, italic=True, align="left",
                 indent=0.6, space_after=6, color=(0x44, 0x44, 0x44))
        elif blk["mode"] == L_MODE and blk["buf"]:
            p = doc.add_paragraph(style="List Bullet" if blk["kind"] == "bullet"
                                  else "List Number")
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.15
            add_styled(p, " ".join(blk["buf"]))
            for r in p.runs:
                r.font.size = Pt(11)
        blk["mode"], blk["buf"], blk["kind"] = N_MODE, [], None

    def flush_all():
        flush_table()
        blk_flush()

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        s = line.strip()

        if not s:
            flush_all()
            i += 1
            continue
        if s == "---":
            flush_all()
            i += 1
            continue

        # headings
        if s.startswith("### "):
            flush_all()
            txt = re.sub(r"\s*\*\(target[^)]*\)\*", "", s[4:])
            para(doc, txt, size=12, bold=True, align="left", space_before=10, space_after=4, keep=True)
            i += 1
            continue
        if s.startswith("## Title"):
            # the manuscript title itself: render it as the document title,
            # not as a heading that reads "Title"
            flush_all()
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip().startswith("**"):
                ttl = lines[j].strip().strip("*").strip()
                para(doc, ttl, size=15, bold=True, align="center",
                     space_before=0, space_after=12)
                i = j
            i += 1
            continue
        if s.startswith("## "):
            flush_all()
            txt = re.sub(r"\s*\*\(target[^)]*\)\*", "", s[3:])
            para(doc, txt, size=14, bold=True, align="left", space_before=14, space_after=6, keep=True)
            i += 1
            continue
        if s.startswith("# "):
            flush_all()
            i += 1
            continue

        # display math block (may span lines)
        if s.startswith("$$"):
            flush_all()
            buf = s[2:]
            while "$$" not in buf and i + 1 < len(lines):
                i += 1
                buf += " " + lines[i].strip()
            buf = buf.split("$$")[0]
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            add_math(p, buf)
            for r in p.runs:
                r.font.size = Pt(11)
            i += 1
            continue

        # figure
        m = re.match(r"^!\[(.*?)\]\((.+?)\)$", s)
        if m:
            flush_all()
            path = os.path.normpath(os.path.join(HERE, m.group(2)))
            if not os.path.exists(path):
                issues.append("figure not found: %s" % path)
                i += 1
                continue
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            with Image.open(path) as im:
                ar = im.size[0] / im.size[1]
            w = 16.0 if ar >= 2.5 else 14.5 if ar >= 1.8 else 12.5 if ar >= 1.3 else 11.0
            # Fig. 5 is redrawn on a taller canvas in v0.45; at the generic 1.8
            # threshold it would fall to 14.5 cm and lose the extra legibility the
            # redraw was meant to buy, so it is pinned to the full text width.
            if "Fig5_sim_display_cost" in path:
                w = 16.0
            p.add_run().add_picture(path, width=Cm(w))
            stats["figs"] += 1
            # caption directly below
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and is_caption(lines[j].strip()):
                cap = lines[j].strip()
                cap = re.sub(r"^\*\*(Fig\. [^*]+)\.\*\*\s*", r"**\1.** ", cap)
                para(doc, cap, size=9, align="center", space_after=10, italic=False)
                i = j
            i += 1
            continue

        # table caption above a table
        if is_caption(s):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip().startswith("|"):
                cap = re.sub(r"^\*\*([^*]+)\.\*\*\s*", r"**\1.** ", s)
                para(doc, cap, size=9, align="left", space_before=8, space_after=3, keep=True)
                i += 1
                continue

        # table body
        if s.startswith("|"):
            cells = split_row(s)
            if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
                tbl_sep[0] = True
                i += 1
                continue
            tbl_buf.append([c for c in cells[1:-1]] if len(cells) > 2 else cells)
            i += 1
            continue
        flush_table()   # a finished table ends here; the text block keeps going

        # blockquote (consecutive '>' lines merge into one indented note)
        if s.startswith(">"):
            if blk["mode"] != Q_MODE:
                flush_all()
                blk["mode"] = Q_MODE
            blk["buf"].append(s.lstrip("> ").strip())
            i += 1
            continue

        # bullets / numbered items: each starts its own paragraph, and indented
        # continuation lines are appended to the item currently being built
        m = re.match(r"^([-*]|\d+\.)\s+(.*)$", s)
        if m:
            flush_all()
            blk["mode"] = L_MODE
            blk["kind"] = "bullet" if m.group(1) in "-*" else "num"
            blk["buf"] = [m.group(2)]
            i += 1
            continue

        # indented continuation of the block currently being built
        if raw[:1] in (" ", "\t"):
            if blk["mode"] in (L_MODE, P_MODE, Q_MODE):
                blk["buf"].append(s)
                i += 1
                continue

        # plain paragraph: hard-wrapped lines merge into one paragraph
        if blk["mode"] == P_MODE:
            blk["buf"].append(s)
        else:
            flush_all()
            blk["mode"] = P_MODE
            blk["buf"] = [s]
        i += 1

    flush_all()
    doc.save(DOCX)
    _normalize_zip(DOCX)

    # ------------------------------------------------------------------ verify
    import docx as _docx
    d2 = _docx.Document(DOCX)
    n_par = len(d2.paragraphs)
    n_tbl = len(d2.tables)
    n_img = len(d2.inline_shapes)
    with zipfile.ZipFile(DOCX) as z:
        xml = z.read("word/document.xml")
    root = etree.fromstring(xml)
    n_omml = len(root.findall(".//" + MML + "oMath"))
    n_nary = len(root.findall(".//" + MML + "nary"))
    empty = [n for n in root.findall(".//" + MML + "nary")
             if n.find(MML + "e") is None or not "".join(n.find(MML + "e").itertext()).strip()]
    txt = xml.decode("utf-8")
    leaks = []
    for pat, name in ((r"\*\*", "bold marker"), (r"(?<!\\)\$\$?", "dollar"),
                      (r"^\|", "table pipe"), (r"!\[", "image marker")):
        if re.search(pat, txt, flags=re.M):
            leaks.append(name)
    print("\n--- built:", DOCX)
    print("paragraphs %d | tables %d | images %d | oMath %d | nary %d (empty %d)"
          % (n_par, n_tbl, n_img, n_omml, n_nary, len(empty)))
    print("math converted OK: %d ; failed: %d" % (stats["math"], len(stats["math_fail"])))
    if leaks:
        issues.append("leaked markdown in docx: %s" % ", ".join(leaks))
    if empty:
        issues.append("%d nary operators with an empty operand (renders as a box)" % len(empty))
    # independent re-check on the written file: no raw LaTeX may survive as math text
    leaked = [(t.text or "").strip() for t in root.iter(MML + "t")
              if t.text and "\\" in t.text]
    if leaked:
        issues.append("raw LaTeX leaked into math text: %s"
                      % ", ".join(sorted(set(repr(x) for x in leaked))))
    if stats["math_fail"]:
        issues.append("%d expressions failed to convert" % len(stats["math_fail"]))
    if issues:
        print("ISSUES:")
        for x in issues:
            print("  -", x)
        return 1
    print("VERIFY OK")
    return 0


if __name__ == "__main__":
    sys.exit(build(dry="--dry" in sys.argv))
