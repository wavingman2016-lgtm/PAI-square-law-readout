# -*- coding: utf-8 -*-
import io

p = 'paper/manuscript/00_manuscript_EN.md'
s = io.open(p, encoding='utf-8').read()
n = 0


def rep(a, b):
    global s, n
    assert s.count(a) >= 1, 'MISS: ' + a[:90]
    s = s.replace(a, b, 1)
    n += 1


MINUS = u'\u2212'
NDASH = u'\u2013'
MDASH = u'\u2014'
DEG = u'\u00b0'

# --- P0-1  \u00a74.2 LaTeX \u8de8\u884c\u65ad\u88c2 ---
rep(u"and $M^2=[BP(\\lvert z\nvert)]^2$.",
    u"and $M^2=[BP(\\lvert z\\vert)]^2$.")

# --- P0-2  PATATO \u5e26\u9891\uff1a\u6539\u4e3a\u6784\u9020\u5e26\u53e3\u5f84\uff08\u4e24\u5904\uff09 ---
rep(u"(91" + DEG + u" array gap; measured band 1.92" + NDASH + u"4.48 MHz, so $\\beta=0.8$ is met but the band is wider than the filter model assumes)",
    u"(a 91" + DEG + u" array gap; the *constructed* analysis band $[0.6f_0,1.4f_0]$ = 1.92" + NDASH + u"4.48 MHz gives $\\beta=B/f_0=0.80<1$, so the Hilbert-free precondition holds and what fails here is not $\\beta$ but the $E$-versus-$M$ ordering)")
rep(u"(a 91" + DEG + u" array gap; the *measured* band, 1.92" + NDASH + u"4.48 MHz, is wider than the band the analysis model assumes)",
    u"(a 91" + DEG + u" array gap; the analysis band is **constructed** as $[0.6f_0,1.4f_0]$ = 1.92" + NDASH + u"4.48 MHz about the de-drifted measured centre $f_0$, giving $\\beta=B/f_0=0.80<1$, so the Hilbert-free precondition holds; what fails on this dataset is not $\\beta$ but the $E$-versus-$M$ ordering)")

# --- P0-3  \u5220\u9664\u8de8\u57df W1 \u5bbd\u5ea6\u5206\u53e5\uff1b\u4fee\u6b63 0.999 \u8865\u507f\u6bd4\u503c ---
rep(u"$\\sqrt{I_E}$ 0.9625 \u00b1 0.0013 mm against $I_C$ 0.1482 \u00b1 0.0000 mm; W1 measured apparent widths: 0.5457 mm for the square-and-low-pass image against 0.7112 mm for the envelope image)",
    u"$\\sqrt{I_E}$ 0.9625 \u00b1 0.0013 mm against $I_C$ 0.1482 \u00b1 0.0000 mm)")
rep(u"This is **not** an artefact of the compensation: $r^2$ instead of $r$ changes the width by a factor 0.999 in the archived sensitivity run, i.e. below the readout resolution (\u00a74.1, Table 2), and within the energy domain",
    u"This is **not** an artefact of the compensation: on W1 the alternative $r^2$ compensation leaves the $E$ image essentially unchanged, moving the $E$ FWHM by a factor **1.0066** (0.5457 against 0.5421 mm) in the archived compensation check \u2014 two orders below the 30.5" + NDASH + u"31.0% broadening it would have to explain \u2014 and within the energy domain")

# --- P0-4  clutter \u533a\u95f4\uff1a\u8865\u53d6\u5904\u5f52\u6863 ---
rep(u"(fair width 0.98 \u2192 27" + NDASH + u"40 mm; gCNR 1.000 \u2192 0.62" + NDASH + u"0.87)",
    u"(archived clutter-regime runs: fair width 0.99" + NDASH + u"1.03 mm \u2192 27" + NDASH + u"40 mm, with the energy read-out falling from the envelope arm's saturated gCNR of 1.000 to 0.87 on the semicircular array and 0.62 on the ring array)")

# --- P1-5  13/13 \u9650\u5b9a\u8bed\u4e24\u5904 ---
rep(u"- Higher gCNR than coherent back-projection in all 13 tested scenarios (+0.1742).",
    u"- Higher gCNR than coherent back-projection in all 13 tested computational scenarios of the specified model (+0.1742).")
rep(u"the currency is separability.* In the replicated paired audit (13 tested scenarios)",
    u"the currency is separability.* In the replicated paired audit (13 tested computational scenarios of the specified model)")

# --- P1-6  4/4 \u7edf\u8ba1\u53e3\u5f84\u516d\u5904 ---
rep(u"- Against squared envelope stacking, no advantage on a 2-D ROI (4/4 testable datasets).",
    u"- Against squared envelope stacking, no advantage on a 2-D ROI (4/4 testable datasets; a directional count, n=4, no interval or $p$ value).")
rep(u"the paired difference against the squared envelope-stacking image is negative in **4/4** testable datasets (" + MINUS + u"0.0385 to " + MINUS + u"0.0009; two saturate, recorded NA), unchanged when the proxy realization is substituted",
    u"the paired difference against the squared envelope-stacking image is negative in **4/4** testable datasets (" + MINUS + u"0.0385 to " + MINUS + u"0.0009; a directional count, n=4, no interval or $p$ value; two saturate, recorded NA), unchanged when the proxy realization is substituted")
rep(u"(negative in 4/4 testable datasets), corroborated by one-dimensional profile controls",
    u"(negative in 4/4 testable datasets " + MDASH + u" a directional count, n=4, with no interval or $p$ value, \u00a74.2), corroborated by one-dimensional profile controls")
rep(u"| no imaging advantage over squared envelope stacking | 2-D ROI common-domain control on the production realization (4/4 testable) + 1-D profile controls |",
    u"| no imaging advantage over squared envelope stacking | 2-D ROI common-domain control on the production realization (4/4 testable; directional count, n=4, no interval or $p$ value) + 1-D profile controls |")
rep(u"negative in **4/4** testable datasets (\u00a74.2); the non-saturating auxiliary endpoint reverses sign on W3;",
    u"negative in **4/4** testable datasets (\u00a74.2; directional count, n=4, no interval or $p$ value); the non-saturating auxiliary endpoint reverses sign on W3;")

# --- P1-7  numerical floor \u2192 \u53ef\u6eaf\u6e90\u7684\u5206\u7bb1\u81ea\u68c0\u53c2\u7167 ---
rep(u"is of the same order as the estimator's own numerical floor, so the count reads as",
    u"is smaller than the estimator's own binning resolution " + MDASH + u" the same metric on deliberately shifted synthetic pairs moves by 0.36" + NDASH + u"0.86 in the archived self-check " + MDASH + u" so the count reads as")

# --- P2-8  \u00a72.7 \u9648\u65e7\u4ea4\u53c9\u5f15\u7528 ---
rep(u"since experiment **E1** (Table 9) is **not done**",
    u"since experiment **E1** (Table S5) is **not done**")

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('replacements applied:', n)
