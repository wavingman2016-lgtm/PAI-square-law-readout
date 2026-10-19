# -*- coding: utf-8 -*-
"""
_cite_insert.py -- 把 refs.bib 的 25 条文献变成正文内的编号引用 + 正式文献表。

为什么存在
    v0.21 验收清单的 **X2**（阻断项）指出：稿件只有一张 "claim -> bib key" 的**草稿映射表**，
    没有正式文献表，正文里的引用也写成了反引号键名（如 `` `patato2023` ``）。本脚本补上这一条：
      正文锚点句 -> 插入 [n]  ->  References 段重建为 Vancouver 编号表

体例说明
    Elsevier / Photoacoustics 的 "number" 体例允许方括号编号。本项目 DOCX 管线**不支持**
    行内上标（<sup> 未被 _build_docx.py 处理），故统一用 `[n]`，而不是上标数字。
    编号 = **首次出现顺序**（refs.bib 里已声明）。

幂等
    已插入过（检测到 "## References" 下方出现 "1. Beard P." ）则直接退出 0，不重复插入。
    任一锚点命中数 != 1 时**失败退出**，不写盘（全或无）。

用法
    python paper/manuscript/_cite_insert.py --check    # 只报告
    python paper/manuscript/_cite_insert.py            # 写盘

版本：v1  2026-10-16
"""
import argparse
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, "00_manuscript_EN.md")

# ---------------------------------------------------------------- 锚点 -> [n]
# (anchor, replacement)；anchor 必须在文中**恰好出现一次**。
EDITS = [
    # §1.1  -- 1 beard2011, 2 wang2007book ；3-6 xu2005ubp / kruger1995paus / lutzweiler2013 / rosenthal2013
    ("and $F$ the local fluence. Back-projection",
     "and $F$ the local fluence [1,2]. Back-projection"),
    ("coherently summing delayed channel signals; in the analytic-signal",
     "coherently summing delayed channel signals [3\u20136]; in the analytic-signal"),
    # §1.2 -- 7 ntziachristos2010frontier ；8 prakash2024tenalgo
    ("obeys $p_0\\propto\\mu_\\mathrm{a}F$ \u2014 so the amplitude",
     "obeys $p_0\\propto\\mu_\\mathrm{a}F$ [2,7] \u2014 so the amplitude"),
    ("a recent ten-algorithm survey of linear-array reconstruction includes",
     "a recent ten-algorithm survey of linear-array reconstruction [8] includes"),
    # §2.2 -- 9 boashash1992if
    ("recovers the squared envelope without ever forming the analytic signal:",
     "recovers the squared envelope without ever forming the analytic signal [9]:"),
    # §2.3 -- 10 goodman1976speckle
    ("and to $1/\\sqrt M$ **only** for independent equal-intensity channels.",
     "and to $1/\\sqrt M$ **only** for independent equal-intensity channels [10]."),
    # §3 Data -- 11 patato2023 ; 12-13 he2022rsom/rsom2023 ; 14-15 lin2021_3dpact/pact3d2020
    ("*External in-vivo* (Table 4): PATATO (mouse, 256 channels, raw time series), RSOM (human skin, raw A-lines), and 3D-PACT (rat brain and human breast, reconstructed volumes).",
     "*External in-vivo* (Table 4): PATATO [11] (mouse, 256 channels, raw time series), RSOM [12,13] (human skin, raw A-lines), and 3D-PACT [14,15] (rat brain and human breast, reconstructed volumes)."),
    # §3 Metrics -- 16 rodriguezmolares2020gcnr
    ("the primary metric is gCNR.",
     "the primary metric is gCNR [16]."),
    # §4.4 ceiling -- 17-18 xu2004limited / pramanik2014tangential
    ("On this broadband, limited-view in-vivo data the",
     "On this broadband, limited-view in-vivo data [17,18] the"),
    # §5.4 -- 19-23 model-based / learned ；24 omar2019mesoscopy
    ("$I_E$ is computed from an explicit physical model and requires no training data; it is therefore a natural physics-based front-end for learned reconstruction, a direction left to future work.",
     "$I_E$ is computed from an explicit physical model and requires no training data; it is therefore a natural physics-based front-end for learned reconstruction [19\u201323] \u2014 a direction left to future work. The mesoscopic regime, where raster-scan geometries and high-frequency content dominate, is a natural further test bed [24]."),
    # §5.5 Data availability
    ("sources and were used unmodified: PATATO (`patato2023`, CC BY 4.0), RSOM (`he2022rsom`, `rsom2023`) and",
     "sources and were used unmodified: PATATO [11] (CC BY 4.0), RSOM [12,13] and"),
    ("3D-PACT (`lin2021_3dpact`, `pact3d2020`). File identifiers",
     "3D-PACT [14,15]. File identifiers"),
    # 25 oadat2023
    ("dataset (`oadat2023`), was evaluated",
     "dataset [25], was evaluated"),
]

