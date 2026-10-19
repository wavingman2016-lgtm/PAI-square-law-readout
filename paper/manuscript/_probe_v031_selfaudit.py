# -*- coding: utf-8 -*-
"""v0.31 self-audit probe (review round 8, items 1-11 + the 8-item package).

What this round changed, and therefore what this probe guards
-------------------------------------------------------------
  (a) the auxiliary endpoint (Wasserstein W1) direction was INVERTED: a smaller
      distance means *closer* distributions, so the endpoint AGREES with gCNR in
      5/6 datasets; the old "more separable in 5/6" / "the two endpoints
      disagree in sign" sentences are withdrawn;
  (b) E4c is reported per configuration, not pooled: 3/6 exceed a pre-specified
      10% threshold and the sign reverses across f0, so the pooled n=30 summary
      is not a valid aggregate; "bounds folding" is withdrawn;
  (c) the W5 frequency chain is registered item by item (0.1875 / 0.406 / 1.25 /
      0.35 MHz) and the used value's provenance is disclosed as unrecoverable;
  (d) the W3 grid correction 601 -> 1000 (0.04 mm pitch claim kept);
  (e) "harmless here" is replaced by the Table S6 sensitivity analysis;
  (f) the background ring is audited (Table S7 / Fig. S4): real secondary
      structure in 5/6 datasets, no de-contamination variant yields an E
      advantage in a majority;
  (g) width evidence is stratified into three non-interchangeable layers;
  (h) scope narrowed: 6-8 dB is an input-output cost of the unsmoothed squaring
      step (full chain not measured), Fig. 5 is exploratory, the timing
      narrative is "attributes most of the measured difference to", the
      re-timing after removing arm C's redundant work is disclosed as not run;
  (i) FORMAT COMPLIANCE: the corrections above had pushed the abstract to 621
      words; it is compressed back to <=500 and two Highlights are back under
      85 characters;
  (j) the W3 grid correction reached the body of §3 but NOT its table carrier:
      TableS1_config_audit.csv still wrote "Nx raised 601 -> 1501" (ASCII arrow),
      so the reader-visible Table S1 kept shipping the withdrawn value while the
      prose was already correct.  Fixed at the source CSV (pa_cfg.m own128 has
      Nx = 1000 at FOV 40 mm; the W3_fov40 recheck grid is 1000), and both arrow
      glyphs are now scanned.

Two lessons that this probe itself has to embody, because both were learned by
being got wrong:

  * READER-VISIBLE CAPTIONS DO NOT LIVE IN THE MASTER BODY.  They are
    hard-coded in _assemble_draft.py and only appear in the assembled draft.
    A caption corrected in the master's appendix but not in the script still
    ships stale, and a master-body probe reports "0 residual" while the DOCX
    carries the withdrawn claim.  Caption checks therefore haystack on the
    assembled draft.
  * WHERE A HAYSTACK CARRIES THE CHANGELOG, IT QUOTES WHAT IT WITHDREW.  Two
    artifacts are audited and they differ.  The DOCX starts at '## Title'
    (`_build_docx.py`), so the status header and every changelog block are
    dropped and the journal file never sees them; residual hits there are zero
    by construction, and the artifact is additionally asserted free of the
    changelog outright.  The assembled draft, by contrast, still carries the
    front matter, and there the changelog names each retracted string next to
    its own withdrawal or correction marker -- so a bare substring count is a
    false alarm and a hit is a residual only when it stands alone (see
    `unexempt`).  The same exemption applies to the DOCX checks as a guard
    against the builder ever changing.

Probe iron rules honoured here:
  * every residual check is paired with a positive control, so "0 hits" cannot
    be confused with a dead detector;
  * the delivery interval is the master AFTER the caption appendix and the Open
    items list are excluded (they are author-side scaffolding, stripped by
    _assemble_draft.py before delivery);
  * the FINAL DOCX is audited as well, because it is the artifact a journal
    would receive.

Exit code 0 = PASS.  Any residual hit, dead control, missed caption control,
over-length abstract or over-long highlight = FAIL.
"""
import io
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MS = os.path.join(ROOT, "paper", "manuscript", "00_manuscript_EN.md")
AD = os.path.join(ROOT, "paper", "manuscript", "01_draft_v0.31_assembled.md")
T4 = os.path.join(ROOT, "paper", "tables", "Table04_datasets.csv")
T6 = os.path.join(ROOT, "paper", "tables", "TableS6_estimator_sensitivity.csv")
T7 = os.path.join(ROOT, "paper", "tables", "TableS7_ring_audit.csv")
DX = os.path.join(ROOT, "paper", "manuscript", "02_PAI_manuscript_v0.31_draft.docx")

