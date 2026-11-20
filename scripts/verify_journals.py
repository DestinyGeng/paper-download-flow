#!/usr/bin/env python3
"""用 ablesci 核验期刊：查 ISSN → 记录收录/分区；查不到归 C。

输出 data/journal-verification.json：
  { "<issn>": {"name":..., "found":true, "jcr":[...], "zone":"3区", "if":"4.2", "checked_at":...} }
"""
import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request

PROXY = 'http://127.0.0.1:3457'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'data', 'journal-verification.json')
META = '/Users/ligenghao/Downloads/中南/自用论文2/论文/metadata.json'


def target():
    tabs = json.load(urllib.request.urlopen(PROXY + '/targets', timeout=10))
    return tabs[0]['targetId']


def navigate(tid, url):
    try:
        urllib.request.urlopen(PROXY + '/navigate?target=' + tid + '&url=' + urllib.parse.quote(url, safe=''), timeout=50)
    except Exception:
        pass


def readpage(tid, n=4000):
    req = urllib.request.Request(PROXY + '/readPage?target=' + tid,
                                 data=json.dumps({'max_chars': n}).encode(),
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=40)).get('text') or ''


def parse(txt):
    m = re.search(r'总计查询到\s*(\d+)\s*条', txt)
    hits = int(m.group(1)) if m else 0
    jcr = re.findall(r'Q[1-4]', txt)[:3]
    zone = re.search(r'([1-4])区', txt)
    imp = re.search(r'(\d+\.\d+)\s*↑|(\d+\.\d+)\s*↓|^(\d+\.\d+)$', txt, re.M)
    return {'found': hits > 0, 'hits': hits, 'jcr': jcr,
            'zone': (zone.group(1) + '区') if zone else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    meta = json.load(open(META, encoding='utf-8'))
    db = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}

    seen = {}
    for x in meta:
        if x.get('level_source') == 'guide':
            continue
        key = (x.get('issn') or x.get('venue') or '').strip()
        if not key or key in seen or key in db:
            continue
        seen[key] = x.get('venue') or key
    todo = list(seen.items())
    if args.limit:
        todo = todo[:args.limit]
    print('待核验', len(todo), flush=True)

    tid = target()
    for i, (key, name) in enumerate(todo, 1):
        q = key if re.match(r'^\d{4}-?\d{3}[\dX]$', key) else name
        url = 'https://www.ablesci.com/journal/index?keywords=' + urllib.parse.quote(q)
        navigate(tid, url)
        time.sleep(4)
        txt = readpage(tid)
        info = parse(txt)
        info['name'] = name
        info['query'] = q
        info['checked_at'] = time.strftime('%Y-%m-%d')
        db[key] = info
        print('  [%d/%d] %-40s found=%-5s jcr=%s zone=%s' % (
            i, len(todo), name[:40], info['found'], ','.join(info['jcr']) or '-', info['zone'] or '-'), flush=True)
        if i % 10 == 0:
            json.dump(db, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(db, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    found = sum(1 for v in db.values() if v.get('found'))
    print('DONE 已核验 %d，收录 %d，未收录 %d' % (len(db), found, len(db) - found), flush=True)


if __name__ == '__main__':
    main()
