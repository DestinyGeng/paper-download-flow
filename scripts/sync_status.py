#!/usr/bin/env python3
"""同步：磁盘 PDF 与 metadata 对齐。只用精确匹配，不猜。"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import D

META = os.path.join(D, 'metadata.json')


def norm(v):
    return re.sub(r'[^0-9a-z\u4e00-\u9fa5]', '', (v or '').lower())


def is_pii(name):
    return bool(re.match(r'(1-s2\.0-|cfri-|hhj\d)', name))


def main():
    meta = json.load(open(META, encoding='utf-8'))
    files = [f for f in os.listdir(D) if f.lower().endswith('.pdf')]
    taken = {x.get('file') for x in meta if x.get('download') == 'ok' and x.get('file')}
    fixed = 0
    for f in files:
        if f in taken or is_pii(f):
            continue
        base = norm(os.path.splitext(f)[0])
        if len(base) < 8:
            continue
        for x in meta:
            if x.get('download') == 'ok':
                continue
            t = norm(x.get('title'))
            if len(t) >= 8 and t[:20] == base[:20]:
                x['download'] = 'ok'
                x['file'] = f
                x['via'] = 'sync'
                x['bytes'] = os.path.getsize(os.path.join(D, f))
                fixed += 1
                break
    if fixed:
        json.dump(meta, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('精确同步：修复 %d 条 | 磁盘 %d 个' % (fixed, len(files)))


if __name__ == '__main__':
    main()
