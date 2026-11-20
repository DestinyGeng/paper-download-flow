#!/usr/bin/env python3
"""CNKI 订阅库批量下载（系统级鼠标版）。

流程：osascript 打开文章页（激活标签）→ CDP 定位按钮 → 滚动居中
     → 换算屏幕坐标 → cliclick 点击 → 按 mtime 检测新文件 → 关闭标签。
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

PROXY = 'http://127.0.0.1:3457'
DL = os.path.expanduser('~/Downloads')
ROWS = '/tmp/cnki_rows.json'
LOG = '/tmp/cnki_gui.log'


def log(msg):
    line = time.strftime('%H:%M:%S ') + msg
    print(line, flush=True)
    open(LOG, 'a', encoding='utf-8').write(line + '\n')


def http(path, timeout=60):
    return urllib.request.urlopen(PROXY + path, timeout=timeout).read().decode()


def ev(expr, tid):
    req = urllib.request.Request(PROXY + '/eval?target=' + tid, data=expr.encode(),
                                 headers={'Content-Type': 'text/plain'})
    return json.load(urllib.request.urlopen(req, timeout=30)).get('value')


def openscript(url):
    subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to open location "%s"' % url],
                   capture_output=True)


def front_bounds():
    out = subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to get bounds of front window'],
                         capture_output=True, text=True).stdout.strip()
    return [int(x.strip()) for x in out.split(',')]


def recent_pdf(after_ts):
    for f in os.listdir(DL):
        if not f.lower().endswith('.pdf') or f.startswith('~$'):
            continue
        p = os.path.join(DL, f)
        try:
            if os.path.getmtime(p) >= after_ts and os.path.getsize(p) > 20000:
                return f
        except OSError:
            pass
    return None


def main():
    rows = json.load(open(ROWS, encoding='utf-8'))
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else len(rows)
    log('gui batch %d..%d of %d' % (start, end, len(rows)))
    ok = miss = 0
    for i in range(start, min(end, len(rows))):
        r = rows[i]
        title = (r.get('title') or '')[:32]
        openscript(r['href'])
        time.sleep(9)
        tabs = json.loads(http('/targets'))
        hits = [t for t in tabs if 'kcms2/article' in t['url']]
        if not hits:
            log('  [%d] 未打开详情页: %s' % (i, title))
            miss += 1
            continue
        tid = hits[0]['targetId']
        page_title = ev('document.title', tid) or ''
        if '安全验证' in page_title:
            log('BLOCKED 安全验证 at #%d' % i)
            break
        ev('(function(){var e=Array.from(document.querySelectorAll("#pdfDown"))'
           '.filter(function(x){return x.getBoundingClientRect().width>0})[0];'
           'if(e)e.scrollIntoView({block:"center"});return 1})()', tid)
        time.sleep(1.2)
        rect = ev('(function(){var e=Array.from(document.querySelectorAll("#pdfDown"))'
                  '.filter(function(x){return x.getBoundingClientRect().width>0})[0];'
                  'if(!e)return null;var b=e.getBoundingClientRect();'
                  'return {x:b.x,y:b.y,w:b.width,h:b.height,ih:innerHeight,oh:outerHeight}})()', tid)
        if not rect:
            log('  [%d] 无 PDF 按钮: %s' % (i, title))
            miss += 1
            continue
        b = front_bounds()
        ch = max(0, rect['oh'] - rect['ih'])
        sx = b[0] + int(rect['x'] + rect['w'] / 2)
        sy = b[1] + ch + int(rect['y'] + rect['h'] / 2)
        started = time.time() - 2
        subprocess.run(['cliclick', 'm:%d,%d' % (sx, sy), 'w:300', 'c:%d,%d' % (sx, sy)],
                       capture_output=True)
        got = None
        for _ in range(8):
            time.sleep(3)
            got = recent_pdf(started)
            if got:
                break
        if got:
            log('  [%d] OK %s -> %s' % (i, title, got[:34]))
            ok += 1
        else:
            log('  [%d] no file: %s' % (i, title))
            miss += 1
        subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to close active tab of front window'],
                       capture_output=True)
        time.sleep(1)
    log('DONE ok=%d miss=%d' % (ok, miss))


if __name__ == '__main__':
    main()