for p in (MS, AD, T4, T6, T7, DX):
    if not os.path.exists(p):
        print("FATAL: missing %s" % p)
        sys.exit(2)

ms = io.open(MS, encoding="utf-8").read()
ad = io.open(AD, encoding="utf-8").read()
t4 = io.open(T4, encoding="utf-8-sig").read()
t6 = io.open(T6, encoding="utf-8-sig").read()
t7 = io.open(T7, encoding="utf-8-sig").read()

# ---- delivery interval: after the status header, before the author-side
# ---- caption appendix (both stripped by _assemble_draft.py).
body = ms[ms.index("## Title"):ms.index("## Figure captions (draft)")]
# reader-visible captions do NOT live in the master body: they are hard-coded
# in _assemble_draft.py and land in the assembled draft (AD).  Caption-level
# controls therefore haystack on AD, never on `body`.
body_w = re.sub(r"\s+", " ", body)      # line-break tolerant copy of `body`

z = zipfile.ZipFile(DX)
dx = re.sub(r"<[^>]+>", "", z.read("word/document.xml").decode("utf-8"))

fails = []

# ============================ residual checks ============================
# (tag, stale string, haystack)  -- every one of these was withdrawn in v0.31
RESID = [
    # (a) auxiliary-endpoint direction
    (u"old W1 claim: more separable in 5/6",  u"more separable in 5/6", body),
    (u"old W1 claim: endpoints disagree",     u"disagree in sign", body),
    (u"old W1 claim: two endpoints framing",  u"the two endpoints", body),
    (u"old W1 claim: distributions apart",    u"distributions are further apart", body),
    # (b) E4c pooling / folding bound
    (u"old E4c claim: bounds folding",        u"bounds folding", body),
    (u"old E4c claim: bounding it",           u"bounding it", body),
    (u"old E4c claim: 4 of the 4",            u"4 of the 4", body),
    # count 4/4 -> 4 of 6
    (u"old count 4/4 testable",               u"4/4 testable", body),
    (u"old count in **4/4**",                 u"in **4/4**", body),
    # bin count wording
    (u"old bin wording 65-bin",               u"65-bin", body),
    # (e) harmless-here
    (u"old scope limit: harmless",            u"harmless", body),
    # (g) resolution claims
    (u"old resolution claim: exactly the ... of", u"exactly the resolution of", body),
    (u"old attribution: broadening belongs to",   u"the broadening belongs to", body),
    # (h) SNR scoping
    (u"old unscoped SNR cost",                u"SNR cost at the detection step", body),
    # two-point criterion naming
    (u"old criterion: Rayleigh dip",          u"Rayleigh dip", body),
    # (d) W3 grid
    (u"old grid 601 -> 1501",                 u"raised 601", body),
    # Hilbert-free scoping
    (u"old abstract: with a Hilbert transform", u"with a Hilbert transform", body),
    (u"old estimator-is-Hilbert-free",        u"estimator below is", body),
    # timing narrative
    (u"old timing: locates the saving in",    u"locates the saving", body),
    (u"old timing: speed-up belongs to",      u"The speed-up belongs to", body),
    # Fig. 5 provenance
    (u"old Fig.5 status: Core evidence",      u"Core evidence", body),
    # metric hierarchy
    (u"old metric: only admissible",          u"only admissible", body),
    (u"old metric: only quantity compared",   u"gCNR is the only quantity", body),
    # W5 frequencies
    (u"old W5 peak 0.19 MHz",                 u"0.19 MHz", body),
    (u"old W5 centre 0.70 MHz",               u"0.70 MHz", body),
    # ---- carriers (table CSVs) ----
    (u"Table04 stale criterion label",        u"Rayleigh separability", t4),
    (u"TableS4 stale endpoint wording",       u"disagree", io.open(
        os.path.join(ROOT, "paper", "tables", "TableS4_common_domain_control.csv"),
        encoding="utf-8-sig").read()),
]

