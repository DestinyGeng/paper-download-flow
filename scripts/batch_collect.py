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
from concurrent.futures import ThreadPoolExecutor, as_completed

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
FROM_YEAR = 2016  # 默认起始年；可用 --years 或 PAPER_YEARS 覆盖
MAX_PAGES = 3


def _from_year():
    """按 --years / PAPER_YEARS 计算起始年份（0 或不设则用 FROM_YEAR）。"""
    import datetime
    n = int(os.environ.get('PAPER_YEARS') or 0)
    if n <= 0:
        return FROM_YEAR
    return datetime.date.today().year - n + 1


OPENALEX_KEY = os.environ.get('OPENALEX_API_KEY') or ''


def http_json(url, tries=4):
    if OPENALEX_KEY:
        url += ('&' if '?' in url else '?') + 'api_key=' + urllib.parse.quote(OPENALEX_KEY)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=90))
        except Exception as exc:
            wait = 3 * (i + 1)
            msg = str(exc)
            if '429' in msg:
                if i == 0:
                    print('! OpenAlex 配额已用尽（共享 IP 免费额度）。'
                          '设置环境变量 OPENALEX_API_KEY 可继续，或等 UTC 零点重置。', flush=True)
                return None
            if 'timed out' in msg or isinstance(exc, json.decoder.JSONDecodeError):
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
                   + '&filter=from_publication_date:%d-01-01' % _from_year()
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


STOP = set('''a an and are as at be been by for from has have in into is it its of on or
such that the their this to was were will with we our us you your'''.split())

QUERY_TERMS = []   # 每条查询自己的主题词（分开算分，避免跨查询串味）
ANCHORS = []       # 领域锚词：不出现就判定为跑题（可选）


def set_anchor(words):
    """锚词，例如 stock,equity,market,volatility；空则不启用。"""
    global ANCHORS
    ANCHORS = [w.strip().lower() for w in words if w.strip()]
    return ANCHORS


def set_topic(queries):
    """从查询词里抽主题词。原来写死成配对交易关键词，换个题目就全被过滤成 0。"""
    global QUERY_TERMS
    QUERY_TERMS = []
    for q in queries:
        ws = [w.strip('-') for w in re.findall(r"[a-z][a-z0-9\-]{2,}", q.lower())]
        QUERY_TERMS.append([w for w in ws if w and w not in STOP])
    return sorted({w for ws in QUERY_TERMS for w in ws})


def _hits(terms, title, blob):
    s = 0
    for w in terms:
        pat = r'\b' + re.escape(w)
        if re.search(pat, title):
            s += 2
        elif re.search(pat, blob):
            s += 1
    return s


def related(p):
    """按单条查询各自算分取最大值；有锚词时锚词缺席直接判 0。"""
    title = (p.get('title') or '').lower()
    blob = title + ' ' + (p.get('abstract') or '').lower()
    if ANCHORS and not any(re.search(r'\b' + re.escape(a), blob) for a in ANCHORS):
        return 0
    return max((_hits(t, title, blob) for t in QUERY_TERMS), default=0)


def emit(stage, done, total, msg=''):
    """给 GUI 的进度行；run.py 解析这个前缀更新进度条。"""
    print('##PROGRESS## ' + json.dumps(
        {'stage': stage, 'done': done, 'total': total, 'msg': msg}, ensure_ascii=False), flush=True)


# 这些站点的"直链"几乎都要过验证/登录，别浪费 60 秒，直接列为人工下载
MANUAL_HOSTS = ('sciencedirect.com', 'wiley.com', 'onlinelibrary.wiley.com', 'springer.com',
                'link.springer.com', 'tandfonline.com', 'jstor.org', 'sagepub.com', 'oup.com',
                'cambridge.org', 'emerald.com', 'cnki.net', 'ssrn.com', 'aeaweb.org',
                'nber.org', 'journals.uchicago.edu', 'annualreviews.org')


def _is_manual_url(url):
    return any(h in (url or '').lower() for h in MANUAL_HOSTS)


def download(p, outdir, timeout=15):
    url = p.get('oa_pdf')
    if not url:
        return None, 'no_oa_url'
    if _is_manual_url(url):
        return None, 'needs_manual'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (research)'})
        resp = urllib.request.urlopen(req, timeout=timeout)
        final = resp.geturl()
        data = resp.read()
    except Exception as exc:
        msg = str(exc)
        if '403' in msg or '401' in msg or _is_manual_url(url):
            return None, 'needs_manual'
        return None, 'fetch_failed:%s' % msg[:40]
    if _is_manual_url(final):
        return None, 'needs_manual'
    if data[:4] != b'%PDF':
        head = data[:2000].lower()
        if any(k in head for k in (b'login', b'verify', b'captcha', b'access denied', b'sign in')):
            return None, 'needs_manual'
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


