# -*- coding: utf-8 -*-
"""v0.33 self-audit probe.

Purpose: catch, before delivery, the classes of error that this round actually
produced.  Every check has a positive control wherever a string is expected to be
absent, so a dead control fails loudly instead of passing silently.

Sections
  1. PROSE residuals   — withdrawn strings, must all be absent from the delivery
                         interval (from '## Title' to '## Figure captions (draft)').
  2. PROSE presence    — replacement wording, must all be present.
  3. TEXT <-> TABLE    — numbers quoted in the text must exist in the table CSV
                         they claim to come from (and vice versa for the headline
                         paired differences).
  4. CITATIONS         — references 1..25 all cited, first appearances ascending.
  5. TABLE/FIGURE ORDER— main tables and main figures numbered by first citation.
  6. ABSTRACT/HIGHLIGHTS — word count via the official _wordcount.py, <=500; each
                         highlight <=85 characters.

Run:  python paper/manuscript/_probe_v033_selfaudit.py
Exit: 0 all pass, 2 at least one FAIL.
"""
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MS = os.path.join(HERE, "00_manuscript_EN.md")
AD = os.path.join(HERE, "01_draft_v0.48_assembled.md")
TBL = os.path.join(ROOT, "paper", "tables")

sys.path.insert(0, HERE)
import _wordcount as WC  # noqa: E402  (official counter, do not reimplement)

ms = io.open(MS, encoding="utf-8").read()
ad = io.open(AD, encoding="utf-8").read()
body = ad[ad.index("## Title"):ad.index("## References")]
body_w = re.sub(r"\s+", " ", body)
ms_w = re.sub(r"\s+", " ", ms)

FAIL = []


def check(name, cond, detail=""):
    tag = "OK" if cond else "FAIL"
    if not cond:
        FAIL.append(name)
    print("  %-58s %s%s" % (name, tag, ("  " + detail) if detail and not cond else ""))


def read(name):
    p = os.path.join(TBL, name)
    return io.open(p, encoding="utf-8-sig").read() if os.path.exists(p) else ""


print("=== 1. PROSE residuals (must all be absent) ===")
RESID = [
    # v0.33-internal corrections
    "second-order zero-phase Butterworth",
    "0.35\u20132.00 MHz",
    "128\u2013256 channels",
    "loses separability in five of six",
    "loses separability in 5 of 6",
    "exceeds $SQ$ in five of six",
    "it costs separability in 5 of 6",
    "The ordering is the same everywhere",
    "C is narrowest, SQ next",
    "65% of its peak at",
    "clips 8.0% of EL",
    "clutter robustness",
    "monetary cost",
    # v0.33 第二轮：数字与计数口径被本轮数据推翻
    "$EL/EH$ constant at 1.999",
    "1.999\\pm0.002",
    "at least as separable as $SQ$ in five of six",
    "a favourable cost",
    "clearly preferable to the bare square",
    "they differ by at most 0.2%",
    # standing bans carried from earlier rounds
    "energy-domain",
    "energy-type",
    "quantitative energy imaging",
    "SNR improvement",
    "improves the SNR",
    "improves spatial resolution",
    "improves the spatial resolution",
    "enhances resolution",
    "Hilbert-free is faster",
    "Hilbert is the main cost",
    "omitting the Hilbert transform is the main",
    "the bare square is the squared envelope",
    "65-bin",
    "601-bin",
    "bounds folding",
    "independent folding control",
    "PLACEHOLDER_",
]
for s in RESID:
    check("absent: %s" % s[:46], s not in body_w, "found in delivery interval")

# 铁律：箭头必须查两种字形。v0.31 的漏检根因就是只查了 Unicode 一种。
for glyph, nm in (("->", "ASCII ->"), ("\u2192", "Unicode U+2192")):
    check("absent: %s in delivery interval" % nm, glyph not in body_w,
          "found in delivery interval")
# 阳性对照：证明上面两条断言真的能命中，而不是恒过的死断言
_probe_arrows = "A -> B \u2192 C"
check("control: arrow detector actually fires",
      ("->" in _probe_arrows) and ("\u2192" in _probe_arrows))

