# -*- coding: utf-8 -*-
"""v0.30 第三轮审计处置：11 项（5 P0 + 6 P1）+ 5 项 P2。

每条均已独立取证；驳回项见 _adjudication_v030.md。
"""
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


D = u'Δ'
NDASH = u'–'
MINUS = u'−'
BETA = u'β'

# ============ P0-A  30.5–31.0% → 30.9%（唯一可核值，取消跨归档区间合并）============
_s = io.open(MS, encoding='utf-8').read()
_n = _s.count(u'30.5–31.0%')
_s = _s.replace(u'30.5–31.0%', u'30.9%')
io.open(MS, 'w', encoding='utf-8', newline='\n').write(_s)
stats[MS + ' :: global 30.5-31.0'] = _n

edit(MS, [
    # 首次出现处补读出层说明，消除同句自相矛盾
    (u'$I_E$ is 30.9% broader than $M$ and $\\approx$6.5× broader than $C$ (simulation, $N_\\mathrm{rep}=4$, per-replicate widths archived in the released resolution log: $\\sqrt{I_E}$ 0.9625 ± 0.0013 mm against $I_C$ 0.1482 ± 0.0000 mm), read at a common −6 dB level in the amplitude domain.',
     u'$I_E$ is 30.9% broader than $M$ and $\\approx$6.5× broader than $C$ (simulation, $N_\\mathrm{rep}=4$, per-replicate widths archived in the released resolution log: $\\sqrt{I_E}$ 0.9625 ± 0.0013 mm against $I_M$ 0.7354 ± 0.0004 mm and against $I_C$ 0.1482 ± 0.0000 mm). That figure is a read-back comparison: $\\sqrt{I_E}$ is the same arm returned to the amplitude domain, and it is a **different statement** from the same-domain identity that follows — within the energy domain $I_E$ and $M^2$ agree to 0.3%'),
    # 同段：去掉重复的 "within the energy domain"
    (u'(0.5421 vs 0.5438 mm on W1; 1.5229 vs 1.5254 mm on W2), so $I_E$ has exactly the resolution of *the envelope arm squared* and the broadening belongs to $L_2$ aggregation itself.',
     u'(0.5421 vs 0.5438 mm on W1; 1.5227 vs 1.5254 mm on W2, both from the same archived dataset table), so $I_E$ has exactly the resolution of *the envelope arm squared* and the broadening belongs to $L_2$ aggregation itself.'),
    (u'(0.3% apart; W2: 1.5254 against 1.5229 mm), so $I_E$ has exactly\nthe resolution of the envelope arm *squared*',
     u'(0.3% apart; W2: 1.5254 against 1.5227 mm, both read from the same archived dataset table), so $I_E$ has exactly\nthe resolution of the envelope arm *squared*'),
    (u'— two orders below the 30.9% broadening it would have to explain —',
     u'— more than an order of magnitude below the 30.9% broadening it would have to explain —'),
])

# ============ P0-D  W2 1.5229 → 1.5227（统一取 results/wire）============
edit(MS, [
    (u'1.5229 vs 1.5254 mm on W2', u'1.5227 vs 1.5254 mm on W2'),
    (u'(W2: 1.5254 against 1.5229 mm)', u'(W2: 1.5254 against 1.5227 mm)'),
])

# ============ P0-E  0.5421/0.5457 标注归档归属 ============
edit(MS, [
    (u'moving the $E$ FWHM by a factor **1.0066** (0.5457 against 0.5421 mm) in the archived compensation check — two orders below the 30.9% broadening it would have to explain —',
     u'moving the $E$ FWHM by a factor **1.0066** (0.5457 against 0.5421 mm; the two archived runs differ in the compensation branch only, the direct $r^2$ route against the production $r$-then-square route) in the archived compensation check — more than an order of magnitude below the 30.9% broadening it would have to explain —'),
])

# ============ P0-F  像差两套序列声明为两次独立实验 ============
edit(MS, [
    (u'wavefront aberration (**+0.092/+0.147/+0.244** at 0.5/1/2 rad)',
     u'wavefront aberration (**+0.092/+0.147/+0.244** at 0.5/1/2 rad in the dedicated phase sweep, a separate experiment from the replicated paired audit of §4.2, which gives its own aberration series +0.0978/+0.1200/+0.1810 on its own pre-fixed seeds; the two are reported separately and not pooled)'),
])

# ============ P1  §4.2 载荷段补 13 场景模型限定 ============
edit(MS, [
    (u'In a replicated run over 13 scenarios (6 replicates each,',
     u'In a replicated run over the 13 computational scenarios of the specified model (6 replicates each,'),
])

# ============ P1  §5.2 4/4 补统计口径 ============
edit(MS, [
    (u'there $E$ is *behind* on separability in **4 of the 4** testable datasets ($\\Delta\\mathrm{gCNR}=-0.0385\\ldots-0.0009$; W1 and W6 saturate and are recorded NA)',
     u'there $E$ is *behind* on separability in **4 of the 4** testable datasets ($\\Delta\\mathrm{gCNR}=-0.0385\\ldots-0.0009$; a directional count, $n=4$, with no interval or $p$ value; W1 and W6 saturate and are recorded NA)'),
])

