#!/usr/bin/env python3
"""把 PII/编号命名的 PDF 改成论文标题。

优先用 PDF 元数据 Title；无效则从首页正文提取。
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import D

META = os.path.join(D, 'metadata.json')


def bad_title(t):
    if not t or len(t) < 12:
        return True
    if re.search(r'proof|\d+\.\.\d+|^[A-Z]+-?\d', t, re.I):
        return True
    return False


def clean(t):
    t = re.sub(r'[\\/:*?"<>|\n\r\t]+', ' ', t or '')
    t = re.sub(r'\s+', ' ', t).strip(' .')
    t = re.sub(r'_[一二-龥]{2,4}$', '', t)
    return t[:80]


def title_from_pdfinfo(p):
    try:
        out = subprocess.run(['pdfinfo', p], capture_output=True).stdout.decode('utf-8', 'replace')
        m = re.search(r'^Title:\s*(.+)$', out, re.M)
        return m.group(1).strip() if m else ''
    except Exception:
        return ''


def title_from_text(p):
    try:
        out = subprocess.run(['pdftotext', '-f', '1', '-l', '1', p, '-'],
                             capture_output=True).stdout.decode('utf-8', 'replace')
    except Exception:
        return ''
    lines = [l.strip() for l in out.splitlines() if len(l.strip()) > 15]
    if not lines:
        return ''
    # 取前 8 行里最长的一行（通常是标题）
    cand = max(lines[:8], key=len)
    return cand


def main():
    meta = json.load(open(META, encoding='utf-8'))
    files = [f for f in os.listdir(D) if f.lower().endswith('.pdf')]
    targets = [f for f in files if re.match(r'(1-s2\.0-[A-Z0-9]+-main|cfri-|hhj\d)', f)]
    print('待处理:', len(targets))
    by_doi = {}
    for x in meta:
        if x.get('doi'):
            by_doi[x['doi'].lower()] = x
    done = 0
    for f in targets:
        p = os.path.join(D, f)
        t = title_from_pdfinfo(p)
        src = 'pdfinfo'
        if bad_title(t):
            t2 = title_from_text(p)
            if t2 and not bad_title(t2):
                t = t2
                src = 'text'
        if bad_title(t):
            print('  跳过（提不出标题）:', f[:40], '|', (t or '')[:30])
            continue
        name = clean(t) + '.pdf'
        dst = os.path.join(D, name)
        n = 1
        while os.path.exists(dst) and os.path.abspath(dst) != os.path.abspath(p):
            n += 1
            dst = os.path.join(D, name[:-4] + '_v%d.pdf' % n)
        if os.path.abspath(dst) == os.path.abspath(p):
            continue
        os.replace(p, dst)
        done += 1
        print('  [%s] %s -> %s' % (src, f[:34], os.path.basename(dst)[:44]))
        # 更新 metadata
        for x in meta:
            if x.get('file') == f:
                x['file'] = os.path.basename(dst)
                x['download'] = 'ok'
                x['via'] = 'rename'
                break
    json.dump(meta, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('改了', done, '个')


if __name__ == '__main__':
    main()