def write_manual(items, outdir):
    """需要登录/验证码的条目：生成清单，交给人工在浏览器里下。"""
    path = os.path.join(outdir, '待人工下载.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('# 待人工下载（需要登录 / 验证码）\n\n')
        f.write('共 %d 篇。用浏览器打开下面的链接，通过学校 VPN 登录后下载，'
                '把 PDF 放进本目录即可。\n\n' % len(items))
        f.write('| # | 年份 | 标题 | 期刊 | DOI | 链接 |\n|---|---|---|---|---|---|\n')
        for i, p in enumerate(items, 1):
            t = (p.get('title') or '').replace('|', '/')[:90]
            j = (p.get('venue') or '').replace('|', '/')[:40]
            link = p.get('landing') or p.get('oa_pdf') or ''
            f.write('| %d | %s | %s | %s | %s | %s |\n' % (
                i, p.get('year') or '', t, j, p.get('doi') or '', link))
    print('需人工下载：%d 篇 → %s' % (len(items), path), flush=True)


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
    ap.add_argument('--years', type=int, default=0, help='最近 N 年（0=不限）')
    ap.add_argument('--pages', type=int, default=MAX_PAGES)
    ap.add_argument('--queries-file', default='')
    ap.add_argument('--anchor', default='', help='领域锚词，逗号分隔：不出现即判跑题')
    ap.add_argument('--min-score', type=int, default=2, help='相关性最低分')
    args = ap.parse_args()
    if args.years:
        os.environ['PAPER_YEARS'] = str(args.years)
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
    set_anchor(args.anchor.split(','))
    print('topic terms:', ', '.join(set_topic(queries)), flush=True)
    if ANCHORS:
        print('anchors:', ', '.join(ANCHORS), flush=True)
    papers = collect(queries, args.per_page, args.pages)
    print('collected %d unique' % len(papers), flush=True)

    pool = len(papers)
    papers = [p for p in papers if related(p) >= args.min_score]
    papers.sort(key=lambda p: (-(p.get('cites') or 0)))
    papers = papers[:args.target]
    emit('filter', len(papers), pool, '从 %d 条候选中筛出 %d 条（目标上限 %d）' % (
        pool, len(papers), args.target))
    print('检索池 %d 条 → 相关性筛选后 %d 条（阈值 %d%s，下载上限 %d）' % (
        pool, len(papers), args.min_score,
        '，锚词 ' + '/'.join(ANCHORS) if ANCHORS else '', args.target), flush=True)

    grader = Grader()
    stats = {'downloaded': 0, 'dup': 0, 'fail': 0, 'no_oa': 0, 'needs_manual': 0}
    manual = []
    todo = []
    for p in papers:
        if p.get('doi') and p['doi'] in done_doi:
            stats['dup'] += 1
            continue
        lvl, src = grader.level(p.get('doi'), p.get('issn'), p.get('title'))
        p['level'] = lvl
        p['level_source'] = src
        todo.append(p)

    # 4 路并发 + 15 秒超时：单篇卡住不会拖死整个流程
    emit('download', 0, len(todo), '准备下载 %d 篇' % len(todo))
    results = {}
    if todo:
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(download, p, outdir): p for p in todo}
            for i, f in enumerate(as_completed(futs), 1):
                p = futs[f]
                try:
                    res, err = f.result()
                except Exception as exc:
                    res, err = None, 'worker:%s' % str(exc)[:40]
                results[id(p)] = (res, err)
                emit('download', i, len(todo), (p.get('title') or '')[:60])

    for p in todo:
        res, err = results.get(id(p), (None, 'missing'))
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
            if err == 'no_oa_url':
                stats['no_oa'] += 1
            elif err == 'needs_manual':
                stats['needs_manual'] += 1
                manual.append(p)
            else:
                stats['fail'] += 1
        state.append(p)
        if p.get('doi'):
            done_doi.add(p['doi'])
    # 按 DOI + 标题去重（跨来源合并后可能同一篇出现两次）
    def _k(x):
        doi = (x.get('doi') or '').strip().lower()
        return doi or norm_title(x.get('title'))

    seen_k, uniq = set(), []
    for x in state:
        k = _k(x)
        if k and k in seen_k:
            continue
        seen_k.add(k)
        uniq.append(x)
    state = uniq
    json.dump(state, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    if manual:
        write_manual(manual, outdir)
    write_report(state, outdir)
    emit('done', 1, 1, '下载完成 %d 成功 / %d 需人工 / %d 无OA' % (
        stats['downloaded'], stats['needs_manual'], stats['no_oa']))
    print('DONE', stats, flush=True)


if __name__ == '__main__':
    main()