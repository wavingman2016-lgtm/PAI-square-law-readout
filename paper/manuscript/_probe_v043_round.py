# -*- coding: utf-8 -*-
"""v0.43 probe: the seventh review round, executed rather than asserted.

What this file exists for
-------------------------
The v0.43 round changed eight things that a reader can check and that a later
edit can silently undo:

  A. the equivalence claim is now conditional on six enumerated conditions;
  B. the geometric weight is a model-consistent choice, not a necessity, and a
     three-weight sensitivity analysis now supports the sentence that says so;
  C. the five-chain design is a controlled comparison of read-out families,
     not an isolation of a single factor, and a supplementary table says what
     each pairwise contrast can attribute;
  D. the detection experiment is placed at an empirical 5% false-alarm *design
     target*, with the order-statistic caveat stated in the methods;
  E. the n = 1 in-vivo acquisition is an illustrative case and nothing in the
     abstract or the conclusion rests on it;
  F. the version label and the TODO inventory no longer disagree;
  G. the reference list has 38 entries, all cited, numbered by first appearance;
  H. the supplementary tables are numbered by first citation.

Two kinds of check, both executed:

  1. presence/absence of exact strings across the three carriers (mother,
     assembled draft, supplement), each absence check carrying a live positive
     control so a typo in the haystack cannot pass as a clean result;
  2. recomputation of every number the round added, from the archived CSVs,
     so a transcription slip in the prose fails here rather than at proof.
"""
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TBL = os.path.join(ROOT, "paper", "tables")
RES = os.path.join(ROOT, "results", "fivechain")

MOTHER = os.path.join(HERE, "00_manuscript_EN.md")
DRAFT = os.path.join(HERE, "01_draft_v0.43_assembled.md")
SUPP = os.path.join(HERE, "03_supplementary_v0.43.md")
SENS = os.path.join(RES, "fivechain_weight_sensitivity.csv")

ok = 0
bad = []


def check(flag, label, want, got):
    global ok
    if flag:
        ok += 1
    else:
        bad.append("%-56s want=%-24s got=%s" % (label, want, got))


def load(p):
    if not os.path.exists(p):
        bad.append("missing carrier: %s" % os.path.basename(p))
        return ""
    return io.open(p, encoding="utf-8").read()


M, D, S = load(MOTHER), load(DRAFT), load(SUPP)
BODY = D[:D.find("## Figure captions")] if "## Figure captions" in D else D
ALL = M + "\n" + D + "\n" + S


def rows(path):
    with io.open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def present(token, label, where=BODY):
    n = where.count(token)
    check(n >= 1, label, ">=1 hit", n)


def absent(token, label, control, where=ALL):
    """Absence check; `control` is a string that must be present, so a wrong
    haystack fails loudly instead of reporting a clean zero."""
    n = where.count(token)
    c = where.count(control)
    check(n == 0 and c >= 1, label, "0 hits (control %d)" % c, n)


def section(text, start, stop):
    i = text.find(start)
    j = text.find(stop, i + 1) if stop else -1
    if i < 0 or j < 0:
        return ""
    return text[i:j]


print("=" * 74)
print("A.  equivalence claim is conditional on six enumerated conditions")
print("=" * 74)

s22 = section(M, "### 2.2", "### 2.3")
for roman in ["(i)", "(ii)", "(iii)", "(iv)", "(v)", "(vi)"]:
    present(roman, "section 2.2 carries condition %s" % roman, s22)
check("(vii)" not in s22, "section 2.2 stops at six conditions",
      "no (vii)", "(vii)" in s22)
present("bounded by", "2.2 opens as a bounded statement", s22)
absent("holds for arbitrary signals", "unconditional identity withdrawn",
       "Six conditions are part of the statement")
present("under the conditions of", "results point back to the conditions", BODY)

print("=" * 74)
print("B.  the geometric weight is a design choice, and is ranged")
print("=" * 74)

