# -*- coding: utf-8 -*-
"""Find the v0.29 versions of the remaining files using markers unique to each."""
import glob, io, os, time

FHROOT = os.path.expanduser('~/.workbuddy/file-history')
blobs = sorted(glob.glob(os.path.join(FHROOT, '*', '*@v*')), key=os.path.getmtime)

TIGHT = {
    'assemble': (['def fig_block', 'fig_block("Fig. 5"', '01_draft_v0.29_assembled.md'],
                 ['01_draft_v0.30_assembled.md']),
    'Table06': (['native-domain dynamic-range difference', 'DR_gain_dB', '+9.64'],
                ['+9.65']),
    'TableS5': (['E4c', 'folding-control', 'raised sampling rate'],
                ['§']),
    'rules': (['当前版本 v0.29 的确定依据', 'MINOR 何时递增'],
              ['v0.30']),
    'README': (['_round.py', 'VERIFY OK', 'v0.29'], ['v0.30']),
}
for tag, (has, nothas) in TIGHT.items():
    print('=== %s ===' % tag)
    n = 0
    for p in blobs:
        try:
            t = io.open(p, encoding='utf-8').read()
        except Exception:
            continue
        if all(s in t for s in has) and not any(s in t for s in nothas):
            n += 1
            print('  %s %7d B  %s' % (time.strftime('%m-%d %H:%M:%S', time.localtime(os.path.getmtime(p))),
                                      len(t.encode('utf-8')), os.path.basename(p)))
    if n == 0:
        print('  (none)')