# ============ P1  Highlights 三条超 85 字符 ============
edit(MS, [
    (u'- Higher gCNR than coherent back-projection in all 13 tested computational scenarios of the specified model (+0.1742).',
     u'- Higher gCNR than coherent back-projection in 13/13 model scenarios (+0.1742).'),
    (u'- Against squared envelope stacking, no advantage on a 2-D ROI (4/4 testable datasets; a directional count, n=4, no interval or $p$ value).',
     u'- No separability advantage over squared envelope stacking on a 2-D ROI.'),
    (u'- Trade vs envelope stacking: 30.9% broader spread, 6–8 dB SNR, earlier clutter failure.',
     u'- Costs: 30.9% broader spread, 6–8 dB SNR, earlier clutter failure.'),
])

# ============ P1  §4.4 括号配对 + 引用位置 ============
edit(MS, [
    (u'On this broadband, limited-view in-vivo data (a 91° array gap; the analysis band is **constructed** as $[0.6f_0,1.4f_0]$ = 1.92–4.48 MHz about the de-drifted measured centre $f_0$, giving $\\beta=B/f_0=0.80<1$, so the Hilbert-free precondition holds; what fails on this dataset is not $\\beta$ but the $E$-versus-$M$ ordering) [17,18] the\nchannel-wise estimator falls **below the envelope-stacking arm**',
     u'On this broadband, limited-view in-vivo data [17,18] (a 91° array gap; the analysis band is **constructed** as $[0.6f_0,1.4f_0]$ = 1.92–4.48 MHz about the de-drifted measured centre $f_0$, giving $\\beta=B/f_0=0.80<1$, so the Hilbert-free precondition holds; what fails on this dataset is not $\\beta$ but the $E$-versus-$M$ ordering), the\nchannel-wise estimator falls **below the envelope-stacking arm**'),
])

# ============ P1  DR 逐数据集值对齐 registry ============
edit(MS, [
    (u'(per dataset: +9.64, +7.06, +15.97, +4.61, +3.23, +2.41)',
     u'(per dataset: +9.65, +7.05, +15.97, +4.63, +3.23, +2.41)'),
])

# ============ P1  0.50× 补 LP 实现限定（§5.7 不主张清单）============
edit(MS, [
    (u'in computation (0.50× of the coherent arm, a saving shared by the whole envelope-domain family and **not** attributable to squaring or to Hilbert removal, §4.2)',
     u'in computation (0.50× of the coherent arm **for the instrumented square-and-low-pass realization**, a saving shared by the whole envelope-domain family and **not** attributable to squaring or to Hilbert removal, §4.2)'),
])

# ============ P1  Fig. 5 未归档行披露 ============
edit(MS, [
    (u'per-scenario $\\Delta$gCNR (E−C) from the broad 15-scenario cross-grid sweep, positive in every scenario (trend mean **+0.247**, grids mixed)',
     u'per-scenario $\\Delta$gCNR (E−C) from the broad 15-scenario cross-grid sweep, positive in every scenario (trend mean **+0.247**, grids mixed; 8 of the 15 rows are recomputed from the archived phase study and 7 are carried literals from an exploratory run that was not archived, a provenance recorded per row in the sweep table and disclosed here because those 7 cannot be recomputed from released code)'),
])

# ============ P2  摘要 CT-style → 与正文术语对齐 ============
edit(MS, [
    (u'with a reproducible display protocol (CT-style windowing, data-domain metrics)',
     u'with a reproducible display protocol (quantile-adaptive display windowing, data-domain metrics)'),
])

# ============ P2  +0.581 → +0.5812（同轴）============
edit(MS, [
    (u'low SNR up to +0.581 at 0 dB', u'low SNR up to +0.5812 at 0 dB'),
])

# ============ P2  0.767 统一 ============
edit(MS, [
    (u'gCNR$_C$ = 0.215 in one script and 0.763 in another',
     u'gCNR$_C$ = 0.215 in one script and 0.767 in another'),
])

# ============ P2  Table 1 残留 ASCII ============
edit(MS, [
    (u'| M | envelope stacking: I_M = sum_m g_m \\|z_m\\| |',
     u'| M | envelope stacking: $I_M = \\sum_m g_m \\lvert z_m\\rvert$ |'),
])

# ============ P2  Conclusion 标题自标词数失真 ============
edit(MS, [
    (u'## 6. Conclusion  *(target ≈4%, ≤150 words)*',
     u'## 6. Conclusion  *(target ≈4%)*'),
])

# ============ P0-B  Fig. 3(f) 图注跨域比较（硬编码于 _assemble_draft.py）============
edit(ASM, [
    (u'"−3 dB width of $I_E$ and the −3 dB width of $I_M$ is 30.88 %, which is what a "',
     u'"amplitude-domain width $\\\\mathrm{FWHM}(\\\\sqrt{I_E})$ and that of $I_M$ is 30.9 % "\n                  "(0.9625 against 0.7354 mm), which is what a "'),
])

# ============ P0-C  Table S5 CSV 的 § 丢失 ============
s = io.open(CSV5, encoding='utf-8').read()
cnt = 0
for a, b in [(u'S2.7', u'§2.7'), (u'S2.1', u'§2.1'), (u'S2.2', u'§2.2'),
             (u'S4.2', u'§4.2'), (u'S2.3', u'§2.3')]:
    cnt += s.count(a)
    s = s.replace(a, b)
io.open(CSV5, 'w', encoding='utf-8', newline='\n').write(s)
stats[CSV5] = cnt

for k in sorted(stats):
    print('%-52s %d' % (k, stats[k]))
