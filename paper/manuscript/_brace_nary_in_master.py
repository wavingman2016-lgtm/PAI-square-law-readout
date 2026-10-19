# -*- coding: utf-8 -*-
"""Make every nary operand in the master explicit, so the LaTeX source is
self-consistent and any downstream converter (DOCX, LaTeX) agrees.

Why this exists
---------------
``MML2OMML.XSL`` emits an **empty** ``<m:e></m:e>`` (drawn by Word as a placeholder
box) whenever it cannot recognise the operand of ``\\sum`` / ``\\int`` / ``\\prod``.
Wrapping the operand in braces, e.g. ``\\sum_m v_m`` -> ``\\sum_m {v_m}``, fixes it.
The transform is semantically identical LaTeX (grouping only).

Ground truth is ``_build_docx.brace_nary`` -- this script never re-implements the
rule, it only reports/applies what the DOCX builder would do.  That guarantees the
markdown master and the DOCX cannot drift apart.

Run:
    python _brace_nary_in_master.py --check     # report only, no writes
    python _brace_nary_in_master.py             # rewrite the master in place
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(HERE, "00_manuscript_EN.md")
sys.path.insert(0, HERE)
import _build_docx as B                                     # noqa: E402

# $...$ / $$...$$ spans; deliberately non-greedy and newline-tolerant for $$.
MATH = re.compile(r"(\$\$)(.+?)(\$\$)|(\$)([^$\n]+?)(\$)", re.S)


def scan(text):
    """Yield (start, end, old_latex, new_latex) for every math span that changes."""
    out = []
    for m in MATH.finditer(text):
        if m.group(1):                                       # display $$...$$
            old = m.group(2)
        else:                                                # inline $...$
            old = m.group(5)
        new = B.brace_nary(old)
        if new != old:
            out.append((m.start(), m.end(), old, new))
    return out


def main():
    t = io.open(MASTER, encoding="utf-8").read()
    changes = scan(t)

    # invariant: brace_nary must be idempotent, otherwise the rewrite is not settled
    non_idem = [n for _, _, o, n in changes if B.brace_nary(n) != n]

    print("math spans needing an explicit nary operand: %d" % len(changes))
    for _, _, o, n in changes:
        print("   -", o)
        print("   +", n)
    if non_idem:
        print("!! brace_nary NOT idempotent on %d span(s):" % len(non_idem))
        for n in non_idem:
            print("     ", n)

    if "--check" in sys.argv:
        return 0 if not changes and not non_idem else 1

    if non_idem:
        print("nothing written (fix brace_nary first)")
        return 1
    if not changes:
        print("master already explicit; nothing to write")
        return 0

    for st, en, o, n in reversed(changes):                   # right-to-left keeps offsets
        t = t[:st] + t[st:en].replace(o, n, 1) + t[en:]
    io.open(MASTER, "w", encoding="utf-8", newline="\n").write(t)

    # re-read and confirm convergence
    t2 = io.open(MASTER, encoding="utf-8").read()
    left = scan(t2)
    print("rewrote %s ; spans still needing a rewrite: %d" % (MASTER, len(left)))
    return 0 if not left else 1


if __name__ == "__main__":
    sys.exit(main())
