"""Candidate retrieval for the v0.43 reference expansion.

Prints, for each bibliographic query, the top Crossref hits with DOI, title,
container and year, so that a reference can be selected *and* verified before
it is cited.  This is a search helper, not a verifier: `_refcheck_v043.py`
re-checks every DOI it finally emits.
"""
import io
import json
import sys
import urllib.parse
import urllib.request

UA = "PAI-reference-search/1.0 (mailto:noreply@example.org)"

QUERIES = [
    ("hollman_cf", "coherence factor of speckle from a multi-row probe"),
    ("dahl_slsc", "lesion detectability short-lag spatial coherence imaging"),
    ("camacho_pcf", "phase coherence imaging Camacho Parrilla Fritsch"),
    ("kay_det", "Fundamentals of Statistical Signal Processing Detection Theory Kay"),
    ("pierce_ac", "Acoustics An Introduction to Its Physical Principles and Applications Pierce"),
    ("szabo_us", "Diagnostic Ultrasound Imaging Inside Out Szabo"),
    ("pa_env", "photoacoustic imaging Hilbert transform envelope detection reconstruction"),
    ("pa_env2", "optoacoustic tomography analytic signal envelope reconstruction"),
    ("pa_sq", "square law detection optoacoustic signal"),
    ("pa_power", "power domain photoacoustic imaging intensity reconstruction"),
    ("pa_review_recent", "photoacoustic imaging reconstruction review 2024"),
    ("task_based", "task-based assessment image quality ultrasound resolution"),
    ("pa_dmas", "delay multiply and sum beamforming photoacoustic imaging"),
    ("pa_pact_review", "photoacoustic computed tomography image reconstruction review"),
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    out = {}
    for key, q in QUERIES:
        url = ("https://api.crossref.org/works?rows=6&select=DOI,title,container-title,issued,author,type"
               "&query.bibliographic=" + urllib.parse.quote(q))
        try:
            d = get(url)
        except Exception as e:  # network is best-effort here
            print("!! %s: %s" % (key, e))
            continue
        items = d["message"]["items"]
        out[key] = items
        print("\n=== %s | %s" % (key, q))
        for it in items:
            title = (it.get("title") or ["?"])[0]
            cont = (it.get("container-title") or ["-"])[0]
            yr = (it.get("issued", {}).get("date-parts") or [[None]])[0][0]
            auth = it.get("author") or []
            a0 = (auth[0].get("family", "?")) if auth else "?"
            print("  %-28s %s  %s | %s | %s" % (it["DOI"], yr, a0, title[:90], cont[:40]))
    with io.open("_ref_candidates.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\nwrote _ref_candidates.json")


if __name__ == "__main__":
    sys.exit(main())