print(u"=== residual (must all be 0) ===")
n = 0
for tag, pat, hay in RESID:
    c = hay.count(pat)
    n += c
    print(u"  %-40s %d" % (tag, c))
    if c:
        fails.append(u"RESIDUAL " + tag)
print(u"  total = %d" % n)

# ============================ positive controls ==========================
CTRL = [
    (u"new count 4 of 6",              u"negative in **4 of 6** testable", body, 1),
    (u"new bin wording 65-edge",       u"65-edge (64-bin)", body, 1),
    (u"new W1 direction",              u"closer, not further apart", body, 1),
    (u"new W1 agreement 5/6",          u"agrees** with the gCNR reading", body, 1),
    (u"new criterion named",           u"5% valley-depth dip criterion", body, 1),
    (u"new Rayleigh disclaimer",       u"not a classical Rayleigh limit", body, 2),
    (u"new folding statement",         u"detected no upsampling-induced change", body, 2),
    (u"new folding not-error-bound",   u"**not** an error bound", body, 1),
    (u"new timing narrative",          u"attributes most of the measured difference to", body_w, 1),
    (u"new E6 disclosure",             u"no re-timing after removing arm", body_w, 1),
    (u"new Fig.5 status",              u"Exploratory evidence", ad, 1),
    (u"new metric hierarchy",          u"primary cross-arm metric", body, 1),
    (u"new grid 1000 -> 1501",         u"raised 1000 \u2192 1501", body, 1),
    (u"new abstract family phrasing",  u"analytic-signal (envelope-forming) family", body, 1),
    (u"new Hilbert-free scoping",      u"admits a Hilbert-free realization", body, 2),
    (u"new SNR scoping",               u"input\u2013output SNR", body, 2),
    (u"new width layers",              u"three layers that are not interchangeable", body, 1),
    (u"new W5 provenance disclosure",  u"cannot be recovered from the released archive", body, 1),
    (u"new ring disclosure 5/6",       u"real secondary structure in 5/6", body, 1),
    (u"new Table 9 status",            u"supported within the tested configurations", body, 1),
    (u"changelog records the format fix", u"compressed back to **", ms, 1),
    # carriers
    (u"Table04 new criterion label",   u"5% valley-depth dip criterion", t4, 1),
    (u"TableS6 pre-specified setting", u"pre-specified setting (65 edges = 64 bins)", t6, 1),
    (u"TableS6 KS knob",               u"binning-free two-sample KS statistic", t6, 6),
    (u"TableS7 de-contamination",      u"peak exclusion", t7, 6),
    (u"TableS7 clean-sector rules",    u"clean sectors, 40 deg rule", t7, 6),
]

print(u"\n=== positive controls ===")
for tag, pat, hay, lo in CTRL:
    c = hay.count(pat)
    ok = c >= lo
    print(u"  %-40s %d (min %d) %s" % (tag, c, lo, u"OK" if ok else u"MISS"))
    if not ok:
        fails.append(u"CONTROL-MISS " + tag)

# ============================ format compliance ==========================
# --- Highlights <= 85 characters (raw), per the master's own header note
print(u"\n=== Highlights (<= 85 chars) ===")
hl = ms[ms.index("**Highlights**"):ms.index("**Keywords**")]
for l in hl.split("\n"):
    t = l.strip().lstrip("- ").strip()
    if not t or t.startswith("**"):
        continue
    L = len(t)
    print(u"  %3d  %s" % (L, t[:60]))
    if L > 85:
        fails.append(u"HIGHLIGHT %d chars" % L)

# --- Abstract <= 500 words, convention A of _wordcount.py.
#     The count is NOT re-implemented here: a second tokenizer written for this
#     probe disagreed with the official one by one word on this very text.  A
#     manuscript that quotes a word count must quote the reproducible one, so
#     the official counter is the single source of truth.
sys.path.insert(0, os.path.dirname(MS))
import _wordcount as WC  # noqa: E402