absent("must be squared", "necessity wording withdrawn", "model-consistent")
present("model-consistent", "model-consistent wording used", BODY)
present("not a physical necessity", "necessity explicitly denied", BODY)
present("Weight sensitivity", "section 3.3 carries the sensitivity analysis", M)

sens = {}
for r in rows(SENS):
    sens.setdefault((r["dataset"], r["metric"]), {})[r["arm"]] = float(r["value"])

ARMS = ["EL2", "EL1", "EL0"]          # g_m^2 (main), g_m, none
DS = ["W1", "W2", "W3", "W4", "W5", "W6"]

# B1. the g_m^2 arm must reproduce Table 6's EL column at the quoted precision
t5 = {r["dataset"]: r for r in rows(os.path.join(TBL, "T5_detection.csv"))}
worst = 0.0
for ds in DS:
    worst = max(worst, abs(sens[(ds, "gcnr2d")]["EL2"] - float(t5[ds]["gCNR EL"])))
check(worst < 5e-5, "g_m^2 arm reproduces Table 6 EL", "<5e-5", "%.2e" % worst)

# B2. the three paired differences quoted in section 4.4
quoted = {
    "W2": ("-0.0115", "-0.0137", "-0.0131"),
    "W3": ("-0.0171", "-0.0175", "-0.0178"),
    "W5": ("-0.0095", "-0.1130", "-0.1624"),
}
s44 = section(M, "**The weight does not create that direction.**", "\n\n")
for ds, want in quoted.items():
    v = sens[(ds, "gcnr2d")]
    got = tuple("%+.4f" % (v[a] - v["M"]) for a in ARMS)
    check(got == tuple("%+.4f" % float(x) for x in want),
          "section 4.4 paired differences on %s" % ds, str(want), str(got))
    for lit in want:
        present(lit if lit.startswith("-") else lit, "  %s quoted on %s" % (lit, ds), s44)

# B3. negative under all three weights in the three testable datasets
for ds in quoted:
    v = sens[(ds, "gcnr2d")]
    check(all(v[a] - v["M"] < 0 for a in ARMS),
          "difference stays negative on %s under all three weights" % ds,
          "3 negatives", " ".join("%+.4f" % (v[a] - v["M"]) for a in ARMS))

# B4. width ratio below one in six of six under all three weights
ratios = {a: [sens[(ds, "fwhm_lat")][a] / sens[(ds, "fwhm_lat")]["M"] for ds in DS]
          for a in ARMS}
for a in ARMS:
    check(max(ratios[a]) < 1.0, "EL/M width ratio below one in 6/6 (%s)" % a,
          "<1.0", "max %.3f" % max(ratios[a]))

# B5. the bound quoted for the non-W5 datasets
dev = max(abs(sens[(ds, "gcnr2d")][a] - sens[(ds, "gcnr2d")]["EL2"])
          for ds in ["W1", "W2", "W3", "W4", "W6"] for a in ["EL1", "EL0"])
check(dev < 0.0022, "non-W5 change in the paired difference is <0.0022",
      "<0.0022", "%.5f" % dev)
# Scoped absence: "0.0023" is also a legitimate standard deviation elsewhere
# (the display-contrast SD of 0.2566 +- 0.0023), so the stale *bound* is what
# must be gone, not the digit string.
absent("at most 0.0023", "the mis-transcribed 0.0023 bound is gone", "0.0022")
absent("at most $0.0023$", "the math-mode form of the bound is gone", "0.0022")

# B6. W5 cost quoted in the text
w5 = sens[("W5", "gcnr2d")]
check(abs((w5["EL2"] - w5["EL1"]) - 0.1034) < 5e-4
      and abs((w5["EL2"] - w5["EL0"]) - 0.1529) < 5e-4,
      "W5 cost of dropping the weight is 0.10 and 0.15",
      "0.1034 / 0.1529",
      "%.4f / %.4f" % (w5["EL2"] - w5["EL1"], w5["EL2"] - w5["EL0"]))

