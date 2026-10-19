# -*- coding: utf-8 -*-
"""v0.30 审计处置：修补上一次非原子运行留下的半句，并补齐未落地的条目。"""
import io

MS = 'paper/manuscript/00_manuscript_EN.md'
ASM = 'paper/manuscript/_assemble_draft.py'
CSV5 = 'paper/tables/TableS5_validation_roadmap.csv'

stats = {}


def edit(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    k = 0
    for a, b in pairs:
        if s.count(a) < 1:
            raise SystemExit('MISS in %s: %s' % (path, a[:80]))
        s = s.replace(a, b)
        k += 1
    io.open(path, 'w', encoding='utf-8', newline='\n').write(s)
    stats[path] = stats.get(path, 0) + k


# --- 修复：读出层说明句与后句重复，需补句号并去掉悬空的 "agree to 0.3%" ---
edit(MS, [
    (u'within the energy domain $I_E$ and $M^2$ agree to 0.3% This is **not** an artefact of the compensation:',
     u'within the energy domain $I_E$ and $M^2$ agree to 0.3%.\nThis is **not** an artefact of the compensation:'),
    # 补偿比值补归档归属
    (u'a factor **1.0066** (0.5457 against 0.5421 mm) in the archived compensation check',
     u'a factor **1.0066** (0.5457 against 0.5421 mm; the two archived runs differ in the compensation branch only — the direct $r^2$ route against the production $r$-then-square route) in the archived compensation check'),
    # §4.2 的同域宽度句补归档来源
    (u'(0.3% apart; W2: 1.5254 against 1.5229 mm), so $I_E$ has exactly',
     u'(0.3% apart; W2: 1.5254 against 1.5227 mm, both read from the same archived dataset table), so $I_E$ has exactly'),
    (u'(0.5421 vs 0.5438 mm on W1; 1.5229 vs 1.5254 mm on W2), so $I_E$ has exactly',
     u'(0.5421 vs 0.5438 mm on W1; 1.5227 vs 1.5254 mm on W2, both read from the same archived dataset table), so $I_E$ has exactly'),
])

# --- 以下为上一轮未落地者，逐条独立判定，缺一即退出 ---
edit(MS, [
    # P0-F  像差两套序列
    (u'wavefront aberration (**+0.092/+0.147/+0.244** at 0.5/1/2 rad)',
     u'wavefront aberration (**+0.092/+0.147/+0.244** at 0.5/1/2 rad in the dedicated phase sweep — a separate experiment from the replicated paired audit of §4.2, which gives its own aberration series +0.0978/+0.1200/+0.1810 on its own pre-fixed seeds; the two are reported separately and not pooled)'),
    # P1 §4.2 载荷段
    (u'In a replicated run over 13 scenarios (6 replicates each,',
     u'In a replicated run over the 13 computational scenarios of the specified model (6 replicates each,'),
    # P1 §5.2 4/4
    (u'in **4 of the 4** testable datasets ($\\Delta\\mathrm{gCNR}=-0.0385\\ldots-0.0009$; W1 and W6 saturate and are recorded NA)',
     u'in **4 of the 4** testable datasets ($\\Delta\\mathrm{gCNR}=-0.0385\\ldots-0.0009$; a directional count, $n=4$, with no interval or $p$ value; W1 and W6 saturate and are recorded NA)'),
    # P1 Highlights 字符上限
    (u'- Higher gCNR than coherent back-projection in all 13 tested computational scenarios of the specified model (+0.1742).',
     u'- Higher gCNR than coherent back-projection in 13/13 model scenarios (+0.1742).'),
    (u'- Against squared envelope stacking, no advantage on a 2-D ROI (4/4 testable datasets; a directional count, n=4, no interval or $p$ value).',
     u'- No separability advantage over squared envelope stacking on a 2-D ROI.'),
    (u'- Trade vs envelope stacking: 30.9% broader spread, 6–8 dB SNR, earlier clutter failure.',
     u'- Costs: 30.9% broader spread, 6–8 dB SNR, earlier clutter failure.'),
    # P1 §4.4 括号配对 + 引用位置
    (u'On this broadband, limited-view in-vivo data (a 91° array gap; the analysis band is **constructed**',
     u'On this broadband, limited-view in-vivo data [17,18] (a 91° array gap; the analysis band is **constructed**'),
    (u'the $E$-versus-$M$ ordering) the\nchannel-wise estimator falls **below the envelope-stacking arm**',
     u'the $E$-versus-$M$ ordering), the\nchannel-wise estimator falls **below the envelope-stacking arm**'),
    # P1 DR 逐数据集对齐 registry
    (u'(per dataset: +9.64, +7.06, +15.97, +4.61, +3.23, +2.41)',
     u'(per dataset: +9.65, +7.05, +15.97, +4.63, +3.23, +2.41)'),
    # P1 0.50× 补 LP 实现限定
    (u'in computation (0.50× of the coherent arm, a saving shared by the whole envelope-domain family',
     u'in computation (0.50× of the coherent arm **for the instrumented square-and-low-pass realization**, a saving shared by the whole envelope-domain family'),
    # P1 Fig.5 未归档行披露
    (u'positive in every scenario (trend mean **+0.247**, grids mixed)',
     u'positive in every scenario (trend mean **+0.247**, grids mixed; 8 of the 15 rows are recomputed from the archived phase study and 7 are carried literals from an exploratory run that was not archived — a provenance recorded per row in the sweep table, disclosed here because those 7 cannot be recomputed from released code)'),
    # P2 摘要术语对齐正文
    (u'with a reproducible display protocol (CT-style windowing, data-domain metrics)',
     u'with a reproducible display protocol (quantile-adaptive display windowing, data-domain metrics)'),
    # P2 +0.581 → +0.5812
    (u'low SNR up to +0.581 at 0 dB', u'low SNR up to +0.5812 at 0 dB'),
    # P2 0.767 统一
    (u'gCNR$_C$ = 0.215 in one script and 0.763 in another',
     u'gCNR$_C$ = 0.215 in one script and 0.767 in another'),
    # P2 Table 1 残留 ASCII
    (u'| M | envelope stacking: I_M = sum_m g_m \\|z_m\\| |',
     u'| M | envelope stacking: $I_M = \\sum_m g_m \\lvert z_m\\rvert$ |'),
    # P2 Conclusion 标题自标词数失真
    (u'## 6. Conclusion  *(target ≈4%, ≤150 words)*',
     u'## 6. Conclusion  *(target ≈4%)*'),
])

# --- P0-B  Fig. 3(f) 图注：跨域比较（读者可见，审稿人先看图注）---
edit(ASM, [
    (u'"−3 dB width of $I_E$ and the −3 dB width of $I_M$ is 30.88 %, which is what a "',
     u'"amplitude-domain width $\\\\mathrm{FWHM}(\\\\sqrt{I_E})$ and that of $I_M$ is 30.9 % "\n                  "(0.9625 against 0.7354 mm), which is what a "'),
])

# --- P0-C  Table S5 CSV：§ 在源文件即已丢失 ---
s = io.open(CSV5, encoding='utf-8').read()
c = 0
for a, b in [(u'S2.7', u'§2.7'), (u'S2.1', u'§2.1'), (u'S2.2', u'§2.2'),
             (u'S4.2', u'§4.2'), (u'S2.3', u'§2.3')]:
    c += s.count(a)
    s = s.replace(a, b)
io.open(CSV5, 'w', encoding='utf-8', newline='\n').write(s)
stats[CSV5 + ' (§ restored)'] = c

for k in sorted(stats):
    print('%-58s %d' % (k, stats[k]))