n_a = WC.count(WC.strip_non_prose(WC.section(ms, "Abstract")), WC.TOK_A)
print(u"\n=== Abstract word count (convention A, _wordcount.py) ===")
print(u"  words = %d  (limit 500)" % n_a)
if n_a > 500:
    fails.append(u"ABSTRACT %d words" % n_a)

# the number the changelog quotes must be the number the script computes
_q = re.search(r"compressed back to \*\*(\d+)\*\*", ms)
if not _q:
    fails.append(u"CHANGELOG-WORDCOUNT-ABSENT")
else:
    _qn = int(_q.group(1))
    print(u"  changelog quotes %d -> %s" % (_qn, u"OK" if _qn == n_a else u"MISMATCH"))
    if _qn != n_a:
        fails.append(u"CHANGELOG-WORDCOUNT %d vs computed %d" % (_qn, n_a))

# ============================ delivery DOCX ==============================
print(u"\n=== delivery DOCX (the artifact) ===")
leak = sorted(set(re.findall(r"(?:docs|notes|pipeline|results|data_ext|oadat_data)/[A-Za-z0-9_\-/\.]+", dx)))
cjk = len(re.findall(r"[\u4e00-\u9fff]", dx))
oi = "Open items" in dx
# _build_docx.py starts at '## Title', so no author-side block may reach the
# journal file.  That is asserted here rather than assumed: if the builder ever
# changes, this fails instead of silently shipping drafting notes.
ASIDE = [m for m in (u"**changelog**", u"second carriers closed", u"Open items",
                     u"**Open items", u"review round") if m in dx]
print(u"  path leaks = %d %s" % (len(leak), leak if leak else u""))
print(u"  CJK chars  = %d" % cjk)
print(u"  author-side blocks = %s" % (ASIDE if ASIDE else u"none"))
for cond, tag in ((leak, u"DOCX-LEAK"), (cjk, u"DOCX-CJK"),
                  (ASIDE, u"DOCX-AUTHORSIDE")):
    if cond:
        fails.append(tag)


def unexempt(hay, pat, ctx, win=300):
    """Hits of `pat` in `hay` NOT within +-win characters of any `ctx` marker.

    The delivery artifact carries this round's changelog in its front matter,
    and the changelog *quotes* the exact strings this round withdrew -- always
    next to its own withdrawal or correction marker ("corrected in v0.31",
    "inverted and are withdrawn", "the previous ... statements",
    "downgraded from", "corrected").  A bare substring count therefore reports
    a false residual on an artifact that is in fact correct; a hit is a
    residual only when it stands on its own.  `ctx` may be a string, a tuple of
    alternative markers, or None ("no exemption is allowed at all").
    """
    ctxs = () if ctx is None else ((ctx,) if isinstance(ctx, str) else tuple(ctx))
    out = []
    for m in re.finditer(re.escape(pat), hay):
        lo, hi = max(0, m.start() - win), min(len(hay), m.end() + win)
        if any(c in hay[lo:hi] for c in ctxs):
            continue
        out.append(m.start())
    return out


# A withdrawn string quoted by the changelog is exempt next to one of these
# markers, each of them a specific withdrawal sentence -- deliberately NOT the
# bare word "withdrawn", which is loose enough to exempt a real residual.
WITHDRAW = (u"corrected in v0.31", u"inverted and are withdrawn")

# A withdrawn string is quoted TWICE in the delivery artifact: once by the
# changelog entry that withdrew it, and once by entry (j), which records that
# the reader-visible carrier finally caught up.  Both quotes are legitimate --
# a third, unannotated occurrence is a real residual.
CAPFIX = (u"they are now synced",)


