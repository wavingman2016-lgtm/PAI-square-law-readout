# -*- coding: utf-8 -*-
"""v0.42 probe: novelty repositioning, Table 1 recoding, over-strong claims.

Two kinds of check, both executed rather than asserted in prose:

  A. presence/absence of exact strings across the three carriers
     (mother manuscript, assembled draft, supplementary);
  B. recomputation of every ratio the review asked to be audited
     ("5/6", "3/3", "1.17%", "8-63%", plus the 1.9-7.3 width ratio that the
     audit turned up) directly from paper/tables/*.csv.

Every absence check carries a live positive control, so a typo in the haystack
cannot pass as a clean result.
"""
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TBL = os.path.join(ROOT, "paper", "tables")

MOTHER = os.path.join(HERE, "00_manuscript_EN.md")
DRAFT = os.path.join(HERE, "01_draft_v0.42_assembled.md")
SUPP = os.path.join(HERE, "03_supplementary_v0.42.md")

ok = 0
bad = []


def check(flag, label, want, got):
    global ok
    if flag:
        ok += 1
    else:
        bad.append("%-52s want=%-22s got=%s" % (label, want, got))


def load(p):
    if not os.path.exists(p):
        bad.append("missing carrier: %s" % p)
        return ""
    return io.open(p, encoding="utf-8").read()


M, D, S = load(MOTHER), load(DRAFT), load(SUPP)
ALL = M + "\n" + D + "\n" + S


