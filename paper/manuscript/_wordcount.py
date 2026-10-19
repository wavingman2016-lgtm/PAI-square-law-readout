#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Summary/abstract word count, done one way and stated the same way every time.

Why this file exists
--------------------
The v0.20 note carried the sentence "495 words" without a script.  That number could not be
reproduced afterwards from the v0.20 text by any tokenizer tried, which makes it an
unverifiable claim in a manuscript whose whole selling point is traceability.  A number that
cannot be regenerated is not evidence; so the count is now a command.

Conventions (both reported, the stricter one quoted in the manuscript)
----------------------------------------------------------------------
  A. every whitespace-separated run of [A-Za-z0-9'-.] that contains at least one
     alphanumeric character counts as one word.  Hyphens and slashes split.
  B. as A, but hyphenated/slashed compounds (`square-and-low-pass`, `15/15`) stay one token.

In both, all mathematics is removed first: display blocks `$$...$$` and inline `$...$`.
Blockquote lines (lines starting with `>`, i.e. drafting notes) are removed as well — they
are not part of the abstract a journal would count.

Usage::

    python _wordcount.py                     # the Abstract of 00_manuscript_EN.md
    python _wordcount.py --section Highlights
    python _wordcount.py path/to/file.md --section Abstract

Zero third-party dependencies.
"""
import argparse
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MD = os.path.join(HERE, "00_manuscript_EN.md")

ALPHA = re.compile(r"[A-Za-z0-9]")
TOK_A = re.compile(r"[^A-Za-z0-9'\-\. ]")
TOK_B = re.compile(r"[^A-Za-z0-9'\-\./ ]")


def section(text, name):
    """Return the body of `## <name>` up to the next `## ` heading."""
    m = re.search(r"^##\s+" + re.escape(name) + r"\s*$", text, re.M)
    if not m:
        raise SystemExit("section %r not found" % name)
    rest = text[m.end():]
    nxt = re.search(r"^##\s+", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def strip_non_prose(body):
    body = "\n".join(l for l in body.split("\n") if not l.lstrip().startswith(">"))
    body = re.sub(r"\$\$.*?\$\$", " ", body, flags=re.S)     # display maths
    body = re.sub(r"\$[^$\n]*\$", " ", body)                  # inline maths
    return body


def count(body, tok):
    body = re.sub(tok, " ", body)
    return len([w for w in body.split() if ALPHA.search(w)])


def main():
    ap = argparse.ArgumentParser(description="abstract word count (reproducible)")
    ap.add_argument("md", nargs="?", default=DEFAULT_MD)
    ap.add_argument("--section", default="Abstract")
    ap.add_argument("--limit", type=int, default=500)
    a = ap.parse_args()

    text = io.open(a.md, "r", encoding="utf-8").read()
    prose = strip_non_prose(section(text, a.section))
    n_a, n_b = count(prose, TOK_A), count(prose, TOK_B)

    print("file      : %s" % a.md)
    print("section   : %s" % a.section)
    print("convention A (hyphens/slashes split) : %d" % n_a)
    print("convention B (compounds kept whole)  : %d" % n_b)
    print("limit     : %d  ->  %s" % (a.limit, "OK" if n_a <= a.limit else "OVER"))
    if a.section == "Abstract":
        print("\nQuote in the manuscript: convention A (= %d)." % n_a)
    return 0 if n_a <= a.limit else 1


if __name__ == "__main__":
    raise SystemExit(main())
