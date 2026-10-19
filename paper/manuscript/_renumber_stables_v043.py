#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Renumber the supplementary tables into order of first citation.

Why
---
Elsevier (and this project's own convention for Tables 1-7) numbers tables in
the order in which the text first cites them.  v0.43 adds two supporting tables
that are cited *earlier* than four of the existing ones -- the contrast-isolation
table in section 1.4 and the weight-sensitivity table in the Table 2 caption --
so the old S1..S6 labels now run 6, 5, 3, 4, 1, 2 through the text.

The fix is a permutation, not a shift, and four of the six labels sit on a cycle
(1->5->2->6->1).  A single pass of naive substitutions therefore corrupts the
text, so every replacement goes through a unique sentinel first.

    old S1 (equivalence)        -> S5    cited in section 4.1
    old S2 (dense dip curves)   -> S6    cited in the Table 4 caption
    old S3 (threshold brackets) -> S3    cited in section 3.5   (fixed point)
    old S4 (bootstrap)          -> S4    cited in section 3.5   (fixed point)
    old S5 (weight sensitivity) -> S2    cited in the Table 2 caption
    old S6 (contrast isolation) -> S1    cited in section 1.4

After the permutation the six `TABLES` entries in ``_assemble_supp_v033.py`` are
re-sorted by display number, so the supplement itself reads S1..S6 in order.

The literal range phrase "Table S1 to Table S6" is protected: its two endpoints
are the extremes of the new numbering as well, and rewriting them inside the
range would produce "Table S5 to Table S1".

Run with ``--check`` to report the first-citation order without writing anything.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.dirname(HERE)
MOTHER = os.path.join(HERE, "00_manuscript_EN.md")
ADRAFT = os.path.join(HERE, "_assemble_draft_v033.py")
ASUPP = os.path.join(HERE, "_assemble_supp_v033.py")
BTAB = os.path.join(PAPER, "tables", "_build_v033_tables.py")
ASSEMBLED = os.path.join(HERE, "01_draft_v0.43_assembled.md")

MAP = {1: 5, 2: 6, 3: 3, 4: 4, 5: 2, 6: 1}
RANGE = "Table S1 to Table S6"
RANGE_TOKEN = "@@RANGE_S1_S6@@"

TARGETS = [MOTHER, ADRAFT, ASUPP, BTAB]


def replace_numbers(text):
    """Cycle-safe substitution of every ``Table S<d>`` token."""
    n_range = text.count(RANGE)
    text = text.replace(RANGE, RANGE_TOKEN)

    hits = 0

    def sub(m):
        nonlocal hits
        hits += 1
        old = int(m.group(1))
        return "Table S@@%d@@" % MAP[old]

    text = re.sub(r"Table S([1-6])\b", sub, text)
    text = re.sub(r"Table S@@(\d)@@", lambda m: "Table S%s" % m.group(1), text)
    text = text.replace(RANGE_TOKEN, RANGE)
    return text, hits, n_range


def reorder_tables_block(text):
    """Sort the ``TABLES = [...]`` entries of the supplement by display number."""
    start = text.index("TABLES = [")
    # include the newline that closes the last entry, or a moved entry loses it
    end = text.index("\n]\n", start) + 1
    head = text[:start]
    block = text[start:end]
    tail = text[end:]

    # split on the entry anchor: a line that opens a tuple with a table number
    parts = re.split(r"(?m)^(?=    \(\"Table S\d\",)", block)
    lead = parts[0]
    entries = parts[1:]
    if len(entries) != 6:
        raise SystemExit("expected 6 TABLES entries, found %d" % len(entries))

    def num(e):
        m = re.match(r'    \("Table S(\d)"', e)
        return int(m.group(1))

    nums = [num(e) for e in entries]
    if sorted(nums) != [1, 2, 3, 4, 5, 6]:
        raise SystemExit("TABLES numbers are not a permutation of 1..6: %s" % nums)
    entries.sort(key=num)
    return head + lead + "".join(entries) + tail


def first_citation_order():
    """Report where each supplementary table is first cited in the assembly."""
    if not os.path.exists(ASSEMBLED):
        return None
    body = io.open(ASSEMBLED, encoding="utf-8").read()
    body = body[:body.find("## Figure captions")]
    seen = {}
    for m in re.finditer(r"Table S(\d)", body):
        seen.setdefault(int(m.group(1)), m.start())
    return [k for k, _ in sorted(seen.items(), key=lambda kv: kv[1])]


def main():
    check_only = "--check" in sys.argv
    for p in TARGETS:
        if not os.path.exists(p):
            raise SystemExit("missing: %s" % p)

    if check_only:
        out = first_citation_order()
        print("first-citation order (assembled v0.43): %s" % out)
        print("ascending: %s" % (out == sorted(out) if out else "n/a"))
        return 0 if (out is None or out == sorted(out)) else 1

    for p in TARGETS:
        t = io.open(p, encoding="utf-8").read()

        # the TABLES block is re-sorted after its numbers change
        has_block = "TABLES = [" in t
        t, hits, n_range = replace_numbers(t)
        if has_block:
            t = reorder_tables_block(t)
        io.open(p, "w", encoding="utf-8", newline="\n").write(t)
        print("%-40s %2d renumbered, %d protected range phrase(s)"
              % (os.path.basename(p), hits, n_range))

    # no token may survive
    for p in TARGETS:
        t = io.open(p, encoding="utf-8").read()
        if "@@" in t:
            raise SystemExit("sentinel left behind in %s" % p)
    print("no sentinels left behind")
    return 0


if __name__ == "__main__":
    sys.exit(main())
