#!/usr/bin/env python3
"""Semantic Scholar 检索：补充 OpenAlex 的覆盖（免费 API，无需 key）。"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import D

META = os.path.join(D, 'metadata.json')
API = 'https://api.semanticscholar.org/graph/v1/paper/search'
FIELDS = 'title,year,citationCount,externalIds,venue,abstract,openAccessPdf,authors'
LOG = '/tmp/s2.log'


def log(m):
    line = time.strftime('%H:%M:%S ') + m
    print(line, flush=True)
    open(LOG, 'a', encoding='utf-8').write(line + '\n')


def search(q, limit=100):
    u = API + '?' + urllib.parse.urlencode({'query': q, 'fields': FIELDS, 'limit': limit})
    for attempt in range(5):
        try:
            hdr = {'User-Agent': 'paper-download-flow/1.2'}
            key = os.environ.get('S2_API_KEY')
            if key:
                hdr['x-api-key'] = key
            req = urllib.request.Request(u, headers=hdr)
            d = json.load(urllib.request.urlopen(req, timeout=40))
            return d.get('data') or []
        except Exception as exc:
            wait = 15 * (attempt + 1)
            log('  重试 %d: %s' % (attempt + 1, str(exc)[:50]))
            time.sleep(wait)
    return []


def rec(r):
    ext = r.get('externalIds') or {}
    doi = (ext.get('DOI') or '').lower()
    oa = r.get('openAccessPdf') or {}
    return {
        'title': r.get('title'),
        'year': r.get('year'),
        'cites': r.get('citationCount') or 0,
        'doi': doi or None,
        'venue': r.get('venue'),
        'abstract': (r.get('abstract') or '')[:1200],
        'oa': oa.get('url'),
        'source': 's2',
    }


def main():
    queries = []
    if '--queries-file' in sys.argv:
        f = sys.argv[sys.argv.index('--queries-file') + 1]
        if os.path.exists(f):
            queries = [x.strip() for x in open(f, encoding='utf-8') if x.strip()]
    if not queries:
        queries = ['pairs trading', 'statistical arbitrage', 'copula pairs trading']
    meta = json.load(open(META, encoding='utf-8'))
    have = {(x.get('doi') or '').lower() for x in meta if x.get('doi')}
    have_titles = {(x.get('title') or '').lower()[:40] for x in meta}
    added = 0
    for q in queries:
        rows = search(q)
        log('%s -> %d 条' % (q, len(rows)))
        for r in rows:
            x = rec(r)
            if not x['title']:
                continue
            if x['doi'] and x['doi'] in have:
                continue
            if x['title'].lower()[:40] in have_titles:
                continue
            meta.append({
                'title': x['title'], 'year': x['year'], 'doi': x['doi'], 'venue': x['venue'],
                'cites': x['cites'], 'abstract': x['abstract'], 'oa': x['oa'],
                'lang': 'en', 'download': 'not_requested', 'source': 's2',
                'level': None, 'level_source': 's2', 'final_level': None, 'final_source': 's2',
            })
            have_titles.add(x['title'].lower()[:40])
            added += 1
        time.sleep(1.2)
    json.dump(meta, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log('新增 %d 条，总计 %d' % (added, len(meta)))


if __name__ == '__main__':
    main()