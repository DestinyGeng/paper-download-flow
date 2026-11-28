#!/usr/bin/env python3
"""把 ablesci 核验结果合并进 metadata，重算 final_level。"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import D as OUT
META = os.path.join(OUT, 'metadata.json')
VER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'journal-verification.json')
GUIDE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'zuel-guide.json')
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


def norm_name(s):
    return re.sub(r'[《》\s　]', '', (s or '').strip())


def load_guide():
    """校定指南：刊名 / 刊号 → 等级。知网条目只有刊名，必须靠这里匹配。"""
    by_name, by_cn = {}, {}
    if not os.path.exists(GUIDE):
        return by_name, by_cn
    for x in json.load(open(GUIDE, encoding='utf-8')):
        lv = x.get('level')
        if not lv:
            continue
        if x.get('title'):
            by_name[norm_name(x['title'])] = lv
        if x.get('cn'):
            by_cn[str(x['cn']).strip()] = lv
    return by_name, by_cn


def grade(ver, rec, by_name=None, by_cn=None):
    if not rec.get('issn') and not rec.get('venue'):
        return '未定', 'no_metadata'
    by_name = by_name or {}
    by_cn = by_cn or {}
    name_hit = by_name.get(norm_name(rec.get('venue')))
    if name_hit:
        return name_hit, 'guide'
    cn_hit = by_cn.get(str(rec.get('cn') or '').strip())
    if cn_hit:
        return cn_hit, 'guide'
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
    return '未定', 'unverified'


def main():
    from collections import Counter
    meta = json.load(open(META, encoding='utf-8'))
    ver = json.load(open(VER, encoding='utf-8')) if os.path.exists(VER) else {}
    by_name, by_cn = load_guide()
    for rec in meta:
        lv, src = grade(ver, rec, by_name, by_cn)
        rec['final_level'] = lv
        rec['final_source'] = src
    json.dump(meta, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    c = Counter(r['final_level'] for r in meta if (r.get('download') or '').startswith('ok'))
    print('定级完成:', dict(c))


if __name__ == '__main__':
    main()