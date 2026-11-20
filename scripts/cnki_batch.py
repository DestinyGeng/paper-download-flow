#!/usr/bin/env python3
"""CNKI 批量下载：逐篇打开详情页 → 点 PDF下载 → 等文件 → 关闭标签页。

依赖：CDP 代理（3457）、已过 CNKI 验证码的浏览器会话。
遇到"安全验证"页会停止并提示。
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import js_expr

PROXY = 'http://127.0.0.1:3457'
DL = os.path.expanduser('~/Downloads')
ROWS = '/tmp/cnki_rows.json'
LOG = '/tmp/cnki_batch.log'


def log(msg):
    line = time.strftime('%H:%M:%S ') + msg
    print(line, flush=True)
    open(LOG, 'a', encoding='utf-8').write(line + '\n')


def http(path, timeout=60):
    return json.load(urllib.request.urlopen(PROXY + path, timeout=timeout))


MAIN = None


def newtab(url):
    """复用同一个前台标签页导航（后台 tab 的点击不触发下载）。"""
    global MAIN
    if MAIN is None:
        MAIN = http('/targets')[0]['targetId']
    try:
        http('/navigate?target=' + MAIN + '&url=' + urllib.parse.quote(url, safe=''), timeout=50)
    except Exception:
        pass
    return MAIN


def closTab(tid):
    try:
        http('/close?target=' + tid, timeout=15)
    except Exception:
        pass


def ev(expr, tid):
    req = urllib.request.Request(PROXY + '/eval?target=' + tid, data=expr.encode(),
                                 headers={'Content-Type': 'text/plain'})
    return json.load(urllib.request.urlopen(req, timeout=30)).get('value')


def click(sel, tid):
    req = urllib.request.Request(PROXY + '/click?target=' + tid, data=sel.encode(),
                                 headers={'Content-Type': 'text/plain'})
    try:
        return urllib.request.urlopen(req, timeout=25).read().decode()[:100]
    except Exception as exc:
        return 'ERR ' + str(exc)[:80]


def main():
    rows = json.load(open(ROWS, encoding='utf-8'))
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else len(rows)
    log('batch start %d..%d of %d' % (start, end, len(rows)))
    ok = miss = 0
    for i in range(start, min(end, len(rows))):
        r = rows[i]
        url = r['href']
        title = (r.get('title') or '')[:36]
        before = {f for f in os.listdir(DL)}
        tid = None
        try:
            tid = newtab(url)
            time.sleep(6)
            page_title = ev('document.title', tid) or ''
            if '安全验证' in page_title:
                log('BLOCKED 安全验证 at #%d，请手动过一次再继续' % i)
                break
            mark = ev(js_expr.mark_visible_by_id('pdfDown', 'data-p'), tid)
            if mark != 'ok':
                log('  [%d] no pdf button: %s' % (i, title))
                miss += 1
                continue
            click('[data-p="1"]', tid)
            got = None
            for _ in range(9):
                time.sleep(3)
                new = {f for f in os.listdir(DL)} - before
                new = [f for f in new if not f.startswith('~$') and not f.endswith('.crdownload')]
                if new:
                    got = new[0]
                    break
            if got:
                log('  [%d] OK %s -> %s' % (i, title, got[:40]))
                ok += 1
            else:
                log('  [%d] no file: %s' % (i, title))
                miss += 1
        except Exception as exc:
            log('  [%d] ERR %s' % (i, str(exc)[:60]))
            miss += 1
        finally:
            time.sleep(1)
    log('DONE ok=%d miss=%d' % (ok, miss))


if __name__ == '__main__':
    main()