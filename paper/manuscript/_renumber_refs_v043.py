# -*- coding: utf-8 -*-
"""Resolve reference placeholders and renumber the whole list by first appearance.

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
    "GAMMELL": "Gammell PM. Improved ultrasonic detection using the analytic signal magnitude. "
               "Ultrasonics. 1981;19(2):73–76. doi:10.1016/0041-624X(81)90111-6",
    "NG": "Ng A, Swanevelder J. Resolution in ultrasound imaging. Contin Educ Anaesth Crit Care Pain. "
          "2011;11(5):186–192. doi:10.1093/bjaceaccp/mkr030",
    "VANTREES": "Van Trees HL. Detection, Estimation, and Modulation Theory, Part I. New York: John "
                "Wiley & Sons; 2001. doi:10.1002/0471221082",
    "PIERCE": "Pierce AD. Acoustics: An Introduction to Its Physical Principles and Applications. "
              "3rd ed. Cham: Springer; 2019. doi:10.1007/978-3-030-11214-1",
    "DAHL": "Dahl JJ, Hyun D, Lediju M, Trahey GE. Lesion detectability in diagnostic ultrasound with "
            "short-lag spatial coherence imaging. Ultrason Imaging. 2011;33(2):119–133. "
            "doi:10.1177/016173461103300203",
    "CAMACHO": "Camacho J, Parrilla M, Fritsch C. Phase coherence imaging. IEEE Trans Ultrason "
               "Ferroelectr Freq Control. 2009;56(5):958–974. doi:10.1109/TUFFC.2009.1128",
    "KIRCHNER": "Kirchner T, Sattler F, Gröhl J, Maier-Hein L. Signed real-time delay multiply and "
                "sum beamforming for multispectral photoacoustic imaging. J Imaging. 2018;4(10):121. "
                "doi:10.3390/jimaging4100121",
    "PARK": "Park H, Yao J, Jing Y. A frequency-domain model-based reconstruction method for "
            "transcranial photoacoustic imaging: a 2D numerical investigation. Photoacoustics. "
            "2023;33:100561. doi:10.1016/j.pacs.2023.100561",
    "ORAEVSKY": "Oraevsky AA. Image reconstruction from photoacoustic projections. Photonics "
                "Insights. 2024;3(4):C06. doi:10.3788/PI.2024.C06",
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
PH = re.compile(r"^\{([A-Z]+)\}$")


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
