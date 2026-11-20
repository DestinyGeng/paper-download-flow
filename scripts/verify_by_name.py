#!/usr/bin/env python3
"""用刊名补查 ablesci：针对 ISSN 缺失或 ISSN 查不到的期刊。"""
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
    return json.load(urllib.request.urlopen(PROXY + '/targets', timeout=10))[0]['targetId']


def nav(tid, url):
    try:
        urllib.request.urlopen(PROXY + '/navigate?target=' + tid + '&url=' + urllib.parse.quote(url, safe=''), timeout=50)
    except Exception:
        pass


def readpage(tid, n=3500):
    req = urllib.request.Request(PROXY + '/readPage?target=' + tid,
                                 data=json.dumps({'max_chars': n}).encode(),
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=40)).get('text') or ''


def parse(txt):
    m = re.search(r'总计查询到\s*(\d+)\s*条', txt)
    hits = int(m.group(1)) if m else 0
    jcr = re.findall(r'Q[1-4]', txt)[:3]
    zone = re.search(r'([1-4])区', txt)
    issn = re.search(r'(\d{4})\s*-\s*(\d{3}[\dX])', txt)
    return {'found': hits > 0, 'hits': hits, 'jcr': jcr,
            'zone': (zone.group(1) + '区') if zone else None,
            'matched_issn': (issn.group(1) + '-' + issn.group(2)) if issn else None}


def main():
    meta = json.load(open(META, encoding='utf-8'))
    db = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    todo = []
    for x in meta:
        if x.get('download') != 'ok' or x.get('level_source') == 'guide':
            continue
        key = (x.get('issn') or '').strip()
        venue = (x.get('venue') or '').strip()
        if not venue or venue.startswith('RePEc'):
            continue
        if key and (db.get(key) or {}).get('found'):
            continue
        if venue in [t[1] for t in todo]:
            continue
        todo.append((key, venue))
    print('按刊名补查', len(todo), flush=True)
    tid = target()
    for i, (key, venue) in enumerate(todo, 1):
        nav(tid, 'https://www.ablesci.com/journal/index?keywords=' + urllib.parse.quote(venue))
        time.sleep(4)
        info = parse(readpage(tid))
        info['name'] = venue
        info['query'] = venue
        info['by'] = 'name'
        info['checked_at'] = time.strftime('%Y-%m-%d')
        if key:
            db[key] = info
        db['name:' + venue] = info
        print('  [%d/%d] %-38s found=%-5s jcr=%s zone=%s issn=%s' % (
            i, len(todo), venue[:38], info['found'], ','.join(info['jcr']) or '-',
            info['zone'] or '-', info['matched_issn'] or '-'), flush=True)
        if i % 10 == 0:
            json.dump(db, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(db, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('DONE 补查 %d' % len(todo), flush=True)


if __name__ == '__main__':
    main()
