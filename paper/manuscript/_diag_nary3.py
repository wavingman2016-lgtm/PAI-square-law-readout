# -*- coding: utf-8 -*-
"""精确定位：复现 _build_docx.build(--dry) 的判定逻辑，打印产生空操作数的
(sanitize 前原文, brace_nary 后, nary 的空 <m:e> 文本) 三元组。"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _build_docx as B

md = io.open(B.MD, encoding="utf-8").read()

# 与 build() 完全相同的表达式收集
exprs = set()
for m in re.finditer(r"\$\$(.+?)\$\$", md, flags=re.S):
    exprs.add(("D", m.group(1)))
for m in re.finditer(r"\$([^$\n]+)\$", md):
    exprs.add(("I", m.group(1)))

hits = 0
for kind, e in sorted(exprs):
    try:
        s1 = B.sanitize(e)
        s2 = B.brace_nary(s1)
        root = B.math_omml(e)
        empties = []
        for nary in root.findall(".//" + B.MML + "nary"):
            ee = nary.find(B.MML + "e")
            txt = "" if ee is None else "".join(ee.itertext()).strip()
            if ee is None or not txt:
                empties.append(repr(txt))
        if empties:
            hits += 1
            print("=" * 78)
            print("RAW     :", repr(e))
            print("SANITIZE:", repr(s1))
            print("BRACED  :", repr(s2))
            print("EMPTY   :", len(empties), empties)
            # 打印 brace_nary 后的 nary 片段上下文
            for mm in re.finditer(r"\\(?:sum|int|prod|oint|bigcup|bigcap)\b", s2):
                j = mm.start()
                print("   nary ctx:", repr(s2[j:j + 60]))
    except Exception as ex:  # noqa: BLE001
        print("!! convert failed:", repr(e[:60]), type(ex).__name__, ex)

print("\nTOTAL expressions with empty nary:", hits)