print("\n=== 2. PROSE presence (positive controls) ===")
PRESENT = [
    ("sixth-order filter", "sixth-order zero-phase Butterworth"),
    ("frequency span", "0.35\u20135.00 MHz"),
    ("array span", "32- and 128-element arrays"),
    ("SQ count", "the count is three of six and not five of six"),
    ("strict SQ count", "strictly positive in three datasets"),
    ("EH/EL ratio", "$2.002$"),
    ("width spread", "at most 0.44%"),
    ("width non-uniformity", "is **not** uniform"),
    ("W2 profile numbers", "36\u201344% of its own maximum"),
    ("W4 black-clip", "black-clips only 0.6% of EL"),
    ("W4 saturation", "saturates 19.0% of the pixels of M"),
    ("percentile window", "clip about 1% in every case"),
    ("limited-view citation", "view-dependent [39]"),
    ("gCNR citation", "primary detection endpoint [33]"),
]
for name, s in PRESENT:
    check("present: %s" % name, s in body_w)

print("\n=== 3. TEXT <-> TABLE consistency ===")
t5 = read("T5_detection.csv")
t4 = read("T4_morphology.csv")
t3 = read("T3_sim_summary.csv")
ts1 = read("TS1_equivalence.csv")

# headline paired differences quoted in prose must appear in Table 5
for v in ["+0.1881", "+0.1339", "+0.0765", "+0.0482", "+0.0114",
          "-0.0115", "-0.0171", "-0.0095",
          "+0.3978", "+0.0997", "+0.0127", "-0.0071"]:
    check("Table 5 carries %s" % v, v in t5)
# and the text must quote the two largest of them
for v in ["+0.1881", "+0.3978"]:
    check("text quotes %s" % v, v in body_w)

# equivalence headline —— 必须真的从 Table S1 算出来，不能写 or True（那是死断言）
ts1_rows = list(csv.DictReader(io.StringIO(ts1)))
pear = [float(r["Pearson"]) for r in ts1_rows if r.get("Pearson")]
check("Table S1 has Pearson column", bool(pear), "rows=%d" % len(ts1_rows))
if pear:
    check("Table S1 min Pearson rounds to >= 0.99998",
          min(pear) >= 0.999975, "min=%.8f" % min(pear))
check("text quotes 0.99998", "0.99998" in body_w)
check("text quotes 1.17%", "1.17%" in body_w)
check("text quotes 62.6%", "62.6%" in body_w)

# a50 的末位：正文与 Table 3 必须同一个数（0.00446 曾与表中的 4.45 矛盾）
a50_row = next((r for r in csv.DictReader(io.StringIO(t3)) if r["quantity"].startswith("a50")), None)
if a50_row:
    el_milli = float(a50_row["EL"])
    check("Table 3 a50 EL = 4.45 (x1e-3)", abs(el_milli - 4.45) < 0.005, "got %s" % el_milli)
    check("text a50 EL matches Table 3 at 3 s.f.",
          "0.00455, 0.00455 and 0.00445" in body_w,
          "expected 0.00445 (= 4.45e-3 from the table)")
check("withdrawn 0.00446 is gone from the body", "0.00446" not in body_w)

# the realisation residual is quoted in both forms in section 4.1 and as a percentage
# in the abstract; both must be present, and they must be the same number.
check("body carries 0.0117 and 1.17% (same residual, two forms)",
      ("0.0117" in body_w) and ("1.17%" in body_w),
      "0.0117=%s 1.17%%=%s" % ("0.0117" in body_w, "1.17%" in body_w))

# morphology ratio range must match the table
ratios = []
for row in csv.DictReader(io.StringIO(t4)):
    if row["metric"] == "lateral FWHM (mm)":
        ratios.append(float(row["EL"]) / float(row["M"]))
if ratios:
    lo, hi = min(ratios), max(ratios)
    check("Table 4 lateral EL/M range %.2f-%.2f quoted" % (lo, hi),
          ("0.37\u20130.92" in body_w) and abs(lo - 0.37) < 0.006 and abs(hi - 0.92) < 0.006,
          "table says %.3f-%.3f" % (lo, hi))

