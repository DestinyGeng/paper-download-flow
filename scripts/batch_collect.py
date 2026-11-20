#!/usr/bin/env python3
"""批量采集：OpenAlex 检索 → 相关性筛选 → 定级 → OA 下载 → 查重 → 生成清单。

用法：
    python3 batch_collect.py --target 500 --out ../论文 [--pages 3]

设计：容错优先，任何单篇失败只记录不中断；支持断点续跑（读已有 metadata.json）。
"""
import argparse
import hashlib
import json
import json.decoder
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request

from report import write_report

HERE = os.path.dirname(os.path.abspath(__file__))
GUIDE = os.path.join(HERE, '..', 'data', 'zuel-guide.json')
UA = {'User-Agent': 'academic-search/1.4 (mailto:research@example.org)'}

QUERIES = [
    'copula pairs trading',
    'statistical arbitrage pairs trading',
    'cointegration pairs trading',
    'cross-market arbitrage cointegration',
    'copula dependence trading strategy',
    'pairs trading profitability',
    'high frequency statistical arbitrage',
    'market neutral arbitrage strategy',
    'copula cointegration exchange rate',
    'spread trading machine learning',
]
FROM_YEAR = 2016
MAX_PAGES = 3


def http_json(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=90))
        except Exception as exc:
            wait = 3 * (i + 1)
            msg = str(exc)
            if '429' in msg or 'timed out' in msg or isinstance(exc, json.decoder.JSONDecodeError):
                time.sleep(wait)
                continue
            raise
    return None


def abstract_of(w):
    inv = w.get('abstract_inverted_index') or {}
    if not inv:
        return ''
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return ' '.join(pos[i] for i in sorted(pos))


def norm_title(t):
    return re.sub(r'[^a-z0-9]+', ' ', (t or '').lower()).strip()


def norm_issn(s):
    return re.sub(r'[^0-9X]', '', (s or '').upper())


class Grader:
    def __init__(self, guide_path=GUIDE):
        self.by_issn = {}
        self.by_title = {}
        if os.path.exists(guide_path):
            for g in json.load(open(guide_path, encoding='utf-8')):
                if g.get('lang') == 'en' and g.get('cn'):
                    self.by_issn.setdefault(norm_issn(g['cn']), g['level'])
                elif g.get('lang') == 'zh' and g.get('title'):
                    self.by_title.setdefault(norm_title(g['title']), g['level'])

    def level(self, doi, issn, title):
        if issn and norm_issn(issn) in self.by_issn:
            return self.by_issn[norm_issn(issn)], 'guide'
        if title and norm_title(title) in self.by_title:
            return self.by_title[norm_title(title)], 'guide'
        return None, 'unknown'


def collect(queries, per_page, pages):
    out, seen = [], set()
    for q in queries:
        for page in range(1, pages + 1):
            url = ('https://api.openalex.org/works?search=' + urllib.parse.quote(q)
                   + '&filter=from_publication_date:%d-01-01' % FROM_YEAR
                   + '&per-page=%d&page=%d&mailto=research@example.org' % (per_page, page))
            data = http_json(url)
            if not data:
                break
            for w in data.get('results', []):
                doi = (w.get('doi') or '').replace('https://doi.org/', '') or None
                title = (w.get('title') or '').strip()
                key = doi or norm_title(title)
                if not key or key in seen:
                    continue
                seen.add(key)
                src_ = ((w.get('primary_location') or {}).get('source') or {})
                best = w.get('best_oa_location') or {}
                out.append({
                    'doi': doi,
                    'title': title,
                    'year': w.get('publication_year'),
                    'authors': [a['author']['display_name'] for a in (w.get('authorships') or []) if a.get('author')],
                    'venue': src_.get('display_name'),
                    'issn': src_.get('issn_l'),
                    'type': w.get('type'),
                    'cites': w.get('cited_by_count'),
                    'abstract': abstract_of(w)[:1200],
                    'oa_pdf': best.get('pdf_url') or (w.get('open_access') or {}).get('oa_url'),
                    'landing': (w.get('primary_location') or {}).get('landing_page_url'),
                    'query': q,
                })
            if not data.get('results'):
                break
            time.sleep(0.4)
        print('  query ok: %-40s total=%d' % (q[:40], len(out)), flush=True)
        if len(out) >= per_page * pages * len(queries):
            break
    return out


