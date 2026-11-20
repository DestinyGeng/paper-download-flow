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
    tid = json.loads(http('/targets'))[0]['targetId']
    results = json.load(open(OUT, encoding='utf-8')) if __import__('os').path.exists(OUT) else []
    seen = {r['href'] for r in results}
    for q in qs:
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
                if r['href'] not in seen:
                    r['query'] = q
                    results.append(r)
                    seen.add(r['href'])
            nxt = ev("(function(){var a=Array.from(document.querySelectorAll('a')).filter(function(x){return /下一页/.test(x.innerText||'')});if(!a.length)return 'no';a[0].setAttribute('data-nx','1');return 'ok'})()", tid)
            if nxt != 'ok':
                break
            click('[data-nx="1"]', tid)
            time.sleep(3)
        json.dump(results, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log('总计 %d 条' % len(results))


if __name__ == '__main__':
    main()