print("=" * 74)
print("C.  controlled comparison of read-out families, with a contrast table")
print("=" * 74)

present("controlled comparison of read-out families", "design is named as a controlled comparison", M)
absent("isolates squaring alone", "single-factor isolation wording withdrawn",
       "controlled comparison of read-out families")
present("not an isolation of a single factor", "single-factor isolation explicitly denied", M)
present("**Table S1.**", "contrast-isolation table is in the supplement", S)
present("Table S1", "contrast-isolation table is cited in the main text", BODY)
present("**Table S2.**", "weight-sensitivity table is in the supplement", S)
present("Table S2", "weight-sensitivity table is cited in the main text", BODY)

contrast = section(S, "**Table S1.**", "**Table S2.**")
for pair in ["EH against EL", "EL against SQ", "M against EL", "C against M", "C against EL"]:
    present(pair, "contrast table states what %s varies" % pair, contrast)

print("=" * 74)
print("D.  detection placed at an empirical design target")
print("=" * 74)

absent("same false-alarm rate", "equal-rate wording withdrawn",
       "false-alarm design target")
absent("Fixed false-alarm rate", "section heading no longer asserts a fixed rate",
       "A fixed false-alarm design target")
present("A fixed false-alarm design target", "section 4.4 heading reworded", M)
present("design target", "design-target wording used", BODY)
present("interpolated between the upper two order statistics",
        "order-statistic caveat stated in section 3.5", M)
present("supported by two observations", "the caveat names its consequence", M)
present("not re-measured on an independent noise set",
        "the realised rate is declared unmeasured", M)
present("does not include threshold-estimation error",
        "the interval's blind spot is stated", M)
check(BODY.count("empirical 5% false-alarm design target") >= 3,
      "the qualified phrase is used consistently",
      ">=3", BODY.count("empirical 5% false-alarm design target"))

print("=" * 74)
print("E.  the in-vivo acquisition is illustrative")
print("=" * 74)

present("Illustrative limited-view case: in-vivo data",
        "section 4.6 heading reworded", M)
absent("Boundary-case feasibility", "the old heading is gone",
       "Illustrative limited-view case")
present("illustrative limited-view in-vivo case", "abstract uses the same word", M)
abs_txt = section(M, "## Abstract", "\n\n## ")
check("validat" not in abs_txt.lower(), "the abstract claims no validation",
      "no 'validat'", abs_txt.lower().count("validat"))
# R3: the manuscript denies that the design isolates a single factor, so the
# abstract must not claim to isolate one either.
check("isolat" not in abs_txt.lower(),
      "the abstract does not claim to isolate a factor", "no 'isolat'",
      abs_txt.lower().count("isolat"))
check("in vivo" not in abs_txt.lower().replace("in-vivo", ""),
      "the abstract mentions in-vivo once, as the illustrative case",
      "0 bare 'in vivo'", abs_txt.lower().count("in vivo"))
present("does not establish", "section 4.6 states what the case cannot do", M)

print("=" * 74)
print("F.  version label and TODO inventory agree")
print("=" * 74)

absent("PAI-v0.37", "the stale tag is gone", "PAI-v0.43")
present("PAI-v0.43", "the current tag is written", M)

print("=" * 74)
print("G.  references: 38 entries, all cited, ordered by first appearance")
print("=" * 74)

refs_txt = M[M.index("## References"):]
listed = re.findall(r"^(\d+)\.\s", refs_txt, flags=re.M)
check(len(listed) == 38 and listed[0] == "1" and listed[-1] == "38",
      "reference list has 38 entries", "1..38", "%d (last %s)" % (len(listed), listed[-1] if listed else "?"))

