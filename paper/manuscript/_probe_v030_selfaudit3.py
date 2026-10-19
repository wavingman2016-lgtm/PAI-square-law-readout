# -*- coding: utf-8 -*-
"""v0.30 第三轮自查：旧口径残留探针（无窗口扫）+ 阳性对照 + $ 配对。

注意：正则里的 $ 用 chr(36) 构造，避免脚本自身转义把探针变成假阴性/假阳性。
"""
import io
import sys

DOLLAR = chr(36)
p = 'paper/manuscript/01_draft_v0.30_assembled.md'
s = io.open(p, encoding='utf-8').read()

BAD = [
    (u'31–34%', u'旧展宽带宽'),
    (u'−0.225', u'旧 E−M'),
    (u'−0.124', u'旧 E−M'),
    (u'0.9425 mm', u'旧 W1 宽度'),
    (u'0.1422', u'旧 W1 宽度'),
    (u'0.72–0.88', u'旧 gCNR 区间'),
    (u'0.05%', u'旧补偿比值'),
    (u'gCNR_C = 0.767', u'旧 gCNR_C'),
    (u'≤0.34 %', u'旧残差'),
    (u'β>1', u'旧 beta 表述'),
    (u'all four arms', u'旧臂数'),
    (u'E4c below', u'旧交叉引用方向'),
    (u'over30', u'拼写'),
    (u'no folding contamination', u'过强表述'),
    (u'**13 tested scenarios**', u'旧 13 限定'),
    (u'all 13 tested scenarios', u'旧 13 限定'),
    (u'paired audit (13 tested scenarios)', u'旧 13 限定'),
    (u'0.5457 mm for the square-and-low-pass image against 0.7112',
     u'跨域宽度分句'),
    (u'a factor 0.999 in the archived sensitivity run', u'旧补偿比值'),
    (u"estimator's own numerical floor", u'无出处 floor'),
    (u'below the readout resolution', u'无参照 resolution'),
    (u'(Table 9) is **not done**', u'陈旧交叉引用'),
    (u'the *measured* band', u'PATATO 旧口径'),
    (u'wider than the band the analysis model assumes', u'PATATO 旧口径'),
    (u'measured band 1.92', u'PATATO 旧口径'),
    (u'β=0.8$ is met', u'PATATO 旧口径'),
    (u'BP(' + chr(92) + 'lvert z\nvert)]', u'LaTeX 断裂'),
    (u'W1 measured apparent widths', u'跨域宽度分句'),
]

POS = [
    u'30.5–31.0%',
    u'the squaring step costs 6–8 dB of SNR',
    u'directional count, n=4',
    u'13 tested computational scenarios',
    u'1.0066',
    u'the *constructed* analysis band',
    u'analysis band is **constructed** as',
    u'0.87 on the semicircular array and 0.62 on the ring array',
    u'BP(' + chr(92) + 'lvert z' + chr(92) + 'vert)]^2',
    u'(Table S5) is **not done**',
    u'4/4** testable datasets (' + u'−' + u'0.0385 to ' + u'−' + u'0.0009; a directional count',
]

fails = 0
print('=== 残留探针（应全为 0）===')
for pat, tag in BAD:
    c = s.count(pat)
    if c:
        fails += 1
        print('  FAIL %-24s %-24s x%d' % (tag, pat[:38], c))
print('  残留总数 = %d' % fails)

miss = 0
print('=== 阳性对照（应全存在）===')
for pat in POS:
    c = s.count(pat)
    if c == 0:
        miss += 1
        print('  MISS %s' % pat[:64])
print('  缺失数 = %d' % miss)

# $ 配对：只在**读者可见区间**（## Title 起）逐行判奇偶。
# 母本状态头位于 ## Title 之前，不进 DOCX，其中的折行/历史注记不参与判定
# （写作管线铁律：交付区间自 ## Title 起）。
D = chr(36)
ti = s.find('## Title')
body = s[ti:] if ti >= 0 else s
odd_lines = [i + 1 for i, l in enumerate(body.split('\n'))
             if (len(l) - len(l.replace(D, '')) - 2 * l.count(D * 2)) % 2]
print('=== $ 配对（区间自 ## Title 起）===')
print('  body starts at char %d ; odd lines = %d' % (ti, len(odd_lines)))
if odd_lines:
    print('   ', odd_lines[:10])
    for i in odd_lines[:5]:
        print('    >', body.split('\n')[i - 1][:160])

sys.exit(1 if (fails or miss or odd_lines) else 0)