# ------------------------------------------------------------ 正式文献表
REFS = [
 "Beard P. Biomedical photoacoustic imaging. Interface Focus. 2011;1(4):602\u2013631. doi:10.1098/rsfs.2011.0028",
 "Wang LV, Wu H. Biomedical Optics: Principles and Imaging. Hoboken, NJ: John Wiley & Sons; 2007. doi:10.1002/9780470177013",
 "Xu M, Wang LV. Universal back-projection algorithm for photoacoustic computed tomography. Phys Rev E. 2005;71(1):016706. doi:10.1103/PhysRevE.71.016706",
 "Kruger RA, Liu P, Fang YR, Appledorn CR. Photoacoustic ultrasound (PAUS) \u2014 reconstruction tomography. Med Phys. 1995;22(10):1605\u20131609. doi:10.1118/1.597629",
 "Lutzweiler C, Razansky D. Optoacoustic imaging and tomography: reconstruction approaches and outstanding challenges in image performance and quantification. Sensors. 2013;13(6):7345\u20137384. doi:10.3390/s130607345",
 "Rosenthal A, Ntziachristos V, Razansky D. Acoustic inversion in optoacoustic tomography: a review. Curr Med Imaging Rev. 2013;9(4):318\u2013336. doi:10.2174/15734056113096660016",
 "Ntziachristos V. Going deeper than microscopy: the optical imaging frontier in biology. Nat Methods. 2010;7(8):603\u2013614. doi:10.1038/nmeth.1483",
 "Prakash R, Manwar R, Avanaki K. Evaluation of 10 current image reconstruction algorithms for linear array photoacoustic imaging. J Biophotonics. 2024;17(3):e202300117. doi:10.1002/jbio.202300117",
 "Boashash B. Estimating and interpreting the instantaneous frequency of a signal \u2014 part 1: fundamentals. Proc IEEE. 1992;80(4):520\u2013538. doi:10.1109/5.135376",
 "Goodman JW. Some fundamental properties of speckle. J Opt Soc Am. 1976;66(11):1145\u20131150. doi:10.1364/JOSA.66.001145",
 "CRUK Cambridge Institute and Department of Physics, University of Cambridge. Example Data for PATATO: Python Photoacoustic Tomography Analysis Toolkit. Cambridge: University of Cambridge Apollo Repository; 2023. handle 1810/345836. CC BY 4.0.",
 "He H, Sch\u00f6nmann C, Schwarz M, Hindelang B, Berezhnoi A, Steimle-Grauer SA, Darsow U, Aguirre J, Ntziachristos V. Fast raster-scan optoacoustic mesoscopy enables assessment of human melanoma microvasculature in vivo. Nat Commun. 2022;13(1):2803. doi:10.1038/s41467-022-30471-9",
 "He H. Fast raster-scan optoacoustic mesoscopy enables assessment of human melanoma microvasculature in vivo [dataset]. Zenodo; 2022. doi:10.5281/zenodo.6466446",
 "Lin L, Hu P, Tong X, Na S, Cao R, Yuan X, Garrett DC, Shi J, Maslov K, Wang LV. High-speed three-dimensional photoacoustic computed tomography for preclinical research and clinical translation. Nat Commun. 2021;12(1):882. doi:10.1038/s41467-021-21232-1",
 "Tong X. 3D-PACT data and codes [dataset]. Figshare; 2020. doi:10.6084/m9.figshare.13114544",
 "Rodriguez-Molares A, Rindal OMH, D'hooge J, M\u00e5s\u00f8y SE, Austeng A, Lediju Bell MA, Torp H. The generalized contrast-to-noise ratio: a formal definition for lesion detectability. IEEE Trans Ultrason Ferroelectr Freq Control. 2020;67(4):745\u2013759. doi:10.1109/TUFFC.2019.2956855",
 "Xu Y, Wang LV, Ambartsoumian G, Kuchment P. Reconstructions in limited-view thermoacoustic tomography. Med Phys. 2004;31(4):724\u2013733. doi:10.1118/1.1644531",
 "Pramanik M. Improving tangential resolution with a modified delay-and-sum reconstruction algorithm in photoacoustic and thermoacoustic tomography. J Opt Soc Am A. 2014;31(3):621\u2013627. doi:10.1364/JOSAA.31.000621",
 "Rosenthal A, Razansky D, Ntziachristos V. Fast semi-analytical model-based acoustic inversion for quantitative optoacoustic tomography. IEEE Trans Med Imaging. 2010;29(6):1275\u20131285. doi:10.1109/TMI.2010.2044584",
 "Treeby BE, Cox BT. k-Wave: MATLAB toolbox for the simulation and reconstruction of photoacoustic wave fields. J Biomed Opt. 2010;15(2):021314. doi:10.1117/1.3360308",
 "Gr\u00f6hl J, Schellenberg M, Dreher K, Maier-Hein L. Deep learning for biomedical photoacoustic imaging: a review. Photoacoustics. 2021;22:100241. doi:10.1016/j.pacs.2021.100241",
 "Yang C, Lan H, Gao H, Gao F, Fei D. A review of deep learning for photoacoustic imaging. Photoacoustics. 2021;21:100215. doi:10.1016/j.pacs.2020.100215",
 "Zhang J, Lan H, Yang C, Lyu T, Guo S, Gao F, Gao F. Limited-view photoacoustic imaging reconstruction with dual domain inputs based on mutual information constraint. In: 2021 IEEE Int Symp Biomed Imaging (ISBI). Piscataway: IEEE; 2021. p. 1522\u20131526. doi:10.1109/ISBI48211.2021.9433949",
 "Omar M, Aguirre J, Ntziachristos V. Optoacoustic mesoscopy for biomedicine. Nat Biomed Eng. 2019;3(5):354\u2013370. doi:10.1038/s41551-019-0377-4",
 "Ozdemir F, Lafci B, De\u00e1n-Ben XL, Razansky D, P\u00e9rez-Cruz F. OADAT: Experimental and Synthetic Clinical Optoacoustic Data for Standardized Image Processing. Trans Mach Learn Res. 2023. arXiv:2206.08612. Evaluated for inclusion and excluded from this work (array geometry not reconcilable with the released metadata).",
]

