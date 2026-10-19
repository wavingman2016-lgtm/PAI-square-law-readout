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
DRAFT = os.path.join(HERE, "01_draft_v0.48_assembled.md")
SUPP = os.path.join(HERE, "03_supplementary_v0.48.md")
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
s44 = section(M, "**The direction survives all three weights.**", "\n\n")
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
# v0.44 compresses the abstract, so the qualifier it must share with section 4.6 is
# "illustrative", not the full heading phrase.
present("illustrative in-vivo case", "abstract uses the same word", M)
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

absent("PAI-v0.47", "the stale tag is gone", "PAI-v0.48")
present("PAI-v0.48", "the current tag is written", M)

print("=" * 74)
print("G.  references: 51 entries, all cited, ordered by first appearance")
print("=" * 74)

refs_txt = M[M.index("## References"):]
listed = re.findall(r"^(\d+)\.\s", refs_txt, flags=re.M)
check(len(listed) == 51 and listed[0] == "1" and listed[-1] == "51",
      "reference list has 51 entries", "1..51", "%d (last %s)" % (len(listed), listed[-1] if listed else "?"))

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
missing = [n for n in range(1, 52) if n not in first]
check(not missing, "every reference 1-51 is cited", "none missing", missing)
order = [k for k, _ in sorted(first.items(), key=lambda kv: kv[1])]
check(order == sorted(order), "first appearances are ascending",
      "ascending", order[:12])

