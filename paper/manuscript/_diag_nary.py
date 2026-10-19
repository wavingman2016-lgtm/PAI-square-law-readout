# -*- coding: utf-8 -*-
"""诊断：找出渲染为空的 nary 运算符（DOCX 里显示为空框）。

不用正则定位 `\\sum`—— re.escape 在新版Python 会把反斜杠转义成 \\\\，
导致模式匹配不到；直接用 str.find 循环最稳。
"""
import io

BS = chr(92)
TOKENS = ['sum', 'int', 'prod', 'oint', 'bigcup', 'bigcap']

s = io.open('01_draft_v0.19_assembled.md', encoding='utf-8').read()


def match_brace(t, j):
    """返回与 t[j]=='{' 配对的右花括号下标；深度计数，支持嵌套。"""
    depth = 0
    for k in range(j, len(t)):
        if t[k] == '{':
            depth += 1
        elif t[k] == '}':
            depth -= 1
            if depth == 0:
                return k
    return -1


pos = 0
n = 0
while pos < len(s):
    k = s.find(BS, pos)
    if k < 0:
        break
    op = None
    for t in TOKENS:
        if s.startswith(t, k + 1):
            op = t
            break
    if op is None:
        pos = k + 1
        continue
    n += 1
    # 跳到操作数起点
    j = k + 1 + len(op)
    while j < len(s) and s[j] in '_^':
        if s[j + 1:j + 2] == '{':
            m = match_brace(s, j + 1)
            j = (m + 1) if m > 0 else (j + 2)
        else:
            j += 2
    operand = s[j:j + 30].replace('\n', ' ')
    # 判定：操作数是否为"裸单 token"（brace_nary 会包成 {tok}，通常安全）
    kind = 'BRACE' if s[j:j + 1] == '{' else ('CMD' if s[j:j + 1] == BS else 'BARE')
    print('%2d  %-7s %-5s  %r' % (n, op, kind, operand))
    pos = k + 1

print('total nary:', n)
