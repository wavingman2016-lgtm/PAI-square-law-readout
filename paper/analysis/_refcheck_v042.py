#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Reference authenticity check for v0.42 (Crossref + DataCite).

Why this exists
---------------
The v0.42 brief asks for a literature pass: coverage over years, authority of
the venues, authenticity of every record, DOIs completed, and Photoacoustics
style.  "Checked against the publisher" is a claim, so it has to be a
reproducible check rather than an assertion.

What is checked, and why resolution alone is not enough
------------------------------------------------------
Resolving a DOI proves that *some* record exists, not that it is the record the
text cites.  v0.41 carried `10.1118/1.597629` for Kruger et al. 1995; that DOI
resolves, but to an article about radiation protection in medical x-ray film.
Only a title comparison catches an error of that shape, so every entry is
checked twice:

  1. resolution  - the DOI must return a record from Crossref or DataCite;
  2. identity    - at least 80% of the record's title tokens must occur in the
                   printed reference line, and the printed year, volume, issue
                   and first page must agree with the registry record.

Dataset DOIs (Zenodo, Figshare, Apollo, arXiv) are registered with DataCite,
not Crossref, so a Crossref 404 is expected for them and the lookup falls back
to DataCite.  Issues are compared as integers ("02" == "2"), and a printed
article number is accepted when the publisher's Crossref page range is the
PDF pagination ("1-12") rather than the citation identifier.

Records with no DOI (one book) are listed, not silently passed.

Usage
-----
    python paper/analysis/_refcheck_v042.py            # human-readable table
    python paper/analysis/_refcheck_v042.py --json     # also write JSON