REFS_HEAD = (
 "**Formal reference list**, numbered in order of first appearance. Citation markers in the text are "
 "bracketed numerals `[n]` (Elsevier \"number\" style); superscripts are not used because the DOCX "
 "pipeline of this project has no inline-superscript path. Entries are reproduced from "
 "`paper/refs/refs.bib`, which remains the single source of truth; every record was checked against the "
 "publisher or repository record (the four former `TODO: verify` markers were resolved 2026-10-14).\n\n"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    t = io.open(MD, "r", encoding="utf-8").read()

    if re.search(r"\n1\. Beard P\. Biomedical photoacoustic imaging", t):
        print("ALREADY APPLIED: the numbered reference list is present. Nothing to do.")
        return 0

    # ---- 1) 锚点插入 ----
    report, bad = [], []
    for anchor, repl in EDITS:
        n = t.count(anchor)
        if n != 1:
            bad.append((anchor[:70], n))
            continue
        t = t.replace(anchor, repl)
        report.append("ok   %-72s" % anchor[:72])

    if bad:
        print("!! ANCHOR MISMATCH (no write):")
        for s, n in bad:
            print("   x%-2d %s" % (n, s))
        return 2

    # ---- 2) References 段重建 ----
    start = t.find("Bibliography: **`paper/refs/refs.bib`**")
    if start < 0:
        print("!! References scaffold not found (no write).")
        return 2
    m = re.search(r"\n\n## (Appendix|Declarations|Figure captions|Table captions|Open items)", t[start:])
    end = start + (m.start() if m else len(t) - start)

    body = REFS_HEAD + "\n".join("%d. %s" % (i + 1, r) for i, r in enumerate(REFS)) + "\n"
    t = t[:start] + body + t[end:]

    print("anchors inserted : %d / %d" % (len(report), len(EDITS)))
    print("reference list   : %d entries" % len(REFS))
    print("section replaced : %d chars -> %d chars" % (end - start, len(body)))

    if a.check:
        print("\n[--check] not written.")
        return 0

    with io.open(MD, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(t)
    print("\n[out] %s" % MD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