def related(p):
    blob = ((p.get('title') or '') + ' ' + (p.get('abstract') or '')).lower()
    hit = 0
    for pat, w in [(r'pairs?[- ]trading', 3), (r'copula', 2), (r'cointegrat', 2),
                   (r'statistical arbitrage', 2), (r'cross[- ]market', 2), (r'arbitrage', 1)]:
        if re.search(pat, blob):
            hit += w
    return hit


def download(p, outdir, timeout=60):
    url = p.get('oa_pdf')
    if not url:
        return None, 'no_oa_url'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (research)'})
        data = urllib.request.urlopen(req, timeout=timeout).read()
    except Exception as exc:
        return None, 'fetch_failed:%s' % str(exc)[:40]
    if data[:4] != b'%PDF':
        return None, 'not_pdf'
    if len(data) < 20000:
        return None, 'too_small'
    first = re.sub(r'[^A-Za-z]', '', (p['authors'][0].split()[-1] if p.get('authors') else 'Anon')) or 'Anon'
    words = re.findall(r'[A-Za-z0-9]+', p.get('title') or '')[:4]
    short = ''.join(words) or 'paper'
    name = fname(p.get('title'))
    dest = os.path.join(outdir, name)
    open(dest, 'wb').write(data)
    return {'file': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}, None


def fname(title):
    """文件名 = 标题（去非法字符，截断 80 字）。"""
    t = (title or 'untitled').strip()
    t = re.sub(r'[\\/:*?"<>|\n\r\t]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip(' .')
    return (t[:80] or 'untitled') + '.pdf'



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', type=int, default=500)
    ap.add_argument('--out', default='../论文')
    ap.add_argument('--per-page', type=int, default=50)
    ap.add_argument('--pages', type=int, default=MAX_PAGES)
    ap.add_argument('--queries-file', default='')
    args = ap.parse_args()
    outdir = os.path.abspath(args.out)
    os.makedirs(outdir, exist_ok=True)
    meta_path = os.path.join(outdir, 'metadata.json')
    state = json.load(open(meta_path, encoding='utf-8')) if os.path.exists(meta_path) else []
    done_doi = {x.get('doi') for x in state if x.get('doi')}
    done_sha = {x.get('sha256') for x in state if x.get('sha256')}

    print('collecting...', flush=True)
    queries = QUERIES
    if args.queries_file and os.path.exists(args.queries_file):
        queries = [l.strip() for l in open(args.queries_file, encoding='utf-8') if l.strip()]
    print('queries: %d' % len(queries), flush=True)
    papers = collect(queries, args.per_page, args.pages)
    print('collected %d unique' % len(papers), flush=True)

    papers = [p for p in papers if related(p) >= 3]
    papers.sort(key=lambda p: (-(p.get('cites') or 0)))
    papers = papers[:args.target]
    print('after relevance filter: %d' % len(papers), flush=True)

    grader = Grader()
    stats = {'downloaded': 0, 'dup': 0, 'fail': 0, 'no_oa': 0}
    for i, p in enumerate(papers, 1):
        if p.get('doi') and p['doi'] in done_doi:
            stats['dup'] += 1
            continue
        lvl, src = grader.level(p.get('doi'), p.get('issn'), p.get('title'))
        p['level'] = lvl
        p['level_source'] = src
        if not p.get('oa_pdf'):
            stats['no_oa'] += 1
            p['download'] = 'no_oa_url'
        else:
            res, err = download(p, outdir)
            if res:
                if res['sha256'] in done_sha:
                    os.remove(os.path.join(outdir, res['file']))
                    stats['dup'] += 1
                    p['download'] = 'dup_sha'
                else:
                    done_sha.add(res['sha256'])
                    p['download'] = 'ok'
                    p['file'] = res['file']
                    p['bytes'] = res['bytes']
                    p['sha256'] = res['sha256']
                    stats['downloaded'] += 1
            else:
                p['download'] = err
                stats['fail'] += 1
        state.append(p)
        if p.get('doi'):
            done_doi.add(p['doi'])
        if i % 20 == 0:
            print('  [%d/%d] %s' % (i, len(papers), stats), flush=True)
            json.dump(state, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    json.dump(state, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    write_report(state, outdir)
    print('DONE', stats, flush=True)


if __name__ == '__main__':
    main()