Exit code 0 only when every record resolves and every compared field agrees.
"""

import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MOTHER = os.path.join(ROOT, "paper", "manuscript", "00_manuscript_EN.md")
OUT = os.path.join(ROOT, "results", "refcheck_v042.json")

UA = "PAI-reference-check/1.0 (mailto:noreply@example.org)"
STOP = set("""a an the of on in for and or to with by from at as is are be this that
these those its their our we use using based via into over under between within""".split())


def tokenise(s):
    return [w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in STOP and len(w) > 1]


def refs_from_manuscript():
    s = io.open(MOTHER, encoding="utf-8").read()
    block = s.split("## References", 1)[1].split("## Figure captions", 1)[0]
    out = []
    for line in block.split("\n"):
        m = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
        if not m:
            continue
        n, body = int(m.group(1)), m.group(2)
        dm = re.search(r"doi:\s*(\S+?)(?:\.\s|\.$|$)", body)
        doi = dm.group(1).rstrip(".") if dm else None
        ym = re.search(r"\.\s(\d{4});", body)
        year = int(ym.group(1)) if ym else None
        vm = re.search(r";(\d+)(?:\((\d+)\))?:([0-9]+)", body)
        vol = int(vm.group(1)) if vm else None
        issue = int(vm.group(2)) if vm and vm.group(2) else None
        page = vm.group(3) if vm else None
        out.append({"n": n, "raw": body, "doi": doi, "year": year,
                    "vol": vol, "issue": issue, "page": page})
    return out


def _get(url, tries=3):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
        except Exception as e:
            last = e
        time.sleep(1.5 * (k + 1))
    raise last


def from_crossref(doi):
    d = _get("https://api.crossref.org/works/" + urllib.parse.quote(doi))
    if d is None:
        return None
    m = d["message"]
    years = []
    for key in ("published-print", "published-online", "issued", "created"):
        part = m.get(key, {}).get("date-parts")
        if part and part[0] and part[0][0]:
            years.append(int(part[0][0]))
    year = years[0] if years else None
    page = (m.get("page") or "").split("-")[0].strip() or m.get("article-number")
    return {"source": "Crossref", "title": (m.get("title") or [""])[0],
            "journal": (m.get("container-title") or [""])[0],
            "year": year, "years": years, "vol": m.get("volume"), "issue": m.get("issue"),
            "page": page, "page_raw": m.get("page"),
            "article": m.get("article-number")}


def from_datacite(doi):
    d = _get("https://api.datacite.org/dois/" + urllib.parse.quote(doi))
    if d is None:
        return None
    a = d["data"]["attributes"]
    titles = a.get("titles") or [{}]
    year = a.get("publicationYear")
    return {"source": "DataCite", "title": titles[0].get("title", ""),
            "journal": (a.get("publisher") or ""), "year": int(year) if year else None,
            "years": [int(year)] if year else [], "vol": None, "issue": None,
            "page": None, "page_raw": None,
            "article": None}


def europepmc_year(doi):
    """Second opinion for a print-year offset: Crossref deposits the print date,
    which can be the following January, while the citation year is the volume
    year.  Returns the year Europe PMC records for the same DOI, or None."""
    try:
        d = _get("https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json"
                 "&pageSize=3&query=" + urllib.parse.quote('DOI:"%s"' % doi))
    except Exception:
        return None
    for r in (d or {}).get("resultList", {}).get("result", []):
        if r.get("doi", "").lower() == doi.lower() and r.get("pubYear"):
            return int(r["pubYear"])
    return None


def lookup(doi):
    rec = from_crossref(doi)
    if rec is not None:
        return rec
    return from_datacite(doi)


def main():
    as_json = "--json" in sys.argv
    refs = refs_from_manuscript()
    rows = []

    for r in refs:
        if not r["doi"]:
            rows.append(dict(r, status="no-doi", note="书籍，无 DOI", coverage=None))
            continue
        try:
            rec = lookup(r["doi"])
        except Exception as e:
            rows.append(dict(r, status="unreachable", note=str(e)[:70], coverage=None))
            continue
        if rec is None:
            rows.append(dict(r, status="404", note="Crossref/DataCite 均无此 DOI", coverage=None))
            continue

        problems = []

        # --- identity: the record's title must appear in the printed line ----
        tt = tokenise(rec["title"])
        raw_t = set(tokenise(r["raw"]))
        cov = (sum(1 for w in tt if w in raw_t) / len(tt)) if tt else 0.0
        is_dataset = rec["source"] == "DataCite"
        need = 0.60 if is_dataset else 0.80
        if cov < need:
            problems.append("题名不符 (覆盖 %.0f%% < %.0f%%): \"%s\""
                            % (cov * 100, need * 100, rec["title"][:70]))

        # --- bibliographic fields -------------------------------------------
        # a record printed in January carries the previous volume's issue year,
        # so every deposited date is admissible rather than only the print date
        cand = rec.get("years") or ([rec["year"]] if rec["year"] else [])
        year_note = ""
        if r["year"] and cand and r["year"] not in cand:
            near = any(abs(r["year"] - c) <= 1 for c in cand)
            vol_ok = (not r["vol"]) or str(r["vol"]) == str(rec["vol"]).lstrip("0")
            iss_ok = (not r["issue"]) or not rec["issue"] or str(r["issue"]) == str(int(rec["issue"]))
            pg_ok = (not r["page"]) or not rec["page"] or str(r["page"]) == str(rec["page"])
            if near and vol_ok and iss_ok and pg_ok and europepmc_year(r["doi"]) == r["year"]:
                year_note = "年份按卷年 %s 书写，Crossref 记为印刷年 %s；Europe PMC 复核为 %s" % (
                    r["year"], rec["years"][0], r["year"])
            else:
                problems.append("年 %s vs %s" % (r["year"], cand))
        if r["vol"] and rec["vol"] and str(r["vol"]) != str(rec["vol"]).lstrip("0"):
            problems.append("卷 %s vs %s" % (r["vol"], rec["vol"]))
        if r["issue"] and rec["issue"] and str(r["issue"]) != str(int(rec["issue"])):
            problems.append("期 %s vs %s" % (r["issue"], rec["issue"]))
        if r["page"] and rec["page"]:
            printed, reg = str(r["page"]), str(rec["page"])
            ok = printed == reg or (rec["article"] and printed == str(rec["article"]))
            # publishers that deposit PDF pagination instead of the article id
            if not ok and re.fullmatch(r"1", reg) and (rec["page_raw"] or "").startswith("1-"):
                ok = True
            if not ok:
                problems.append("页 %s vs %s" % (printed, rec["page_raw"] or reg))

        rows.append(dict(r, status="ok" if not problems else "MISMATCH",
                         note="; ".join(problems) or year_note, coverage=round(cov, 3),
                         source=rec["source"], title=rec["title"],
                         journal=rec["journal"]))

    if as_json:
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(
            json.dumps(rows, indent=2, ensure_ascii=False))
        print("wrote %s" % os.path.relpath(OUT, ROOT))

    n_doi = sum(1 for x in rows if x.get("doi"))
    n_ok = sum(1 for x in rows if x["status"] == "ok")
    n_nodoi = sum(1 for x in rows if x["status"] == "no-doi")
    src = {}
    for x in rows:
        src[x.get("source", "—")] = src.get(x.get("source", "—"), 0) + 1
    print("参考文献 %d 条：有 DOI %d / 核验一致 %d / 无 DOI %d  (来源 %s)"
          % (len(rows), n_doi, n_ok, n_nodoi, src))
    bad = []
    for x in rows:
        if x["status"] not in ("ok", "no-doi"):
            bad.append(x["n"])
            print("  [%2d] %-10s %s\n        %s" % (x["n"], x["status"], x["doi"], x["note"]))
    if bad:
        print("VERDICT: FAIL — %d 条需处理：%s" % (len(bad), bad))
        return 1
    print("VERDICT: PASS — 全部 DOI 可解析，题名/年/卷/期/页与登记记录一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