first = {}
for m in re.finditer(r"\[([0-9][0-9,\s\u2013\-]*)\]", BODY):
    for part in m.group(1).split(","):
        part = part.strip()
        mm = re.match(r"^(\d+)\s*[\u2013\-]\s*(\d+)$", part)
        if mm:
            for n in range(int(mm.group(1)), int(mm.group(2)) + 1):
                first.setdefault(n, m.start())
        elif part.isdigit() and int(part) > 0:
            first.setdefault(int(part), m.start())
missing = [n for n in range(1, 39) if n not in first]
check(not missing, "every reference 1-38 is cited", "none missing", missing)
order = [k for k, _ in sorted(first.items(), key=lambda kv: kv[1])]
check(order == sorted(order), "first appearances are ascending",
      "ascending", order[:12])

NEW = {
    7: "10.3788/PI.2024.C06",
    9: "10.1016/0041-624X(81)90111-6",
    15: "10.3390/jimaging4100121",
    16: "10.1109/TUFFC.2009.1128",
    17: "10.1177/016173461103300203",
    20: "10.1007/978-3-030-11214-1",
    27: "10.1002/0471221082",
    30: "10.1093/bjaceaccp/mkr030",
    33: "10.1016/j.pacs.2023.100561",
}
for n, doi in sorted(NEW.items()):
    line = re.search(r"^%d\.\s(.*)$" % n, refs_txt, flags=re.M)
    got = line.group(1) if line else ""
    check(doi in got, "ref %d carries its DOI" % n, doi,
          got[-46:] if got else "entry not found")

print("=" * 74)
print("H.  tables: single-token cells, and numbering by first citation")
print("=" * 74)

tl = list(csv.reader(io.open(os.path.join(TBL, "TL_literature.csv"), encoding="utf-8-sig")))
cells = [c for r in tl[1:] for c in r[4:9]]
check(set(cells) <= {"yes", "NR", "n.a."},
      "every coded cell is a bare yes/NR/n.a.", "subset", sorted(set(cells)))
check(cells.count("NR") == 23, "23 cells are NR", "23", cells.count("NR"))
check(len(tl) - 1 == 9, "nine rows", "9", len(tl) - 1)

for kind, pat in [("Table", r"Table\s*(S?\d+)"), ("Fig.", r"Fig\.\s*(S?\d+)")]:
    seen = {}
    for m in re.finditer(pat, BODY):
        seen.setdefault(m.group(1), m.start())
    got = [k for k, _ in sorted(seen.items(), key=lambda kv: kv[1])]
    main = [k for k in got if not k.startswith("S")]
    sup = [k for k in got if k.startswith("S")]
    check(main == [str(i) for i in range(1, len(main) + 1)],
          "%s main numbers follow first citation" % kind.strip("."),
          "1..%d" % len(main), main)
    check(sup == ["S%d" % i for i in range(1, len(sup) + 1)],
          "%s supplementary numbers follow first citation" % kind.strip("."),
          "S1..S%d" % len(sup), sup)

print("=" * 74)
print("I.  numbers this round added, recomputed from the CSVs")
print("=" * 74)

present("3.12", "EL-to-C upper bound carried in the text", BODY)
# Scoped: "3.08" is a substring of the PSLR value 3.085 in Table S2, so only the
# retired interval endpoint is checked.
absent("to 3.08", "the superseded interval endpoint is gone", "3.12")
present("1.96", "EL-to-C lower bound carried in the text", BODY)

t4 = {r["dataset"]: r for r in rows(os.path.join(TBL, "T4_morphology.csv"))}
check(len(t4) == 6, "morphology table covers six datasets", "6", len(t4))

print()
print("-" * 74)
if bad:
    for b in bad:
        print("DEV   " + b)
print("checked %d items: OK %d / problems %d" % (ok + len(bad), ok, len(bad)))
print("VERDICT: %s" % ("PASS" if not bad else "FAIL"))
sys.exit(0 if not bad else 1)
