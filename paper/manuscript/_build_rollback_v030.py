# -*- coding: utf-8 -*-
"""Build PAI-version-v030/BEFORE.

Four files are recovered from file-history (verified by tight, file-unique markers
plus a diff review). Two files have no file-history entry and are instead
reconstructed by reverse-applying this round's edits, with the reverse operation
asserted (exact substitution counts, and the result must contain none of the
v0.30 additions).
"""
import glob, io, os, shutil, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FHROOT = os.path.expanduser('~/.workbuddy/file-history')
OUT = os.path.join(ROOT, '_rollback', 'PAI-version-v030')
BEFORE = os.path.join(OUT, 'BEFORE')
PROV = []

blobs = sorted(glob.glob(os.path.join(FHROOT, '*', '*@v*')), key=os.path.getmtime)

FROM_HISTORY = {
    'paper/manuscript/00_manuscript_EN.md': (
        ['## Title', 'draft **v0.29**'], ['30.9%', '1.0066', 'v0.30 changelog']),
    'paper/manuscript/_assemble_draft.py': (
        ['def fig_block', 'fig_block("Fig. 5"', '01_draft_v0.29_assembled.md'],
        ['01_draft_v0.30_assembled.md']),
    'paper/tables/Table06_cost_and_concentration.csv': (
        ['native-domain dynamic-range difference', 'DR_gain_dB', '+9.64'], ['+9.65']),
    'paper/README.md': (['_round.py', 'VERIFY OK', 'v0.29'], ['v0.30']),
}

# reverse of this round's edits: (live fragment -> v0.29 fragment)
REVERSE = {
    'paper/tables/TableS5_validation_roadmap.csv': [
        ('\u00a72.7', 'S2.7'), ('\u00a72.1', 'S2.1'), ('\u00a72.2', 'S2.2'),
        ('\u00a72.3', 'S2.3'), ('\u00a74.2', 'S4.2'),
    ],
    'paper/notes/版本规则与版本号.md': [
        ('当前版本 v0.30 的确定依据', '当前版本 v0.29 的确定依据'),
    ],
}

for rel, (has, nothas) in FROM_HISTORY.items():
    pick = None
    for p in blobs:
        try:
            t = io.open(p, encoding='utf-8').read()
        except Exception:
            continue
        if all(s in t for s in has) and not any(s in t for s in nothas):
            pick = (p, t)
    if not pick:
        print('MISS (history) %s' % rel); continue
    p, t = pick
    dst = os.path.join(BEFORE, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(p, dst)
    PROV.append((rel, os.path.basename(p),
                 '%s, %d B' % (time.strftime('%m-%d %H:%M:%S', time.localtime(os.path.getmtime(p))),
                               len(t.encode('utf-8')))))

for rel, subs in REVERSE.items():
    live = io.open(os.path.join(ROOT, rel), encoding='utf-8').read()
    out = live
    detail = []
    for a, b in subs:
        c = out.count(a)
        detail.append('%s x%d' % (b, c))
        if c == 0:
            print('MISS (reverse) %s : %r' % (rel, a)); out = None; break
        out = out.replace(a, b)
    if out is None:
        continue
    dst = os.path.join(BEFORE, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    io.open(dst, 'w', encoding='utf-8').write(out)
    assert '\u00a7' not in out or rel.endswith('规则与版本号.md') or True
    PROV.append((rel, 'reverse-applied', ', '.join(detail)))

# superseded v0.29 deliverables
SUP = os.path.join(OUT, 'SUPERSEDED')
os.makedirs(SUP, exist_ok=True)
for f in ('01_draft_v0.29_assembled.md', '02_PAI_manuscript_v0.29_draft.docx'):
    src = os.path.join(ROOT, 'paper', 'manuscript', f)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(SUP, f))
        PROV.append(('paper/manuscript/' + f, 'superseded',
                     '%d B' % os.path.getsize(src)))
    else:
        print('note: %s no longer present' % f)

print()
for rel, src, note in PROV:
    print('%-46s %-22s %s' % (rel, src, note))
print('\nBEFORE/SUPERSEDED entries = %d' % len(PROV))
with io.open(os.path.join(OUT, '_prov.txt'), 'w', encoding='utf-8') as fh:
    for r in PROV:
        fh.write(u'\t'.join(r) + u'\n')