# ---- S2 cross-checks: every quoted S2 number must exist in Table 3 ----
# 这些数字是本轮新算出来的，正文与表必须同源。表中以不同精度/单位出现，
# 所以在表文本里找"数值本身"，在正文里找"引用的写法"。
t3nums = []
for row in csv.DictReader(io.StringIO(t3)):
    t3nums.extend(row.get(k, "") for k in ("C", "M", "EH", "EL", "SQ"))
t3flat = " ".join(t3nums)

check("Table 3 has a50 row", "a50 at 5% false-alarm design target" in t3)
# 表里 a50 以 x1e-3 记（1.86 / 4.55 / 4.45 / 3.86），不是 0.00186，直接比值。
for txt, v in (("EL a50", "4.45"), ("C a50", "1.86"), ("SQ a50", "3.86"),
               ("M a50", "4.55")):
    check("Table 3 carries %s = %s x1e-3" % (txt, v),
          any(x == v for x in t3nums),
          "not in table")
# 正文必须引用 a50 的两位写法（1.86e-3 与 4.46e-3 一类），不许只在表里出现
for txt in ("0.0019", "0.0039", "0.0045", "2.4 times"):
    check("text quotes %s" % txt, txt in body_w)

# E 段：三层比值必须同时出现在表与正文
for txt in ("0.984", "0.445", "0.960", "1.88"):
    check("Table 3 carries timing %s" % txt, txt in t3)
check("text quotes end-to-end 0.984", "0.984" in body_w)
check("text quotes 2.25 times", "2.25" in body_w)
check("text quotes 1.86-fold", "1.86" in body_w)

# D 段：显示对比度的四条数字必须与表一致（D 在 TS2，不在 T3）
ts2 = read("TS2_sim_detail.csv")
check("TS2 carries weak contrast 0.3697", "0.3697" in ts2)
check("text quotes 0.3697", "0.3697" in body_w)
check("text quotes 0.2566", "0.2566" in body_w)
check("text quotes 0.1821", "0.1821" in body_w)

# 禁止把饱和并列说成"并列/平局"以外的含义：NA 口径仍须在场
check("NA wording kept", "not testable" in body_w)
check("no zero-for-NA", "+0.0000" not in body_w)

print("\n=== 4. CITATIONS ===")
refs_txt = ms[ms.index("## References"):]
listed = re.findall(r"^(\d+)\.\s", refs_txt, flags=re.M)
check("reference list has 51 entries", len(listed) == 51 and listed[0] == "1",
      "found %d" % len(listed))
first = {}
for m in re.finditer(r"\[([0-9][0-9,\s\u2013\-]*)\]", body_w):
    for part in m.group(1).split(","):
        part = part.strip()
        mm = re.match(r"^(\d+)\s*[\u2013\-]\s*(\d+)$", part)
        if mm:
            for n in range(int(mm.group(1)), int(mm.group(2)) + 1):
                if n > 0:
                    first.setdefault(n, m.start())
        elif part.isdigit() and int(part) > 0:
            first.setdefault(int(part), m.start())
missing = [n for n in range(1, 39) if n not in first]
check("every reference 1-38 cited", not missing, "never cited: %s" % missing)
order = [k for k, _ in sorted(first.items(), key=lambda kv: kv[1])]
check("first appearances ascending", order == sorted(order),
      "order: %s" % order[:30])

print("\n=== 5. TABLE / FIGURE ORDER ===")
seq = []
for m in re.finditer(r"(Table|Fig\.)\s*(S?\d+)", body_w):
    seq.append((m.group(1), m.group(2)))
for kind in ("Table", "Fig."):
    main = [int(n) for k, n in seq if k == kind and not n.startswith("S")]
    seen, uniq = set(), []
    for n in main:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    check("%s main numbers in citation order" % kind.strip("."),
          uniq == sorted(uniq) and uniq == list(range(1, len(uniq) + 1)),
          "order: %s" % uniq)

print("\n=== 6. ABSTRACT / HIGHLIGHTS ===")
i0 = ms.index("## Abstract")
i1 = ms.index("---", i0)
ab = re.sub(r"^## Abstract", "", ms[i0:i1])
nA = WC.count_a(ab) if hasattr(WC, "count_a") else None
if nA is None:
    import subprocess
    out = subprocess.run([sys.executable, os.path.join(HERE, "_wordcount.py")],
                         capture_output=True, text=True).stdout
    m = re.search(r"convention A[^:]*:\s*(\d+)", out)
    nA = int(m.group(1)) if m else -1