# v0.44 adds thirteen records, so the whole list is renumbered by first appearance.
# The numbers below are the v0.44 display numbers; each DOI is unchanged.
NEW = {
    7: "10.3788/PI.2024.C06",
    11: "10.1016/0041-624X(81)90111-6",
    15: "10.1177/016173469802000201",
    18: "10.3390/jimaging4100121",
    19: "10.1109/TUFFC.2009.1128",
    20: "10.1177/016173461103300203",
    21: "10.1117/1.JBO.23.2.026005",
    23: "10.1002/j.1538-7305.1945.tb00453.x",
    24: "10.1109/PROC.1967.5573",
    26: "10.1007/978-3-030-11214-1",
    34: "10.1364/BOE.391026",
    36: "10.1002/0471221082",
    37: "10.1016/S0001-2998(78)80014-2",
    38: "10.1002/0471722162",
    41: "10.1093/bjaceaccp/mkr030",
    42: "10.1103/PhysRevE.67.056605",
    43: "10.1088/0266-5611/26/12/125002",
    46: "10.1016/j.pacs.2023.100561",
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


print("=" * 74)
print("J.  the eighth review round: the changes a reader can check")
print("=" * 74)

# J1 title and running term
present("squared-amplitude read-out, apparent profile narrowing", "title uses the new term", BODY)
absent("power-domain contrast", "the retired title phrase is gone", "squared-amplitude read-out", BODY)
absent("apparent sharpening", "no sharpening in the title", "squared-amplitude read-out",
       BODY[BODY.find("## Title"):BODY.find("**Keywords**")])
present("*Squared-amplitude read-out* is the general name", "the term is defined once, in 2.3", BODY)
absent("power-domain read-out", "the retired running term is gone", "squared-amplitude read-out", BODY)

# J2 abstract: four units, two numbers, no maths
ab = section(M, "## Abstract", "## 1. Introduction")
ab_par = [p for p in ab.split("\n\n") if p.strip() and not p.startswith("##")]
check(len(ab_par) == 4, "abstract has four paragraphs", "4", len(ab_par))
ab_words = len(ab.replace("## Abstract", "").split())
check(228 <= ab_words <= 246, "abstract is 75-78% of the v0.44 length", "228..246 words", ab_words)
for tok in ("1.17%", "1.00 mm", "1.50 mm",
            "at a common empirical 5% false-alarm design target",
            "same acquisition, propagation geometry, delay model, interpolation, "
            "reconstruction grid, valid mask and summation framework",
            "two realizations of the same narrow-band, band-limited squared-envelope target"):
    present(tok, "abstract carries: %s" % tok[:44], ab)
check("$" not in ab, "abstract carries no maths", "0 dollars", ab.count("$"))

# J3 the shared-framework sentence travels with the claim
check(M.count("same acquisition, propagation geometry, delay model") == 3,
      "shared framework stated in abstract, 2.1 and 3.2",
      "3 in the mother", M.count("same acquisition, propagation geometry, delay model"))
check(S.count("same acquisition, propagation geometry, delay model") == 1,
      "Table S1 states the same framework",
      "1 in the supplement", S.count("same acquisition, propagation geometry, delay model"))
absent("shape of the point spread function", "no PSF-shape claim in 1.2",
       "apparent single-target response profile")
present("apparent single-target response profile", "response-profile wording used", BODY)

# J4 the two over-strong sentences
absent("a property of the read-out rather than of the weighting rule",
       "causal sentence about the weight retired",
       "robust to the three tested weighting choices")
present("robust to the three tested weighting choices", "robustness wording present", BODY)
absent("adequate to rank the chains", "the ranking licence is withdrawn",
       "does not certify an operating point")
present("does not certify an operating point", "the replacement caveat is present", BODY)

# J5 one canonical equality sentence, and no rival formulation
absent("one definition, two realizations", "the old formulation is gone",
       "two realizations of the same narrow-band")
EQ = "two realizations of the same narrow-band, band-limited squared-envelope target"
check(EQ in ab and EQ in section(M, "### 2.3", "### 2.4")
      and EQ in section(M, "## 7. Conclusion", "## Declarations"),
      "equality sentence stated in abstract, 2.3 and 7",
      "3 carriers", (EQ in ab, EQ in section(M, "### 2.3", "### 2.4"),
                     EQ in section(M, "## 7. Conclusion", "## Declarations")))

# J6 Goodman: no Gaussian-channel-equals-fully-developed-speckle
absent("in the fully developed case, exponential", "the over-reading is gone",
       "fully developed")
present("requires many independent phasors within the resolution cell",
        "the condition is stated instead of assumed", BODY)

# J7 structure: three discussion sections, seven claims
for h in ("### 5.1 What changes", "### 5.2 Why the rankings diverge",
          "### 5.3 Scope and practical use"):
    present(h, "discussion heading: %s" % h[4:], BODY)
check("### 5.4" not in BODY and "### 5.5" not in BODY,
      "no fourth or fifth discussion subsection", "none",
      BODY.count("### 5.4") + BODY.count("### 5.5"))
tc = list(csv.reader(io.open(os.path.join(TBL, "TC_claim_scope.csv"), encoding="utf-8-sig")))
check(len(tc) - 1 == 7, "Table 7 carries seven core claims", "7", len(tc) - 1)

# J8 the W5 marker
check(BODY.count("W5†") >= 7, "W5 is flagged wherever it is labelled", ">=7", BODY.count("W5†"))
check(BODY.count("† W5 carries") == 3, "the three affected captions define the dagger", "3",
      BODY.count("† W5 carries"))
present("is not used as the sole basis of any directional conclusion",
        "the standing of W5 is stated in the text", BODY)

# J9 the notes moved into the supplement
present("*Coding rule.*", "Table 1 coding rule now lives in Note S1", S)
present("*Per-cell evidence.*", "Table 1 per-cell evidence is in Note S1", S)
for row in ("**L1**", "**L2**", "**L3**", "**L4**", "**L5**", "**L6**"):
    present(row, "Note S1 codes row %s" % row[2:4], S)
present("**Note S2. Threshold and interpolation conventions", "Note S2 exists", S)
present("**Note S3. Statistical conventions", "Note S3 exists", S)
absent("moves $a_{50}$ by at most 2.5", "interpolation defence left the methods",
       "Note S2 states what the interpolation convention", BODY)

# J10 the thirteen added records are the ones cited, with their DOIs
refs_txt = M[M.index("## References"):]
for doi, label in [
        ("10.1002/j.1538-7305.1945.tb00453.x", "Rice 1945"),
        ("10.1109/PROC.1967.5573", "Urkowitz 1967"),
        ("10.1117/1.JBO.21.6.061007", "Zhou tutorial"),
        ("10.1038/nmeth.3925", "Wang & Yao guide"),
        ("10.21105/joss.05686", "PATATO toolkit"),
        ("10.1103/PhysRevE.67.056605", "Xu 2003 resolution"),
        ("10.1088/0266-5611/26/12/125002", "Haltmeier 2010"),
        ("10.1016/S0001-2998(78)80014-2", "Metz 1978"),
        ("10.1002/0471722162", "David & Nagaraja"),
        ("10.1364/BOE.391026", "Kempski 2020"),
        ("10.1109/TUFFC.2022.3169082", "Gubbi 2022"),
        ("10.1117/1.JBO.23.2.026005", "Mozaffarzadeh 2018"),
        ("10.1177/016173469802000201", "Jespersen 1998")]:
    present(doi, "reference DOI: %s" % label, refs_txt)
check(len(re.findall(r"^\d+\.\s", refs_txt, flags=re.M)) == 51,
      "thirteen records were added to thirty-eight", "51",
      len(re.findall(r"^\d+\.\s", refs_txt, flags=re.M)))

# J11 OADAT is cited at its canonical TMLR record
present("openreview.net/forum?id=BVi6MhKO0G", "OADAT cites the OpenReview forum", ALL)
present("no Crossref DOI is registered for the Transactions version",
        "the missing journal DOI is declared", ALL)

# J12 the new citations sit where the claims are
for frag, label in [("[23,24]", "square-law theory in 2.2"),
                    ("[9,10]", "analytic-signal implementation in 1.1"),
                    ("[9,14,15]", "envelope detection and compounding in 1.3"),
                    ("[19\u201321]", "coherence-weighted beamforming in 1.3"),
                    ("[34,35]", "gCNR ROI and saturation in 3.5"),
                    ("[37]", "ROC framing in 3.5"),
                    ("[38]", "order statistics in 3.5"),
                    ("[32]", "released toolkit in 3.3"),
                    ("[42,43]", "resolution theory in 5.2")]:
    present(frag, "citation group %s: %s" % (frag, label), BODY)

# J13 Table 1 cites the renumbered records
tl_rows = list(csv.reader(io.open(os.path.join(TBL, "TL_literature.csv"), encoding="utf-8-sig")))
tl_refs = {r[0]: r[-1] for r in tl_rows[1:]}
check(tl_refs.get("L2") == "[14]" and tl_refs.get("L4") == "[16]"
      and tl_refs.get("L5") == "[17]" and tl_refs.get("L6") == "[13]",
      "Table 1 reference column follows the renumbering", "[14]/[16]/[17]/[13]", tl_refs)


print("=" * 74)
print("K.  cross-references, and table order by first citation")
print("=" * 74)

heads = set(re.findall(r"^#{2,3} (\d+(?:\.\d+)?)", BODY, flags=re.M))
heads |= set(re.findall(r"^\*\*(\d+\.\d+) ", BODY, flags=re.M))
used = set(re.findall(r"\u00a7(\d+(?:\.\d+)?)", BODY))
dangling = sorted(used - heads)
check(not dangling, "every section reference resolves", "none", dangling)

# tables must be cited in numerical order (rule 8 of the version note)
seen = []
for m in re.finditer(r"Table (\d+)", section(BODY, "## Title", "## References")):
    n = int(m.group(1))
    if n not in seen:
        seen.append(n)
check(seen == sorted(seen) and seen[0] == 1,
      "tables are cited in ascending order", "1..7 ascending", seen)

figs = []
for m in re.finditer(r"Fig\. (\d+)", section(BODY, "## Title", "## References")):
    n = int(m.group(1))
    if n not in figs:
        figs.append(n)
check(figs == sorted(figs), "figures are cited in ascending order",
      "ascending", figs)


print("=" * 74)
print("L.  the ninth review round: abstract length, positioning, identity form")
print("=" * 74)

# L1 the abstract was cut again and kept its four units
check(228 <= ab_words <= 246, "abstract is 228-246 words", "228..246", ab_words)
check(len(ab_par) == 4, "abstract still has four paragraphs", "4", len(ab_par))
for gone in ("62.6%", "0.4%", "0.40 mm", "2.002", "0.0019", "1.88-fold", "0.1881",
             "display window", "black-clips"):
    absent(gone, "abstract no longer carries %s" % gone, "1.17%", ab)
present("endpoint-dependent", "abstract keeps the endpoint-dependence", ab)

# L2 the positioning sentence, in 1.4 and 7
POS = ("does not propose square-law detection as a new")
check(M.count(POS) == 2, "positioning sentence in 1.4 and 7", "2", M.count(POS))
present("controlled, task-based comparison of where a channel-wise squared-amplitude read-out is placed",
        "the comparison is named in section 7", M)

# L3 no 'requires' attached to the read-out or the weight
for bad_frag in ("read-out requires", "placement requires", "that function requires",
                 "that quantity requires", "that functional requires"):
    absent(bad_frag, "no '%s'" % bad_frag, "paired with that", BODY)
check(BODY.count("paired with that read-out") >= 2
      and BODY.count("paired with that placement") >= 1
      and BODY.count("paired with that quantity") >= 1
      and BODY.count("paired with that functional") >= 1,
      "every read-out/weight instance uses the paired-with form", "2/1/1/1",
      (BODY.count("paired with that read-out"), BODY.count("paired with that placement"),
       BODY.count("paired with that quantity"), BODY.count("paired with that functional")))

# L4 the identity is displayed with an approximation sign and a measured residual
present(r"2\,\mathrm{LPF}\{x^2\}\;\approx\;A^2=\lvert z\rvert^2",
        "identity displayed with approx", M)
present("the residual is what \u00a74.1 measures: at most 1.17% of the peak",
        "display is tied to the measured residual", M)
absent("What the low-pass guarantees", "no 'guarantees' for a finite-order filter", "attenuation, not elimination")
present("that removal is attenuation, not elimination", "the finite-order caveat is stated", M)

# L5 cost attribution is implementation-bound
present("specific to the present implementation and hardware environment",
        "cost attribution qualified", M)
present("the measured C\u2013EL gap was dominated by complex-valued rather than real-valued back-projection",
        "the same qualifier in section 7", M)

# L6 bootstrap caveat
present("quantify Monte Carlo uncertainty conditional on the estimated per-chain thresholds",
        "bootstrap caveat added", M)
present("do not include uncertainty in threshold estimation",
        "threshold uncertainty excluded explicitly", M)

# L7 retired words
absent("apparent sharpening", "no 'sharpening' anywhere", "apparent narrowing", BODY)
absent("routinely discussed", "the literature-sociology claim is retired",
       "treating these variants as interchangeable", BODY)

# L8 Fig. 5 caption matches the redrawn figure
present("summarised in the panel note rather than on the bars",
        "caption points at the panel note", BODY)
present("bar heights are means and the pass-to-pass SD is quoted in \u00a74.5 rather than drawn",
        "caption no longer claims error bars", BODY)

# L9 Note S1 states where the coding came from and what is still open
present("*Source of each coding.*", "Note S1 records the coding source", S)
present("Page-level anchors are deliberately not given",
        "Note S1 states the page-anchor limit", S)

print("=" * 74)
print("M.  the tenth round: technical wording and author-supplied metadata")
print("=" * 74)

# M1 metadata block
present("Hongbo Fu, Yijie Zeng, Jian Zhang", "author list filled", M)
present("School of Biomedical Engineering, Guangzhou Medical University", "affiliation filled", M)
present("**Corresponding author**: Jian Zhang", "corresponding author named", M)
present("Hongbo Fu: conceptualization, methodology, software", "CRediT for the first author", M)
present("Jian Zhang: writing \u2013 review and editing, visualization", "CRediT for the corresponding author", M)
present("**Competing interests.** The authors declare no competing interests.", "COI statement", M)
present("DeepSeek-V4.1-Flash", "AI tool named", M)
absent("[TODO \u2014 author list", "author placeholder gone", "Hongbo Fu")
_left = re.findall(r"\[TODO \u2014 [^\]\n]*", M)
_allowed = ("[TODO \u2014 corresponding e-mail",
            "[TODO \u2014 repository DOI",
            "[TODO \u2014 funding body")
check(all(tok.startswith(_allowed) for tok in _left),
      "only author-input placeholders remain", "e-mail / DOI / funding", _left or "none")
present("https://github.com/wavingman2016-lgtm/PAI-square-law-readout", "public repository URL in place", M)
check(re.search(r"commit `[0-9a-f]{8}`", M) is not None,
      "commit hash quoted with the archive tag", "8 hex digits", "none")
absent("[TODO \u2014 public repository URL", "repository URL placeholder gone", "https://github.com/")

# M2 wording changes
present("attenuates the dominant $2f_0$ component", "2.2 uses 'dominant component'", M)
absent("principal part of the $2f_0$", "2.2 'principal part' retired", "dominant", M)
present("makes the squared record approximate a squared envelope", "2.3 conditional conversion", M)
absent("The low-pass is what converts", "2.3 conversion sentence retired", "approximate a squared envelope", M)
present("the design does not isolate the contributions of squaring and filtering", "4.3 attribution bounded", M)
absent("the four incoherent chains tie", "4.4 'tie' retired", "not separated by the available", M)
present("not separated by the available $a_{50}$ precision", "4.4 precision wording", M)
present("the additional pointwise multiplication is negligible relative to", "4.5 arithmetic scope", M)
present("should not be interpreted as confidence intervals for a transferable false-alarm operating point",
        "3.5 interval caveat extended", M)
present("without implying equivalence", "7 no-equivalence qualifier", M)

# M3 the Highlights keep their symbols in the source and in the rendered draft
for tok in ("within 1.17% in all six datasets", "8\u201363%", "4:1 versus 1.00 mm", "in 5/6"):
    present(tok, "highlight token: %s" % tok, BODY)

print("=" * 74)
print("N.  the eleventh round: kernel, spreading models, valley model, cleanup")
print("=" * 74)

# N1 the kernel is unfiltered DAS, not UBP
present("no time-derivative or ramp filter", "2.1 declares the kernel unfiltered", M)
present("unfiltered delay-and-sum, not the universal back-projection", "2.1 names the difference", M)
present("unfiltered DAS; UBP with ramp filter", "Table 1 L1 separates the two", BODY)
present("**What a ramp filter would change.**", "5.2 discusses the filtered variant", M)

# N2 spherical versus cylindrical spreading
present("$d_m^{-1/2}$", "2.4 gives the cylindrical amplitude exponent", M)
present("intensity falls as $d_m^{-2}$", "2.4 gives the spherical intensity exponent", M)
present("robustness check across the two models", "Table S2 is read against both models", M)

# N3 the two-profile model
present("P_{EL}(x)\\approx r^2 f^2(x)+f^2(x-d)", "4.3 states the squared-profile model", M)
present("The squared read-out therefore fills the valley more than the envelope read-out",
        "4.3 states the criterion", M)
absent("as soon as the strong target's skirt at its neighbour exceeds $1/r$",
       "the peak-only criterion is retired", "as soon as that ratio exceeds one", M)

# N4 W5 and ROI
present("a ring of that diameter radiates predominantly", "6 gives the W5 acoustic picture", M)
present("applies to all five chains equally", "3.2 argues ROI independence", M)

# N5 threshold order statistics
present("36th to 40th order statistics", "3.5 states the distribution-free interval", M)
present("coverage 0.952", "Note S2 records the coverage", S)

# N6 submission cleanup
absent("**Formal reference list**", "the build note under References is gone", "doi:10.1016", BODY)
absent("Evaluated for inclusion and excluded", "the internal note on [51] is gone", "openreview.net", BODY)
present("limits quoted in Table 4", "Fig. 3 points at the right table", BODY)
absent("limits quoted in Table 3", "the stale table number is gone", "limits quoted in Table 4", BODY)

print("=" * 74)
print("O.  the twelfth round: EH-versus-M typo and the valley-position ratio")
print("=" * 74)

# O1 the in-vivo sentence names the chain whose image was compared
present("reproduces the squared envelope (*EH*) closely", "4.6 names EH as the reproduced chain", M)
absent("reproduces envelope stacking closely", "the mis-named chain is gone",
       "reproduces the squared envelope", M)
present("while its separability against envelope stacking (*M*) reverses",
        "the contrast is now stated against M explicitly", M)

# O2 the archived number is the EL-versus-EH correlation, not EL-versus-M
import csv as _csv
_rows = list(_csv.DictReader(io.open(os.path.join(ROOT, "results", "study_patato", "patato_summary.csv"),
                                     encoding="utf-8-sig")))
_v = {r["quantity"]: r["value"] for r in _rows if r["chain"] == "EL"}
check("pearson_vs_EH" in _v and abs(float(_v["pearson_vs_EH"]) - 0.9992) < 5e-4,
      "the archived Pearson is EL against EH", "0.9992",
      _v.get("pearson_vs_EH"))
check(not any(k.startswith("pearson_vs_M") for k in _v),
      "no EL-versus-M correlation exists in the archive", "absent",
      sorted(_v))

# O3 the valley-position ratio
present("r f(x_v)/f(x_v-d)", "4.3 gives the ratio at an intermediate valley point", M)
present("the criterion is easier to meet between the peaks", "4.3 states the consequence", M)
present("the reversal can appear at amplitude ratios for which $r\\epsilon$ is still below one",
        "4.3 reconciles the 2:1 case", M)

# O4 the supplement carries the same version tag as the manuscript
check(os.path.exists(SUPP) and "v0.48" in os.path.basename(SUPP),
      "supplement file name matches the draft version", "v0.48", os.path.basename(SUPP))
print()
print("-" * 74)
if bad:
    for b in bad:
        print("DEV   " + b)
print("checked %d items: OK %d / problems %d" % (ok + len(bad), ok, len(bad)))
print("VERDICT: %s" % ("PASS" if not bad else "FAIL"))
sys.exit(0 if not bad else 1)
