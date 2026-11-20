#!/usr/bin/env python3
"""级别判定：校定指南优先 + 中科院/JCR 补位。

等级序：A+ > A > A- > B+ > B > C > 不认定
B+ 为自建档（JCR Q1），正式上报时按 B 记。

用法：
    python3 classify.py --venue "Automatica" --cas 2 --jcr Q1 --indexed
    python3 classify.py --self-test
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GUIDE = os.path.join(HERE, '..', 'data', 'zuel-guide.json')


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


def load_guide(path=GUIDE):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def guide_lookup(guide, venue, issn=None):
    if issn:
        code = re.sub(r'[^0-9X]', '', issn.upper())
        for g in guide:
            if g.get('lang') == 'en' and re.sub(r'[^0-9X]', '', (g.get('cn') or '').upper()) == code:
                return g
    key = norm(venue)
    if not key:
        return None
    for g in guide:
        if g.get('lang') == 'zh' and norm(g.get('title')) == key:
            return g
    return None


def classify(venue, cas=None, jcr=None, warning=False, indexed=False, guide=None, issn=None):
    if warning:
        return '剔除', '预警名单（指南第七条，高于一切）'
    hit = guide_lookup(guide or [], venue, issn)
    if hit:
        return hit['level'], '校定指南列出（%s）' % (hit.get('section') or '附录')
    if cas == 1:
        return 'A', '中科院 1 区'
    if (jcr or '').upper() == 'Q1':
        return 'B+', 'JCR Q1（自建档，可报 B）'
    if cas == 2:
        return 'B', '中科院 2 区（封顶 B）'
    if indexed:
        return 'C', '索引收录但未达 1/2 区且非 Q1'
    return '不认定', '未被指南列出且未达索引门槛'


def self_test():
    guide = [{'lang': 'en', 'cn': '0893-9454', 'level': 'A+', 'section': '英文 A+级期刊',
              'title': 'REVIEW OF FINANCIAL STUDIES'}]
    cases = [
        (dict(venue='Automatica', cas=2, jcr='Q1', indexed=True), 'B+'),
        (dict(venue='Journal X', cas=1, jcr='Q4', indexed=True), 'A'),
        (dict(venue='Journal Y', cas=3, jcr='Q1', indexed=True), 'B+'),
        (dict(venue='Journal Z', cas=4, jcr='Q2', indexed=True), 'C'),
        (dict(venue='Journal W', cas=None, jcr=None, indexed=False), '不认定'),
        (dict(venue='Review of Financial Studies', issn='0893-9454', cas=1, jcr='Q1'), 'A+'),
        (dict(venue='Predatory', cas=1, jcr='Q1', warning=True), '剔除'),
    ]
    ok = True
    for kwargs, expect in cases:
        got, why = classify(guide=guide, **kwargs)
        if got != expect:
            ok = False
        print('%s %-26s expect=%-4s got=%-4s (%s)' % ('OK ' if got == expect else 'FAIL', kwargs.get('venue'), expect, got, why))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--venue', default='')
    ap.add_argument('--issn', default=None)
    ap.add_argument('--cas', type=int, default=None)
    ap.add_argument('--jcr', default=None)
    ap.add_argument('--warning', action='store_true')
    ap.add_argument('--indexed', action='store_true')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        sys.exit(self_test())
    level, why = classify(args.venue, args.cas, args.jcr, args.warning, args.indexed, guide=load_guide(), issn=args.issn)
    print(json.dumps({'venue': args.venue, 'level': level, 'reason': why}, ensure_ascii=False))


if __name__ == '__main__':
    main()