# (tag, stale pattern, exemption context)
dx_resid = [
    (u"DOCX old count 4/4",       u"4/4 testable",          (u"corrected in v0.31",) + CAPFIX),
    (u"DOCX old bin wording",     u"65-bin",                None),
    (u"DOCX stale criterion",     u"Rayleigh separability", None),
    (u"DOCX old W1 claim",        u"disagree in sign",      WITHDRAW + CAPFIX),
    (u"DOCX old folding bound",   u"bounds folding",        None),
    (u"DOCX old Core evidence",   u"Core evidence",         (u"downgraded from",) + CAPFIX),
    (u"DOCX old grid 601",        u"raised 601",            u"corrected"),
    (u"DOCX old grid 601 arrow",  u"601 \u2192 1501",       u"corrected"),
]
for tag, pat, ctx in dx_resid:
    h = unexempt(dx, pat, ctx)
    print(u"  %-28s %d  (exempt %d)" % (tag, len(h), dx.count(pat) - len(h)))
    if h:
        fails.append(tag)

# ================== reader-visible captions (assembled draft) =============
# The reader-visible figure/table captions are HARD-CODED in _assemble_draft.py.
# The master's caption appendix is stripped before delivery, so the assembled
# draft is the only carrier that can prove what a reader actually sees -- a
# caption updated in the master but not in the script still ships stale.
print(u"\n=== reader-visible captions (assembled draft) ===")
CAP_STALE = [
    (u"caption old Core evidence",  u"Core evidence",    (u"downgraded from",) + CAPFIX),
    (u"caption old count 4/4",      u"4/4 testable",     (u"corrected in v0.31",) + CAPFIX),
    (u"caption old W1 claim",       u"disagree in sign", WITHDRAW + CAPFIX),
    (u"caption old grid 601",       u"raised 601",       u"corrected"),
    (u"caption old grid 601 arrow", u"601 \u2192 1501",  u"corrected"),
    # the round changelog quotes the withdrawn ASCII carrier string in order to
    # record the fix, so that one occurrence is exempt -- but only next to the
    # sentence that records it.
    (u"caption Table S1 grid 601",  u"601 -> 1501",
     (u"after (d) had corrected", u"second carriers closed")),
]
for tag, pat, ctx in CAP_STALE:
    h = unexempt(ad, pat, ctx)
    print(u"  %-30s %d  (exempt %d)" % (tag, len(h), ad.count(pat) - len(h)))
    if h:
        fails.append(tag)
CAP_CTRL = [
    (u"caption new Fig.5 status",      u"Exploratory evidence",            1),
    (u"caption new Table 6 no Plan B", u"not transferred",                 1),
    (u"caption new Table S6 zero-note", u"Rows with a zero entry",         1),
    (u"caption new Table S7 four",     u"four de-contamination variants",  1),
    (u"caption Table S1 grid 1000",    u"1000 -> 1501",                    1),
    # the intermediate is the opposite of the DOCX: it DOES keep the front
    # matter, which is exactly why its stale-string hits need exemption rules.
    (u"assembled draft keeps changelog", u"second carriers closed",         1),
]
for tag, pat, lo in CAP_CTRL:
    c = ad.count(pat)
    print(u"  %-30s %d (min %d) %s" % (tag, c, lo, u"OK" if c >= lo else u"MISS"))
    if c < lo:
        fails.append(u"CAPTION-CONTROL-MISS " + tag)

# ============================ markdown hygiene ===========================
print(u"\n=== $ pairing (delivery interval) ===")
odd = sum(1 for l in body.split("\n")
          if (len(l) - len(l.replace("$", "")) - 2 * l.count("$$")) % 2)
print(u"  odd lines = %d" % odd)
if odd:
    fails.append(u"DOLLAR-ODD %d" % odd)

print(u"\n=== markdown table column counts ===")
bad = 0
for b in re.findall(r"(?:^\|.*\n)+", body, re.M):
    ls = [l for l in b.strip().split("\n") if l.strip()]
    cols = [len(l.split("|")) - 2 for l in ls]
    if len(set(cols)) > 1:
        bad += 1
        print(u"  MISMATCH %s" % cols)
print(u"  mismatched blocks = %d" % bad)
if bad:
    fails.append(u"TABLE-COLS %d" % bad)

print(u"\n=== VERDICT: %s ===" % (u"FAIL" if fails else u"PASS"))
for f in fails:
    print(u"  " + f)
sys.exit(1 if fails else 0)
