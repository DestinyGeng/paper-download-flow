#!/usr/bin/env python3
"""ScienceDirect 检索：用本地 CDP 代理驱动已登录的 Chrome，抓结果列表并入清单。

用法：
    python3 sd_search.py --queries-file q.txt --out ../新闻 --pages 2 [--anchor stock,equity]
"""
import json
import os
import re
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = os.environ.get('CDP_PROXY') or 'http://127.0.0.1:3457'
sys.path.insert(0, HERE)

import urllib.request


def http(path, timeout=50):
    return urllib.request.urlopen(PROXY + path, timeout=timeout).read().decode()


def ev(expr, tid):
    req = urllib.request.Request(PROXY + '/eval?target=' + tid, data=expr.encode(),
                                 headers={'Content-Type': 'text/plain'})
    return json.load(urllib.request.urlopen(req, timeout=40)).get('value')


def nav(tid, url):
    try:
        http('/navigate?target=%s&url=%s' % (tid, urllib.parse.quote(url, safe='')), timeout=60)
    except Exception:
        pass


def target():
    return json.loads(http('/targets'))[0]['targetId']


def emit(stage, done, total, msg=''):
    print('##PROGRESS## ' + json.dumps(
        {'stage': stage, 'done': done, 'total': total, 'msg': msg}, ensure_ascii=False), flush=True)


EXTRACT = """Array.from(document.querySelectorAll('li.ResultItem')).map(function(li){
  var a=li.querySelector('h3 a, a.result-list-title-link');
  if(!a) return null;
  var txt=(li.innerText||'').split('\\n').map(function(s){return s.trim()}).filter(Boolean);
  return {title:(a.innerText||'').trim(), href:a.href||'', lines:txt.slice(0,6)};
})"""


def parse_meta(lines):
    """从列表行里取年份和期刊名。"""
    joined = ' | '.join(lines or [])
    year = None
    m = re.search(r'\b(19|20)\d{2}\b', joined)
    if m:
        year = int(m.group(0))
    venue = ''
    for ln in (lines or [])[1:]:
        if re.search(r'\b(19|20)\d{2}\b', ln):
            venue = re.split(r'[,·]|\b(19|20)\d{2}\b', ln)[0].strip()
            venue = re.sub(r'(January|February|March|April|May|June|July|August|'
                           r'September|October|November|December)\s*$', '', venue).strip()
            venue = re.sub(r'\s*\d+\s*$', '', venue).strip()
            break
    return year, venue


def keep_by_anchor(title, anchors):
    if not anchors:
        return True
    t = (title or '').lower()
    return any(a in t for a in anchors)


def main():
    qs, out, pages, anchors = [], '.', 1, []
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == '--queries-file' and i + 1 < len(argv):
            qs = [x.strip() for x in open(argv[i + 1], encoding='utf-8') if x.strip()]
        elif a == '--out' and i + 1 < len(argv):
            out = os.path.abspath(argv[i + 1])
        elif a == '--pages' and i + 1 < len(argv):
            pages = int(argv[i + 1])
        elif a == '--anchor' and i + 1 < len(argv):
            anchors = [w.strip().lower() for w in argv[i + 1].split(',') if w.strip()]

    os.makedirs(out, exist_ok=True)
    meta_path = os.path.join(out, 'metadata.json')
    state = json.load(open(meta_path, encoding='utf-8')) if os.path.exists(meta_path) else []

    def key_of(x):
        doi = (x.get('doi') or '').strip().lower()
        return doi or re.sub(r'[^a-z0-9]+', ' ', (x.get('title') or '').lower()).strip()

    have = {key_of(x) for x in state}

    print('ScienceDirect 检索：%d 个词，%d 页' % (len(qs), pages), flush=True)
    tid = target()
    added = 0
    for qi, q in enumerate(qs, 1):
        for page in range(pages):
            url = ('https://www.sciencedirect.com/search?qs=%s&show=50&offset=%d'
                   % (urllib.parse.quote(q), page * 50))
            nav(tid, url)
            time.sleep(8)
            rows = ev(EXTRACT, tid) or []
            for r in rows:
                if not r or not r.get('title'):
                    continue
                if not keep_by_anchor(r['title'], anchors):
                    continue
                t = r['title'].strip()
                k = re.sub(r'[^a-z0-9]+', ' ', t.lower()).strip()
                if k in have:
                    continue
                have.add(k)
                _y, _v = parse_meta(r.get('lines'))
                state.append({
                    'title': t, 'year': _y, 'venue': _v,
                    'authors': [], 'doi': None, 'lang': 'en', 'landing': r.get('href'),
                    'query': q, 'download': 'needs_manual', 'cites': 0,
                    'source': 'sciencedirect',
                })
                added += 1
            json.dump(state, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print('  %s p%d → 本轮 %d 条，累计新增 %d' % (q[:30], page + 1, len(rows), added), flush=True)
        emit('sd', qi, len(qs), '%s → 新增 %d' % (q[:30], added))
    print('ScienceDirect 完成：新增 %d 条' % added, flush=True)


if __name__ == '__main__':
    main()
