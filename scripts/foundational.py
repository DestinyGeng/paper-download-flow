#!/usr/bin/env python3
"""采集配对交易文献（不限引用），按引用量排序，标记奠基论文。"""
import json
import os
import time
import urllib.parse
import urllib.request

UA = {'User-Agent': 'academic-search/1.4 (mailto:research@example.org)'}
BASE = 'https://api.openalex.org/works'
OUT = '/tmp/foundational.json'
LOG = '/tmp/foundational.log'

QUERIES = ['pairs trading', 'pair trading', 'statistical arbitrage', 'cointegration',
           'copula trading', 'mean reversion', 'relative value arbitrage', 'spread trading',
           'ETF arbitrage', 'cross market arbitrage', 'copula pairs']


def log(m):
    line = time.strftime('%H:%M:%S ') + m
    print(line, flush=True)
    open(LOG, 'a', encoding='utf-8').write(line + '\n')


def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45))


def rec(r, src):
    loc = (r.get('primary_location') or {}).get('source') or {}
    return {'id': r.get('id'), 'doi': (r.get('doi') or '').replace('https://doi.org/', ''),
            'title': r.get('title'), 'year': r.get('publication_year'),
            'cites': r.get('cited_by_count') or 0, 'venue': loc.get('display_name'),
            'issn': loc.get('issn_l'), 'src': src,
            'oa': (r.get('open_access') or {}).get('oa_url')}


def main():
    found = {}
    for q in QUERIES:
        for page in (1, 2):
            u = (BASE + '?filter=title.search:%s&per-page=100&page=%d'
                 '&sort=cited_by_count:desc&mailto=research@example.org') % (urllib.parse.quote(q), page)
            try:
                d = get(u)
            except Exception as exc:
                log('%s p%d ERR %s' % (q, page, str(exc)[:40]))
                break
            n = 0
            for r in d.get('results', []):
                x = rec(r, q)
                if x['id'] not in found:
                    found[x['id']] = x
                    n += 1
            log('%s p%d -> +%d，累计 %d' % (q, page, n, len(found)))
            if len(d.get('results', [])) < 100:
                break
            time.sleep(0.35)
    rows = sorted(found.values(), key=lambda z: -z['cites'])
    json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log('总计 %d 篇 | cites>=100: %d | 50-99: %d | <50: %d' % (
        len(rows), sum(1 for r in rows if r['cites'] >= 100),
        sum(1 for r in rows if 50 <= r['cites'] < 100),
        sum(1 for r in rows if r['cites'] < 50)))


if __name__ == '__main__':
    main()
