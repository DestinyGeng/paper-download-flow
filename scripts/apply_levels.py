#!/usr/bin/env python3
"""把 ablesci 核验结果合并进 metadata，重算 final_level。"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUT = '/Users/ligenghao/Downloads/中南/自用论文2/论文'
META = os.path.join(OUT, 'metadata.json')
VER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'journal-verification.json')
KEEP = ('A+', 'A', 'A-', 'B+', 'B')


def norm_issn(s):
    return re.sub(r'[^0-9X]', '', (s or '').upper())


def lookup(ver, rec):
    for key in (rec.get('issn'), 'name:' + (rec.get('venue') or '')):
        if key and key in ver:
            return ver[key]
    code = norm_issn(rec.get('issn'))
    if code:
        for k, v in ver.items():
            if not k.startswith('name:') and norm_issn(k) == code:
                return v
    return {}


def grade(ver, rec):
    if not rec.get('issn') and not rec.get('venue'):
        return '未定', 'no_metadata'
    lv = rec.get('level')
    if lv in KEEP:
        return lv, 'guide'
    info = lookup(ver, rec)
    if info.get('found'):
        jcr = (info.get('jcr') or [None])[0]
        zone = info.get('zone') or ''
        if zone == '1区':
            return 'A', 'zone1'
        if jcr == 'Q1':
            return 'B+', 'jcr_q1'
        if zone == '2区':
            return 'B', 'zone2'
        return 'C', 'weak'
    return 'C', 'unverified'


def main():
    from collections import Counter
    meta = json.load(open(META, encoding='utf-8'))
    ver = json.load(open(VER, encoding='utf-8')) if os.path.exists(VER) else {}
    for rec in meta:
        lv, src = grade(ver, rec)
        rec['final_level'] = lv
        rec['final_source'] = src
    json.dump(meta, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    c = Counter(r['final_level'] for r in meta if (r.get('download') or '').startswith('ok'))
    print('定级完成:', dict(c))


if __name__ == '__main__':
    main()