check("abstract <= 500 words (convention A)", 0 < nA <= 500, "got %s" % nA)
print("      abstract words (A): %d" % nA)

for ln in ms.split("\n"):
    if ln.startswith("- ") and "Highlights" not in ln:
        pass
hl_block = ms[ms.index("**Highlights**"):ms.index("**Keywords**")]
hl = [ln[2:].strip() for ln in hl_block.split("\n") if ln.startswith("- ")]
bad = [h for h in hl if len(h) > 85]
check("highlights block has 3-5 items", 3 <= len(hl) <= 5, "found %d" % len(hl))
check("highlights <= 85 chars each", bool(hl) and not bad, "too long: %s" % [b[:40] for b in bad])

print("\n=== 7. ABSTRACT AS PLAIN TEXT (DOCX) ===")
# 第三节评审报告称摘要的数字被"压坏"（1.97.3 / 0.0171 to 0.0095 / 62.6 …）。
# 逐字比对后确认：DOCX 里的字符是完整的，被吞掉的是 % 与 U+2212 / U+2013，
# 且数学域（OMML）在纯文本抽取中会被整段丢弃。摘要要能原样粘进投稿系统，
# 因此 v0.37 把摘要改成零 OMML、区间写成 "to"、比值写成 "EH-to-EL"。
# 这里用最笨的抽取方式（只取 w:t，不取 m:t）验证它仍然可读。
import zipfile  # noqa: E402

dx = os.path.join(HERE, "02_PAI_manuscript_v0.48_draft.docx")
_xml = zipfile.ZipFile(dx).read("word/document.xml").decode("utf-8")
check("DOCX contains maths elsewhere (positive control)", _xml.count("<m:oMath") > 100,
      "found %d" % _xml.count("<m:oMath"))
_paras = re.findall(r"<w:p[ >].*?</w:p>", _xml, re.S)


def _wt(p):
    return "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S))


# The anchor is deliberately a short, stable phrase rather than the whole first
# sentence: an anchor tied to the full wording turns any rewrite of that sentence
# into a false report that the abstract is missing (v0.38 rewrote it and the probe
# failed for exactly that reason).
_AB_ANCHOR = "reconstructs a pressure amplitude"

_ab, _on = [], False
for _p in _paras:
    _s = _wt(_p)
    if _AB_ANCHOR in _s:
        _on = True
    elif not _on:
        continue
    if _s.strip().endswith("Introduction") or _s.strip().startswith("Keywords"):
        break
    _ab.append(_p)
_abtxt = " ".join(_wt(p) for p in _ab)
check("abstract located in DOCX", len(_ab) >= 4, "paragraphs %d" % len(_ab))
check("abstract carries no OMML maths", all("<m:oMath" not in p for p in _ab),
      "math in %d paragraphs" % sum(1 for p in _ab if "<m:oMath" in p))
# v0.38 states this residual in the percentage form only, to stay inside the 500-word
# limit; the normalised value 0.0117 is still carried by section 4.1 and is asserted
# on the body below, so dropping it here narrows the abstract check without losing
# the underlying number.
for _tok in ("1.17%", "1.00 mm", "1.50 mm",
             "at a common empirical 5% false-alarm design target", "EL", "EH"):
    check("abstract plain-text token %s" % _tok, _tok in _abtxt, "missing")
# v0.44 cut the abstract to four information units and two numbers.  The tokens below
# left the abstract by design and must now be absent from it; each is still carried by
# the results section, and the body check above keeps it alive there.
for _tok in ("62.6%", "0.4%", "0.40 mm", "2.002", "0.0019", "1.88-fold", "0.1881"):
    check("abstract no longer carries %s" % _tok, _tok not in _abtxt, "still present")
check("no empty parentheses in abstract", "()" not in _abtxt, "found a bare ()")

print("\n" + "=" * 62)
if FAIL:
    print("VERDICT: FAIL (%d)" % len(FAIL))
    for f in FAIL:
        print("   -", f)
    sys.exit(2)
print("VERDICT: PASS")