def rows(name):
    with io.open(os.path.join(TBL, name), encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def absence(token, label, where=ALL):
    """Absence check with a live control: the control must be present."""
    n = where.count(token)
    check(n == 0, label, "0 hits", n)


print("=" * 74)
print("A.  novelty wording")
print("=" * 74)

for frag, label in [
        ("we did not identify a photoacoustic study that explicitly isolated a",
         "1.3 bounded prior-art paragraph present (Crossref, to 18 Oct 2026)"),
        ("it is not a claim that square-law processing is new",
         "1.3 explicit novelty boundary"),
        ("Square-law processing and related non-linear operations are established "
         "in adjacent fields",
         "1.3 early concession in gap sentence"),
        ("the contribution is not the invention of the square-law operation",
         "1.5 contribution reworded"),
        ("the geometric compensation paired with that placement under the adopted spreading model",
         "1.5 four-part contribution"),
        ("does not propose square-law detection as a new reconstruction principle",
         "1.4 positioning sentence"),
        ("- Five PAI read-out chains separate squaring",
         "Highlights item 1"),
]:
    check(frag in M, label, "present", "absent")

# positive control for the absence checks below: this phrase must exist
check("The gap is operational rather than nominal." in M,
      "control: gap sentence still present", "present",
      "absent (absence checks would be dead)")
# v0.45: the novelty defence leaves the abstract but stays in 1.3/1.5
absence("The subject is where the square is applied and how the result is weighted",
        "abstract novelty clause retired")
check("The claim made here therefore concerns the operational placement" in M,
      "novelty boundary still stated in 1.3", "present", "absent")
# the wording that the abstract novelty expectation replaced must not return unnoticed
absence("What is studied is where the square is applied",
        "retired abstract novelty wording gone")

print("=" * 74)
print("B.  over-strong claims withdrawn")
print("=" * 74)

absence("quadratic in absorption", "B1 'quadratic in absorption' gone")
check("quadratic in the reconstructed pressure-related amplitude" in M,
      "B1 replacement wording present", "present",
      "absent")
absence("stands in place of", "B2 'stands in place of' gone")
check("power-like in the algebraic sense" in M,
      "B2 algebraic statement present", "present", "absent")
absence("at unchanged spatial frequency content", "B3a unchanged SFG gone")
absence("at fixed spatial frequency content", "B3b fixed SFG gone")
absence("while its spatial frequency content is unchanged", "B3c SFG-unchanged gone")
check("does not by itself demonstrate new spatial-frequency information" in M,
      "B3 replacement wording present", "present", "absent")
absence("coded no,", "B4 'coded no' gone")
# the pressure-related law must not be silently dropped from 2.3
check("not a calibrated law of the optical absorption coefficient" in M,
      "B5 non-calibration caveat in 2.3", "present", "absent")

print("=" * 74)
print("C.  Table 1 recoding")
print("=" * 74)

tl = rows("TL_literature.csv")
cols = list(tl[0].keys())
coded = [c for c in cols if c not in ("id", "method family", "representative work",
                                      "evidence type", "ref.")]
vocab = set()
for r in tl:
    for c in coded:
        vocab.add(r[c].strip())
check(vocab == {"yes", "NR", "n.a."}, "C1 cell vocabulary is {yes, NR, n.a.}",
      "{'yes','NR','n.a.'}", sorted(vocab))
n_no = sum(1 for r in tl for c in coded if r[c].strip() == "no")
check(n_no == 0, "C2 no bare 'no' cell", "0", n_no)
n_nr = sum(1 for r in tl for c in coded if r[c].strip() == "NR")
check(n_nr == 23, "C3 NR cell count", "23", n_nr)
check(len(tl) == 9, "C4 nine rows", "9", len(tl))

check("Nearest-neighbour comparison of operation placement and aggregation" in D,
      "C5 Table 1 title reworded", "present", "absent")
check("**NR** \u2014 the operation is not explicitly reported" in D,
      "C6 caption defines NR", "present", "absent")
check("no cell in this table asserts a confirmed " in D,
      "C7 caption denies confirmed absence", "present", "absent")
check("only a " in D and "bounded claim about the operational placement" in D,
      "C8 caption carries the bounded claim", "present", "absent")
check("not a claim that square-law processing is new" in M,
      "C8b 1.3 carries the bounded claim", "present", "absent")
absence("**no** \u2014 the operation is not reported for that record",
        "C9 old caption legend gone", D)

print("=" * 74)
print("D.  denominators recomputed from the CSVs")
print("=" * 74)

t5 = rows("T5_detection.csv")
t4 = rows("T4_morphology.csv")
t1 = rows("TS1_equivalence.csv")


def num(x):
    x = x.strip().replace("\u2212", "-")
    try:
        return float(x)
    except ValueError:
        return None


n_ds = len(t5)
check(n_ds == 6, "D0 six datasets", "6", n_ds)

# D1 EL exceeds C in gCNR in 5/6, by up to 0.1881
elc = [num(r["EL-C"]) for r in t5]
pos = [v for v in elc if v is not None and v > 0]
neg = [v for v in elc if v is not None and v < 0]
check(len(pos) == 5 and len(neg) == 1, "D1a EL>C in 5 of 6", "5 pos / 1 neg",
      "%d pos / %d neg" % (len(pos), len(neg)))
check(abs(max(pos) - 0.1881) < 5e-5, "D1b max EL-C = 0.1881", "0.1881",
      "%.4f" % max(pos))
check("5/6 datasets" in D, "D1c draft says 5/6", "present", "absent")

# D2 EL vs M: 3 testable, all negative, range -0.0171 .. -0.0095
elm = [(r["dataset"], num(r["EL-M"])) for r in t5]
test = [v for _, v in elm if v is not None]
sat = [d for d, v in elm if v is None]
check(len(test) == 3 and len(sat) == 3, "D2a 3 testable / 3 saturated", "3 / 3",
      "%d / %d" % (len(test), len(sat)))
check(all(v < 0 for v in test), "D2b all testable EL-M negative", "3 negatives",
      sum(1 for v in test if v < 0))
check(abs(min(test) + 0.0171) < 5e-5 and abs(max(test) + 0.0095) < 5e-5,
      "D2c EL-M range -0.0171..-0.0095", "-0.0171 / -0.0095",
      "%.4f / %.4f" % (min(test), max(test)))

# D3 EL vs SQ: higher in 3, untestable in 2, lower by 0.0071 in 1
elsq = [num(r["EL-SQ"]) for r in t5]
hi = [v for v in elsq if v is not None and v > 0]
lo = [v for v in elsq if v is not None and v < 0]
na = [v for v in elsq if v is None]
check(len(hi) == 3 and len(na) == 2 and len(lo) == 1,
      "D3a EL-SQ 3 higher / 2 NA / 1 lower", "3 / 2 / 1",
      "%d / %d / %d" % (len(hi), len(na), len(lo)))
check(abs(lo[0] + 0.0071) < 5e-5, "D3b the lower one is -0.0071", "-0.0071",
      "%.4f" % lo[0])

# D4 1.17% = max normalized EL-EH difference
d = {r["dataset"]: num(r["max |EL-EH| / max EH"]) for r in t1}
check(abs(max(d.values()) - 0.0117) < 5e-7, "D4a max EL-EH diff = 0.0117",
      "0.0117", max(d.values()))
pear = min(num(r["Pearson"]) for r in t1)
check(pear >= 0.99998, "D4b min Pearson >= 0.99998", ">= 0.99998", pear)

# D5 EL/M narrowing 8-63% (lateral FWHM)
lat = {r["dataset"]: r for r in t4 if r["metric"] == "lateral FWHM (mm)"}
ratio = {k: num(v["EL"]) / num(v["M"]) for k, v in lat.items()}
nar = sorted((1 - v) * 100 for v in ratio.values())
check(abs(min(nar) - 8) < 0.6 and abs(max(nar) - 63) < 0.6,
      "D5a narrowing 8-63%", "8 .. 63", "%.1f .. %.1f" % (min(nar), max(nar)))
check("8% to 63%" in D, "D5b draft says 8% to 63%", "present", "absent")

# D6 EL/C width ratio: 1.9-7.3 on five datasets, W3 the exception
cr = {k: num(v["EL"]) / num(v["C"]) for k, v in lat.items()}
exc = [k for k, v in cr.items() if v < 1]
rest = [v for k, v in cr.items() if v >= 1]
check(exc == ["W3"], "D6a the C-narrower exception is W3", "['W3']", exc)
check(round(min(rest), 1) == 1.9 and round(max(rest), 1) == 7.3,
      "D6b EL/C range 1.9 .. 7.3", "1.9 / 7.3",
      "%.1f / %.1f" % (min(rest), max(rest)))
check(len(rest) == 5, "D6c five datasets", "5", len(rest))
check("1.9 to 7.3 times wider than *C* on five of six" in D,
      "D6d draft carries the five-of-six qualifier", "present",
      "MISSING \u2014 denominator defect")

# D7 peak side-lobe ratio lower for EL than M in 5 of 6
psl = {r["dataset"]: r for r in t4 if r["metric"] == "lateral PSLR (dB)"}
better = [k for k, v in psl.items() if num(v["EL"]) < num(v["M"])]
check(len(better) == 5, "D7 PSLR EL better in 5 of 6", "5", len(better))

# D8 two-point criterion: M 1.00 mm, EL/EH 1.50 mm at 4:1
check("1.00 mm" in M and "1.50 mm" in M, "D8 two-point values present (4:1)",
      "present", "absent")

print("=" * 74)
print("E.  supplementary Note S1")
print("=" * 74)

for frag, label in [
        ("**Note S1. Search protocol behind the nearest-neighbour comparison", "E1 note present"),
        ("up to 18 October 2026", "E2 date"),
        ('"square-law"', "E3 query family square-law"),
        ('"p-th root"', "E4 query family p-th root"),
        ("*Inclusion criteria.*", "E5 inclusion criteria"),
        ("*Exclusion criteria.*", "E6 exclusion criteria"),
        ("*Not done.*", "E7 explicit not-done list"),
        ("six records", "E8 evidence base count"),
]:
    check(frag in S, label, "present", "absent")
check(S.count('"') >= 16, "E9 eight query families quoted", ">=16 quotes",
      S.count('"'))
check("Note S1 states the query strings" in M,
      "E10 main text points at Note S1", "present", "absent")

print()
print("=" * 74)
print("checked %d items: OK %d / problems %d" % (ok + len(bad), ok, len(bad)))
for b in bad:
    print("  DEV", b)
print("VERDICT:", "PASS" if not bad else "FAIL")
sys.exit(0 if not bad else 1)
