# -*- coding: utf-8 -*-
"""v0.44: resolve reference placeholders and renumber the whole list by first appearance.

The mother manuscript cites nine new references as ``[{GAMMELL}]`` and the rest
by number.  This script

  1. finds every citation group outside math (math is protected by splitting on
     ``$``, so ``$\\mu\\in[0,1]$`` is never read as a citation),
  2. orders all cited keys by first appearance and assigns 1..N,
  3. rewrites each group, compressing runs of three or more into an en dash,
  4. rebuilds the reference list in the new order with the new entries inserted.

It asserts that every reference is cited at least once, that the mapping is
contiguous, and that the new list has the expected length.
"""
import io
import re
import sys

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.abspath(os.path.join(_HERE, '00_manuscript_EN.md')).replace(os.sep, '/')

s = io.open(P, encoding="utf-8").read()

NEW = {
    "RICE": "Rice SO. Mathematical analysis of random noise. Bell Syst Tech J. 1945;24(1):46–156. "
            "doi:10.1002/j.1538-7305.1945.tb00453.x",
    "URKOWITZ": "Urkowitz H. Energy detection of unknown deterministic signals. Proc IEEE. "
                "1967;55(4):523–531. doi:10.1109/PROC.1967.5573",
    "ZHOUM": "Zhou Y, Yao J, Wang LV. Tutorial on photoacoustic tomography. J Biomed Opt. "
             "2016;21(6):061007. doi:10.1117/1.JBO.21.6.061007",
    "WANGYAO": "Wang LV, Yao J. A practical guide to photoacoustic tomography in the life sciences. "
               "Nat Methods. 2016;13(8):627–638. doi:10.1038/nmeth.3925",
    "PATATOJOSS": "Else TR, Gröhl J, Hacker L, Bohndiek SE. PATATO: a Python photoacoustic tomography "
                  "analysis toolkit. J Open Source Softw. 2024;9(93):5686. doi:10.21105/joss.05686",
    "XU2003": "Xu M, Wang LV. Analytic explanation of spatial resolution related to bandwidth and detector "
              "aperture size in thermoacoustic or photoacoustic reconstruction. Phys Rev E. "
              "2003;67(5):056605. doi:10.1103/PhysRevE.67.056605",
    "HALTMEIER": "Haltmeier M, Zangerl G. Spatial resolution in photoacoustic tomography: effects of detector "
                 "size and detector bandwidth. Inverse Probl. 2010;26(12):125002. "
                 "doi:10.1088/0266-5611/26/12/125002",
    "METZ": "Metz CE. Basic principles of ROC analysis. Semin Nucl Med. 1978;8(4):283–298. "
            "doi:10.1016/S0001-2998(78)80014-2",
    "DAVID": "David HA, Nagaraja HN. Order Statistics. 3rd ed. Hoboken, NJ: John Wiley & Sons; 2003. "
             "doi:10.1002/0471722162",
    "KEMPSKI": "Kempski KM, Graham MT, Gubbi MR, Palmer TJ, Lediju Bell MA. Application of the generalized "
               "contrast-to-noise ratio to assess photoacoustic image quality. Biomed Opt Express. "
               "2020;11(7):3684. doi:10.1364/BOE.391026",
    "GUBBI": "Gubbi MR, Gonzalez EA, Lediju Bell MA. Theoretical framework to predict generalized "
             "contrast-to-noise ratios of photoacoustic images with applications to computer vision. IEEE "
             "Trans Ultrason Ferroelectr Freq Control. 2022;69(6):2098–2114. doi:10.1109/TUFFC.2022.3169082",
    "MOZAFFAR": "Mozaffarzadeh M, Yan Y, Mehrmohammadi M, Makkiabadi B. Enhanced linear-array photoacoustic "
                "beamforming using modified coherence factor. J Biomed Opt. 2018;23(2):026005. "
                "doi:10.1117/1.JBO.23.2.026005",
    "JESPERSEN": "Jespersen SK, Wilhjelm JE, Sillesen H. Multi-angle compound imaging. Ultrason Imaging. "
                 "1998;20(2):81–102. doi:10.1177/016173469802000201",
}

i_refs = s.find("## References")
i_end = s.find("## Figure captions (draft)")
assert i_refs > 0 and i_end > i_refs, "reference block anchors not found"
body, refs, tail = s[:i_refs], s[i_refs:i_end], s[i_end:]

# ---- parse the existing list -------------------------------------------------
old = {}
for line in refs.splitlines():
    m = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
    if m:
        old[int(m.group(1))] = m.group(2).strip()
assert sorted(old) == list(range(1, len(old) + 1)), "existing reference list is not contiguous"
NOLD = len(old)

# ---- find citation groups outside math --------------------------------------
ITEM = re.compile(r"^(\d+)(?:\s*[–-]\s*(\d+))?$")
PH = re.compile(r"^\{([A-Z][A-Z0-9]*)\}$")


def parse(inner):
    keys = []
    for part in [p.strip() for p in inner.split(",")]:
        if not part:
            return None
        mp = PH.match(part)
        if mp:
            if mp.group(1) not in NEW:
                return None
            keys.append(mp.group(1))
            continue
        mi = ITEM.match(part)
        if mi:
            a = int(mi.group(1))
            b = int(mi.group(2)) if mi.group(2) else a
            if a < 1 or b > NOLD or b < a:
                return None
            keys.extend(range(a, b + 1))
            continue
        return None
    return keys or None


segments = body.split("$")
offsets, acc = [], 0
for seg in segments:
    offsets.append(acc)
    acc += len(seg) + 1

groups = []
for i, seg in enumerate(segments):
    if i % 2:                      # odd segment = inside math
        continue
    for m in re.finditer(r"\[([^\[\]]+)\]", seg):
        keys = parse(m.group(1))
        if keys:
            groups.append((offsets[i] + m.start(), offsets[i] + m.end(), keys))
assert groups, "no citation groups found"

# ---- order by first appearance ----------------------------------------------
order = []
for _, _, keys in groups:
    for k in keys:
        if k not in order:
            order.append(k)
num = {k: i + 1 for i, k in enumerate(order)}
N = len(order)

missing = [k for k in range(1, NOLD + 1) if k not in num]
assert not missing, "reference(s) never cited: %s" % missing
assert N == NOLD + len(NEW), "expected %d references, mapped %d" % (NOLD + len(NEW), N)


def render(nums):
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:
            out.append("%d–%d" % (nums[i], nums[j]))
        else:
            out.extend(str(n) for n in nums[i:j + 1])
        i = j + 1
    return "[" + ",".join(out) + "]"


# ---- rewrite body (descending offsets so earlier ones stay valid) -----------
newbody = body
for start, end, keys in sorted(groups, key=lambda g: -g[0]):
    newbody = newbody[:start] + render([num[k] for k in keys]) + newbody[end:]

# ---- rebuild the list --------------------------------------------------------
m_first = re.search(r"^\d+\.\s", refs, re.M)
assert m_first, "no numbered entries found"
intro = refs[:m_first.start()].rstrip()
lines = ["%d. %s" % (num[k], old[k] if isinstance(k, int) else NEW[k]) for k in order]
newrefs = intro + "\n\n" + "\n".join(lines) + "\n\n---\n"

io.open(P, "w", encoding="utf-8", newline="\n").write(newbody + newrefs + tail)

print("references: %d -> %d" % (NOLD, N))
print("mapping (new := old/placeholder):")
print("  " + ", ".join("%d:%s" % (num[k], k) for k in order))
print("citation groups rewritten: %d" % len(groups))
