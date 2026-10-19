#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Export the v0.43 DOCX to PDF with Word, then count the characters that the
DOCX->PDF path is known to damage.

Why a PDF at all
----------------
A reviewer once reported "the numbers are corrupted" for a draft whose DOCX was
correct: the damage was introduced by the PDF export, not by the manuscript.
Character-level forensics on the exported file is the only way to tell the two
apart, and it has to run on the *exported* artefact rather than on the source.

What is counted
---------------
The four characters that have gone missing or changed in earlier rounds, plus a
control that must be non-zero so an empty extraction cannot look clean:

    %  percent signs in numeric ranges
    -  U+2013 en dash (range separator)
    -  U+2212 minus sign (negative numbers in running text)
    :  colon in ratios and labels
    b  U+03B2 Greek beta (mu/beta notation in section 2.2)

Usage
-----
    python paper/manuscript/_export_proof_v043.py
"""
import os
import sys

import pymupdf
import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOCX = os.path.join(HERE, "02_PAI_manuscript_v0.43_draft.docx")
OUTDIR = os.path.join(ROOT, "_proof")
PDF = os.path.join(OUTDIR, "PAI_v043_proof.pdf")


def export():
    if not os.path.exists(DOCX):
        raise SystemExit("missing: %s" % DOCX)
    if not os.path.isdir(OUTDIR):
        os.makedirs(OUTDIR)
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    doc = None
    try:
        doc = word.Documents.Open(DOCX, ReadOnly=True, AddToRecentFiles=False)
        # wdExportFormatPDF = 17
        doc.ExportAsFixedFormat(OutputFileName=PDF, ExportFormat=17,
                                OpenAfterExport=False, OptimizeFor=0,
                                CreateBookmarks=1, DocStructureTags=True)
    finally:
        if doc is not None:
            doc.Close(SaveChanges=False)
        word.Quit()
    return PDF


def main():
    pdf = export()
    d = pymupdf.open(pdf)
    text = "".join(p.get_text() for p in d)
    print("exported -> %s" % os.path.relpath(pdf, ROOT))
    print("pages %d | characters %d" % (d.page_count, len(text)))
    marks = [
        ("%", "%"),
        ("\u2013", "en dash"),
        ("\u2212", "minus sign"),
        (":", "colon"),
        ("\u03b2", "beta"),
    ]
    for ch, label in marks:
        print("  %-12s %-4s %5d" % (label, ch, text.count(ch)))
    # controls: a string that must survive the export unchanged
    for probe in ["1.96 to 3.12", "PAI-v0.43", "Table S1", "Illustrative limited-view"]:
        print("  control %-28s %s" % (probe, probe in text))
    d.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
