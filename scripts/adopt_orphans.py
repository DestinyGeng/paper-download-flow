#!/usr/bin/env python3
"""给未登记的 PDF 补评级：按文件名反查 metadata / OpenAlex，再按规则定级。"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUT = '/Users/ligenghao/Downloads/中南/自用论文2/论文'
META = os.path.join(OUT, 'metadata.json')
VER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'journal-verification.json')
UA = {'User-Agent': 'academic-search/1.4 (mailto:research@example.org)'}
KEEP = ('A+', 'A', 'A-', 'B+', 'B')


def clean(name):
    t = name[:-4]
    t = re.sub(r'^1-s2\.0-[A-Z0-9]+-main$', '', t)
    t = re.sub(r'^\d{4}_[A-Za-z]+_', '', t)
    t = re.sub(r'[_-]+', ' ', t)
    return t.strip()


def norm(s):
    return re.sub(r'[^a-z0-9\u4e00-\u9fa5]', '', (s or '').lower())


def grade(ver, rec):
    lv = rec.get('level')
    if lv in KEEP:
        return lv, 'guide'
    info = {}
    for k in (rec.get('issn'), 'name:' + (rec.get('venue') or '')):
        if k and k in ver:
            info = ver[k]
            break
    if info.get('found'):
        z = info.get('zone') or ''
        q = (info.get('jcr') or [None])[0]
        if z == '1区':
            return 'A', 'zone1'
        if q == 'Q1':
            return 'B+', 'q1'
        if z == '2区':
            return 'B', 'zone2'
        return 'C', 'weak'
    return 'C', 'unverified'


def openalex_by_title(title):
    u = ('https://api.openalex.org/works?search=%s&per-page=1&mailto=research@example.org'
         % urllib.parse.quote(title[:120]))
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))
        r = (d.get('results') or [None])[0]
        if not r:
            return None
        return {'title': r.get('title'), 'doi': (r.get('doi') or '').replace('https://doi.org/', ''),
                'year': r.get('publication_year'),
                'venue': ((r.get('primary_location') or {}).get('source') or {}).get('display_name'),
                'issn': ((r.get('primary_location') or {}).get('source') or {}).get('issn_l')}
    except Exception:
        return None


def main():
    meta = json.load(open(META, encoding='utf-8'))
    ver = json.load(open(VER, encoding='utf-8')) if os.path.exists(VER) else {}
    known = {(x.get('file') or '') for x in meta if x.get('download') == 'ok'}
    pdfs = [f for f in os.listdir(OUT) if f.lower().endswith('.pdf') and f not in known]
    by_title = {}
    for x in meta:
        key = norm(x.get('title'))[:60]
        if key:
            by_title.setdefault(key, x)
    result = []
    for f in pdfs:
        t = clean(f)
        key = norm(t)[:60]
        rec = by_title.get(key)
        src = 'meta'
        if not rec:
            for k, v in by_title.items():
                if key and (key[:30] in k or k[:30] in key):
                    rec = v
                    src = 'meta-fuzzy'
                    break
        if not rec:
            rec = openalex_by_title(t)
            src = 'openalex'
            time.sleep(0.5)
        if not rec:
            result.append({'file': f, 'title': t, 'level': '?', 'src': 'none'})
            continue
        lv, why = grade(ver, rec)
        result.append({'file': f, 'title': rec.get('title') or t, 'level': lv, 'src': src,
                       'venue': rec.get('venue'), 'doi': rec.get('doi'), 'why': why})
    json.dump(result, open('/tmp/orphans.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    from collections import Counter
    print('孤儿文件', len(result), '评级:', dict(Counter(r['level'] for r in result)))
    for r in result:
        print('  %-4s %-42s %s' % (r['level'], (r.get('title') or '')[:42], (r.get('venue') or '')[:28]))


if __name__ == '__main__':
    main()
