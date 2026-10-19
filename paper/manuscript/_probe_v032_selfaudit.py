# -*- coding: utf-8 -*-
"""v0.32 self-audit probe (ninth-round review execution).

Guards three things this round changed, each with a positive control so a dead
control fails loudly instead of silently:

  1. PROSE residuals — the round-9 withdrawn strings must be absent from the
     DELIVERY INTERVAL (from '## Title' to '## Figure captions (draft)'); the
     front-matter changelog legitimately quotes some of them as historical
     records and is NOT scanned.
  2. NEW wording — each round-9 replacement must actually be present.
  3. CARRIERS — TableS1_config_audit.csv / Table03_registry.csv must carry the
     W5 "historical / not verifiable" disclosure, not the old "measured / same
     rule as W4".

Plus the standing gates: Highlights <=85 chars, abstract word count (official
_wordcount.py) <= 500 and equal to the changelog's quoted 494.

Run:  python paper/manuscript/_probe_v032_selfaudit.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MS = os.path.join(HERE, "00_manuscript_EN.md")
AD = os.path.join(HERE, "01_draft_v0.32_assembled.md")
T1 = os.path.join(ROOT, "paper", "tables", "TableS1_config_audit.csv")
T3 = os.path.join(ROOT, "paper", "tables", "Table03_registry.csv")

ms = io.open(MS, encoding="utf-8").read()
body = ms[ms.index("## Title"):ms.index("## Figure captions (draft)")]
body_w = re.sub(r"\s+", " ", body)

FAIL = []


def check(name, cond, detail=""):
    tag = "OK" if cond else "FAIL"
    if not cond:
        FAIL.append(name)
    print("  %-52s %s%s" % (name, tag, ("  " + detail) if detail and not cond else ""))


print("=== 1. PROSE residuals (delivery interval; must all be 0) ===")
RESID = [
    "independent raised-sampling-rate folding control",
    "independent folding control",
    "detected no upsampling-induced change",
    "bounds folding",
    "bounded by the independent",
    "binning-free alternative estimator",
    "binning-free (KS)",
    "binning-free variation",
    "robust to background de-contamination",
    "no difference is defined there",
    "no dataset shows E ahead",
    "15-scenario",
    "trend mean",
    "carried literal",
    "8 of the 15",
    "7 of the 15",
    "+0.247",
    "Exploratory evidence",
    "Core evidence",
    "4/4 testable",
    "disagree in sign",
    "65-bin",
    "601 -> 1501",
    "601 \u2192 1501",
    "harmless here",
]
for pat in RESID:
    n = len(re.findall(re.escape(pat), body))
    check("residual: %s" % pat, n == 0, "%d hit(s)" % n)

print("=== 2. NEW wording (positive controls; must all be present) ===")
POS = [
    ("resampling sensitivity check", 1),
    ("does not separate", 1),
    ("complementary distribution-difference metric", 1),
    ("background-median-normalized distribution distance", 1),
    ("two-point resolution limit", 1),
    ("no consistent E advantage", 1),
    ("KS-distance variation", 1),
    ("not verifiable", 1),
    ("0.50 mm", 1),
    ("a majority of datasets", 1),
]
for pat, m in POS:
    n = len(re.findall(re.escape(pat), body))
    check("present: %s" % pat, n >= m, "%d < %d" % (n, m))

print("=== 3. CARRIER checks (TableS1 / Table03 W5) ===")
t1 = io.open(T1, encoding="utf-8").read()
t3 = io.open(T3, encoding="utf-8").read()


def csv_rows(text):
    import csv
    return list(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))))


r1 = {r["id"]: r for r in csv_rows(t1)}
r3 = {r["id"]: r for r in csv_rows(t3)}
w5 = r1.get("W5", {}); w6 = r1.get("W6", {}); w3r = r3.get("own5", {})
check("S1 W5 decision_basis no 'measured spectral peak'",
      "measured spectral peak" not in w5.get("decision_basis", ""))
check("S1 W5 decision_basis no 'Same rule as W4'",
      "Same rule as W4" not in w5.get("decision_basis", ""))
check("S1 W5 perf_metric = not verifiable",
      w5.get("perf_metric_used_in_choice", "").startswith("not verifiable"))
check("S1 W6 no 'W4/W5'",
      "W4/W5" not in w6.get("decision_basis", ""))
check("T3 W5 config = historical",
      "historical; provenance not recoverable" in w3r.get("validated_config", ""))
check("T3 W5 config not '(measured)'",
      "0.35 MHz (measured)" not in w3r.get("validated_config", ""))

print("=== 4. Standing gates ===")
hl = re.findall(r"^- (.+)$", ms[ms.index("**Highlights"):ms.index("**Keywords")], re.M)
hl = [h for h in hl if not h.strip().startswith("(")]
for h in hl:
    check("highlight <=85: %s..." % h[:30], len(h) <= 85, "%d chars" % len(h))

sys.path.insert(0, HERE)
import _wordcount as WC
prose = WC.strip_non_prose(WC.section(ms, "Abstract"))
n_a = WC.count(prose, WC.TOK_A)
check("abstract <= 500", n_a <= 500, "%d" % n_a)
q = re.search(r"re-settles at \*\*(\d+)\*\* words", ms)
if q:
    check("changelog quotes %d == computed %d" % (int(q.group(1)), n_a), int(q.group(1)) == n_a)

print()
if FAIL:
    print("=== VERDICT: FAIL === (%d item(s))" % len(FAIL))
    sys.exit(1)
print("=== VERDICT: PASS ===")
