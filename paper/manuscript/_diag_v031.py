# -*- coding: utf-8 -*-
import io
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
ms = io.open(os.path.join(_HERE, '00_manuscript_EN.md'), encoding='utf-8').read()
body = ms[ms.index('## Title'):ms.index('## Figure captions (draft)')]
i = body.find('no re-timing')
print('find no re-timing:', i)
if i >= 0:
    seg = body[i:i+60]
    print('segment:', repr(seg))
    for ch in seg:
        if ord(ch) > 127 or ch in '- ':
            print('  special char %r U+%04X' % (ch, ord(ch)))
print('count full phrase:', body.count('no re-timing after removing arm'))
j = body.find('no re-timing after removing')
print('partial find:', j)
if j >= 0:
    print('partial segment:', repr(body[j:j+50]))
