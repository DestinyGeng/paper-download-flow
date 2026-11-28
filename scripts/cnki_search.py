#!/usr/bin/env python3
"""CNKI 批量检索：多关键词 + 北大核心筛选 + 翻页抓取。

输出 /tmp/cnki_all.json：[{query, title, href, src, date}]
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

PROXY = 'http://127.0.0.1:3457'
LOG = '/tmp/cnki_search.log'
OUT = '/tmp/cnki_all.json'


def emit(stage, done, total, msg=''):
    print('##PROGRESS## ' + json.dumps(
        {'stage': stage, 'done': done, 'total': total, 'msg': msg}, ensure_ascii=False), flush=True)


def anchors_from_argv():
    for i, a in enumerate(sys.argv):
        if a == '--anchor' and i + 1 < len(sys.argv):
            return [w.strip().lower() for w in sys.argv[i + 1].split(',') if w.strip()]
    return []


def keep_by_anchor(title, anchors):
    if not anchors:
        return True
    t = (title or '').lower()
    return any(a in t for a in anchors)


def out_dir():
    for i, a in enumerate(sys.argv):
        if a == '--out' and i + 1 < len(sys.argv):
            return os.path.abspath(sys.argv[i + 1])
    return os.path.abspath(os.environ.get('PAPER_OUT') or
                           os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '论文'))


def merge_into_outdir(results, outdir):
    """把知网结果并进 metadata.json，并单独出一份中文清单。"""
    os.makedirs(outdir, exist_ok=True)
    meta_path = os.path.join(outdir, 'metadata.json')
    state = json.load(open(meta_path, encoding='utf-8')) if os.path.exists(meta_path) else []
    def _key(x):
        doi = (x.get('doi') or '').strip().lower()
        return doi or re.sub(r'[^a-z0-9]+', ' ', (x.get('title') or '').lower()).strip()

    have = {_key(x) for x in state}
    added = 0
    for r in results:
        t = (r.get('title') or '').strip()
        k = re.sub(r'[^a-z0-9]+', ' ', t.lower()).strip()
        if not t or k in have:
            continue
        have.add(k)
        state.append({
            'title': t,
            'year': int((r.get('date') or '').strip()[:4]) if (r.get('date') or '').strip()[:4].isdigit() else None,
            'venue': r.get('src') or '',
            'authors': [],
            'doi': None,
            'lang': 'zh',
            'landing': (r.get('href') or '') if (r.get('href') or '').startswith('http')
                       else 'https://kns.cnki.net' + (r.get('href') or ''),
            'query': r.get('query'),
            'download': 'needs_manual',
            'cites': 0,
        })
        added += 1
    json.dump(state, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    zh = [x for x in state if x.get('lang') == 'zh']
    path = os.path.join(outdir, '中文检索结果.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('# 中文检索结果（知网，需登录下载）\n\n共 %d 条。点链接在浏览器里过 VPN 下载。\n\n' % len(zh))
        f.write('| # | 年份 | 标题 | 来源 | 检索词 | 链接 |\n|---|---|---|---|---|---|\n')
        for i, x in enumerate(zh, 1):
            f.write('| %d | %s | %s | %s | %s | %s |\n' % (
                i, x.get('year') or '', (x.get('title') or '').replace('|', '/')[:80],
                (x.get('venue') or '').replace('|', '/')[:24], x.get('query') or '',
                x.get('landing') or ''))
    print('中文结果 %d 条（新增 %d）→ %s' % (len(zh), added, path), flush=True)
    return added

QUERIES = ['配对交易', '统计套利', '跨市场套利', '协整 套利', '量化交易 套利', '高频交易 套利', '股指期货 套利', 'ETF 套利']


def log(m):
    line = time.strftime('%H:%M:%S ') + m
    print(line, flush=True)
    open(LOG, 'a', encoding='utf-8').write(line + '\n')


def http(path, timeout=50):
    return urllib.request.urlopen(PROXY + path, timeout=timeout).read().decode()


def ev(expr, tid):
    req = urllib.request.Request(PROXY + '/eval?target=' + tid, data=expr.encode(),
                                 headers={'Content-Type': 'text/plain'})
    return json.load(urllib.request.urlopen(req, timeout=30)).get('value')


def click(sel, tid):
    req = urllib.request.Request(PROXY + '/click?target=' + tid, data=sel.encode(),
                                 headers={'Content-Type': 'text/plain'})
    try:
        return urllib.request.urlopen(req, timeout=20).read().decode()[:80]
    except Exception as exc:
        return 'ERR ' + str(exc)[:60]


EXTRACT = """Array.from(document.querySelectorAll('table tr')).map(function(tr){
  var a=tr.querySelector('a');
  var c=Array.from(tr.querySelectorAll('td')).map(function(x){return (x.innerText||'').trim()});
  return a?{title:(a.innerText||'').trim(),href:a.getAttribute('href')||'',src:c[3]||'',date:c[4]||''}:null
}).filter(function(x){return x&&x.title&&x.href.indexOf('kcms2')>=0})"""


def main():
    import sys
    qs = QUERIES
    if '--queries-file' in sys.argv:
        f = sys.argv[sys.argv.index('--queries-file')+1]
        if os.path.exists(f):
            qs = [x.strip() for x in open(f, encoding='utf-8') if x.strip()]
    outdir = out_dir()
    tid = json.loads(http('/targets'))[0]['targetId']
    fresh = '--fresh' in sys.argv
    if fresh and os.path.exists(OUT):
        os.remove(OUT)
    results = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else []
    seen = {r['href'] for r in results}
    emit('cnki', 0, len(qs), '共 %d 个中文检索词' % len(qs))
    anchors = anchors_from_argv()
    if anchors:
        log('锚词：' + ', '.join(anchors))
    for qi, q in enumerate(qs, 1):
        url = ('https://kns.cnki.net/kns8s/defaultresult/index?kw=%s&korder=SU'
               % urllib.parse.quote(q))
        try:
            http('/navigate?target=%s&url=%s' % (tid, urllib.parse.quote(url, safe='')))
        except Exception:
            pass
        time.sleep(7)
        title = ev('document.title', tid) or ''
        if '安全验证' in title:
            log('%s -> 触发验证，跳过' % q)
            continue
        # 点「北大核心」筛选
        mark = ev("(function(){var a=Array.from(document.querySelectorAll('a')).filter(function(x){return (x.innerText||'').trim()==='北大核心'});if(!a.length)return 'no';a[0].setAttribute('data-bk','1');return 'ok'})()", tid)
        if mark == 'ok':
            click('[data-bk="1"]', tid)
            time.sleep(3)
        total = ev("(function(){var m=document.body.innerText.match(/总库\\s*\\n?\\s*(\\d+)/);return m?m[1]:'?'})()", tid)
        log('%s -> 筛选后 %s' % (q, total))
        for page in range(3):
            rows = ev(EXTRACT, tid) or []
            for r in rows:
                if r['href'] in seen:
                    continue
                if not keep_by_anchor(r.get('title'), anchors):
                    continue
                r['query'] = q
                results.append(r)
                seen.add(r['href'])
            nxt = ev("(function(){var a=Array.from(document.querySelectorAll('a')).filter(function(x){return /下一页/.test(x.innerText||'')});if(!a.length)return 'no';a[0].setAttribute('data-nx','1');return 'ok'})()", tid)
            if nxt != 'ok':
                break
            click('[data-nx="1"]', tid)
            time.sleep(3)
        json.dump(results, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        log('%s → 累计 %d 条（单条查询锚词：%s）' % (
            q, len(results), '启用' if anchors else '未启用'))
        emit('cnki', qi, len(qs), '%s → 累计 %d 条' % (q, len(results)))
    log('总计 %d 条' % len(results))
    merge_into_outdir(results, outdir)


if __name__ == '__main__':
    main()
