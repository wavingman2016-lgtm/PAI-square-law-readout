# -*- coding: utf-8 -*-
"""逐个 nary 表达式走完 sanitize -> brace_nary -> l2m -> XSLT，
直接报告哪一个产出空的 <m:e></m:e>。"""
import io
import re
import sys

HERE = '.'
sys.path.insert(0, HERE)

# 复制 _build_docx.py 里的相关函数（避免 import 时执行整个构建）
src = io.open('_build_docx.py', encoding='utf-8').read()
blocks = re.findall(
    r'def (?:_match_delim|_match_brace|sanitize|brace_nary)\(.*?(?=\ndef |\nclass |\n# ---)',
    src, re.S)
ns = {'re': re}
for b in blocks:
    exec(b, ns)

import latex2mathml.converter as l2m
from lxml import etree

XSLT = etree.XSLT(etree.parse(r"C:////Program Files////Microsoft Office////root////Office16////MML2OMML.XSL"))

BS = chr(92)
TOKENS = ['sum', 'int', 'prod', 'oint', 'bigcup', 'bigcap']
MML = '{http://www.w3.org/1998/Math/MathML}'

s = io.open('01_draft_v0.19_assembled.md', encoding='utf-8').read()

# 抽出所有 $...$ / $$...$$ 片段
frags = []
for mm in re.finditer(r'\$\$(.+?)\$\$|\$([^$\n]+?)\$', s, re.S):
    frags.append(mm.group(1) or mm.group(2))

bad = 0
for fr in frags:
    if not any((BS + t) in fr for t in TOKENS):
        continue
    try:
        t = ns['brace_nary'](ns['sanitize'](fr))
        dom = etree.fromstring(l2m.convert(t).encode('utf-8'))
        root = XSLT(dom).getroot()
    except Exception as e:
        print('CONVERT FAIL:', fr[:80], '->', e)
        bad += 1
        continue
    for nary in root.findall('.//' + MML + 'nary'):
        e = nary.find(MML + 'e')
        if e is not None and len(e) == 0:
            bad += 1
            print('EMPTY OPERAND in:', fr[:130])
            print('   after brace_nary:', t[:160])
print('empty/broken:', bad)
