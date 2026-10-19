#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""v0.42 numeric probe: every new number of this round, recomputed from the
bootstrap archive rather than from the table that quotes it.

The round added a bootstrap interval, a per-chain interval envelope, a binomial
standard error and a Wilson column.  None of them existed when
``_probe_v033_numbers.py`` was written, so this file is the source check for
them, kept separate so the older probe keeps its 43-item baseline.

Rules (same three-way verdict as the older probe)
-------------------------------------------------
  OK      -- the quoted number equals the recomputed value rounded the same way
  DEV     -- rounding still differs (last digit, inverted bounds, wrong quantity)
  MISSING -- the quantity is not in the archive, so nothing can be checked

Usage: python paper/manuscript/_probe_v041_bootstrap.py
Exit code 0 iff no DEV and no MISSING.
"""
import csv
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
JSON = os.path.join(ROOT, "results", "study_detection_bootstrap.json")
CSV4 = os.path.join(ROOT, "paper", "tables", "TS4_detection_bootstrap.csv")
MOTHER = os.path.join(HERE, "00_manuscript_EN.md")
ASSEMBLED = os.path.join(HERE, "01_draft_v0.44_assembled.md")
SUPP = os.path.join(HERE, "03_supplementary_v0.44.md")

ROWS = []


def check(status, label, quoted, calc, note=""):
    ROWS.append((status, label, quoted, calc, note))


def r(x, nd):
    return "%.*f" % (nd, x)


def main():
    if not os.path.exists(JSON):
        print("MISSING archive: %s" % JSON)
        return 1
    d = json.load(io.open(JSON, encoding="utf-8"))
    arms = d["arms"]
    body = io.open(MOTHER, encoding="utf-8").read()
    ab = body[body.find("## Abstract"):body.find("## 1. Introduction")]
    draft = io.open(ASSEMBLED, encoding="utf-8").read() if os.path.exists(ASSEMBLED) else ""
    supp = io.open(SUPP, encoding="utf-8").read() if os.path.exists(SUPP) else ""

    # --- 1. bootstrap settings actually used -------------------------------
    check("OK" if d["B"] == 4000 else "DEV", "resamples B", "4000", d["B"])
    check("OK" if d["n_rep"] == 20 else "DEV", "trials per amplitude", "20", d["n_rep"])

    # The ladder quoted in 3.5 has fifteen amplitudes.  The three staged archives
    # now merge into exactly those fifteen, and the merge is only legal because
    # the overlapping amplitudes carry identical Pd (asserted inside the
    # analysis script, which refuses to merge a different draw).
    amp = [float(x) for x in d["amplitudes"]]
    check("OK" if len(amp) == 15 else "DEV", "merged amplitudes", "15", len(amp))
    check("OK" if r(amp[-1], 2) == "0.40" else "DEV",
          "merged upper amplitude", "0.40", r(amp[-1], 4))
    check("OK" if len(d["mat"]) == 3 else "DEV",
          "archives merged", "3", len(d["mat"]))
    quoted = body.split("a\\in\\{", 1)[1].split("\\}", 1)[0]
    quoted = quoted.replace("\\,", "").replace(" ", "")
    quoted = [float(x) for x in quoted.split(",")]
    check("OK" if len(quoted) == 15 else "DEV",
          "ladder amplitudes quoted in 3.5", "15", len(quoted))
    check("OK" if quoted == amp else "DEV",
          "merged ladder equals the ladder quoted in 3.5", "identical",
          "match=%s" % (quoted == amp))
    check("OK" if all(a["a50"] <= 0.005 for a in arms.values()) else "DEV",
          "every a50 at or below the last pre-ceiling amplitude", "a50 <= 0.005",
          r(max(a["a50"] for a in arms.values()), 6))
    # the withdrawn claim must be gone from every carrier, main text and supp
    stale = ["ten amplitudes from 0.0002 to 0.01", "only the ten amplitudes",
             "could not have entered the resampling"]
    for s_ in stale:
        n_hit = body.lower().count(s_) + supp.lower().count(s_) + draft.lower().count(s_)
        check("OK" if n_hit == 0 else "DEV",
              "withdrawn range claim absent: %s" % s_[:34], "0 hits", n_hit)

    # --- 2. EL-to-C ratio interval ----------------------------------------
    rc = d["ratio_EL_over_C"]
    lo, hi = rc["lo"], rc["hi"]
    check("OK" if r(lo, 2) == "1.96" else "DEV", "EL/C ratio CI low", "1.96", r(lo, 4))
    check("OK" if r(hi, 2) == "3.12" else "DEV", "EL/C ratio CI high", "3.12", r(hi, 4))
    check("OK" if round(rc["point"], 1) == 2.4 else "DEV",
          "EL/C point ratio", "2.4", r(rc["point"], 3))
    # v0.44 cut the abstract to two numbers, so the EL-to-C ratio interval left the
    # abstract by design.  The expectation moves with it: the interval must still be
    # quoted in 4.4, and it must no longer be in the abstract.
    check("OK" if ("ED_EL_C_95 = 1.96 to 3.12" in body or
                   "puts the EL-to-C ratio at 1.96 to 3.12" in body) else "DEV",
          "ratio interval quoted in section 4.4", "1.96 to 3.12", "present=%s" %
          ("puts the EL-to-C ratio at 1.96 to 3.12" in body))
    check("OK" if ("1.96 to 3.12" not in ab) else "DEV",
          "ratio interval no longer in the abstract", "0 hits",
          "count=%d" % ab.count("1.96 to 3.12"))
    check("OK" if ("bootstrap 95% interval" not in body) else "DEV",
          "abstract no longer prefixes the interval with 'bootstrap'", "0 hits",
          "count=%d" % body.count("bootstrap 95% interval"))
    check("OK" if ("1.96 to 3.12" in body) else "DEV",
          "ratio interval quoted in 4.4", "1.96 to 3.12",
          "count=%d" % body.count("1.96 to 3.12"))

    # --- 3. per-chain interval envelope -----------------------------------
    c = arms["C"]
    clo, chi = c["a50_boot_lo"], c["a50_boot_hi"]
    check("OK" if r(clo, 4) == "0.0014" else "DEV", "C a50 CI low", "0.0014", r(clo, 6))
    check("OK" if r(chi, 4) == "0.0022" else "DEV", "C a50 CI high", "0.0022", r(chi, 6))
    inc = [arms[k] for k in ("M", "EH", "EL", "SQ")]
    ilo = min(a["a50_boot_lo"] for a in inc)
    ihi = max(a["a50_boot_hi"] for a in inc)
    check("OK" if r(ilo, 4) == "0.0034" else "DEV",
          "incoherent envelope low", "0.0034", r(ilo, 6))
    check("OK" if r(ihi, 4) == "0.0049" else "DEV",
          "incoherent envelope high", "0.0049", r(ihi, 6))
    check("OK" if chi < ilo else "DEV",
          "C interval strictly below every incoherent interval",
          "C high < incoherent low", "%s < %s" % (r(chi, 6), r(ilo, 6)))

    # --- 4. no replicate censored -----------------------------------------
    cens = sum(a["censored"] for a in arms.values())
    check("OK" if cens == 0 else "DEV", "censored resamples (all arms)", "0", cens)

    # --- 5. binomial standard error ---------------------------------------
    n = d["n_rep"]
    se = 0.5 / (n ** 0.5)
    check("OK" if r(se, 2) == "0.11" else "DEV",
          "max binomial SE of Pd at 20 trials", "0.11", r(se, 4))

    # --- 6. bracket success-count span (Table S3 caption) -----------------
    spans = []
    for a in arms.values():
        b = a["bracket"]
        spans.append(abs(b[1]["hits"] - b[0]["hits"]))
    check("OK" if (min(spans), max(spans)) == (7, 11) else "DEV",
          "bracket success-count span", "7 to 11", "%d to %d" % (min(spans), max(spans)))
    check("OK" if ("7 to 11 successes" in supp) else "DEV",
          "span quoted in Table S3 caption", "7 to 11", "present=%s" %
          ("7 to 11 successes" in supp))

    # --- 7. Table S4 exists, is cited, and agrees with the archive --------
    check("OK" if ("Table S4" in body) else "DEV",
          "Table S4 cited in main text", ">=1 citation", body.count("Table S4"))
    check("OK" if ("Table S4" in supp) else "DEV",
          "Table S4 present in supplement", "1 block", supp.count("**Table S4.**"))
    check("OK" if len(arms) == 5 else "DEV", "chains in bootstrap", "5", len(arms))

    with io.open(CSV4, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    check("OK" if len(rows) == 5 else "DEV", "Table S4 rows", "5", len(rows))
    for row in rows:
        k = row["arm"]
        if k not in arms:
            check("MISSING", "Table S4 arm %s in archive" % k, k, "absent")
            continue
        want = r(arms[k]["a50"], 6)
        check("OK" if row["a50"] == want else "DEV",
              "Table S4 a50 %s" % k, want, row["a50"])
        wlo = r(arms[k]["a50_boot_lo"], 6)
        check("OK" if row["boot 2.5%"] == wlo else "DEV",
              "Table S4 CI low %s" % k, wlo, row["boot 2.5%"])

    # --- 8. Wilson column is a real interval, ordered and inside [0,1] ----
    for row in rows:
        txt = row["Wilson 95% at upper $a$"]
        try:
            a, b = [float(x) for x in txt.replace("\u2013", "-").split("-")]
        except ValueError:
            check("DEV", "Wilson parsed %s" % row["arm"], txt, "unparsable")
            continue
        ok = 0.0 <= a < b <= 1.0
        check("OK" if ok else "DEV", "Wilson ordered %s" % row["arm"],
              "0 <= lo < hi <= 1", txt)

    # --- 9. interpolation sensitivity moved to Note S2 in v0.44 ------------
    check("OK" if ("moves $a_{50}$ by at" in supp and "2.5%" in supp) else "DEV",
          "log-interpolation sensitivity, in Note S2", "2.5%", "present")
    check("OK" if ("0.5 to 0.6%" in supp) else "DEV",
          "log-interpolation sensitivity, incoherent, in Note S2", "0.5 to 0.6%", "present")
    check("OK" if ("moves $a_{50}$ by at most 2.5" not in body) else "DEV",
          "log-interpolation detail no longer in the main text", "0 hits",
          "count=%d" % body.count("moves $a_{50}$ by at most 2.5"))

    # --- 10. the retracted phrasings must be gone -------------------------
    gone = ["incoherent sum amplifies", "expected direction for a limited-view",
            "no confidence interval is attached"]
    for g in gone:
        hit = body.count(g) + draft.count(g) + supp.count(g)
        check("OK" if hit == 0 else "DEV", "retracted phrasing absent: %s" % g[:38],
              "0", hit)

    # --- report -----------------------------------------------------------
    w = max(len(x[1]) for x in ROWS) + 2
    print("%-5s %-*s %14s %14s" % ("", w, "item", "quoted", "recomputed"))
    print("-" * (w + 40))
    dev = miss = 0
    for st, label, quoted, calc in [(a, b, c, d_) for a, b, c, d_, *_ in ROWS]:
        if st == "DEV":
            dev += 1
        elif st == "MISSING":
            miss += 1
        print("%-5s %-*s %14s %14s" % (st, w, label, quoted, calc))
    print("-" * (w + 40))
    print("checked %d items: OK %d / DEV %d / MISSING %d"
          % (len(ROWS), len(ROWS) - dev - miss, dev, miss))
    print("VERDICT: %s" % ("PASS" if dev == 0 and miss == 0 else "FAIL"))
    return 0 if dev == 0 and miss == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
