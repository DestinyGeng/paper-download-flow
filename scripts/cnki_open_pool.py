#!/usr/bin/env python3
"""标签页池：维持 N 个 CNKI 页打开；用户关一个补一个。

计数包含验证页（verify），避免验证页不计数导致无限补开。
"""
import json
import subprocess
import sys
import time
import urllib.request

PROXY = 'http://127.0.0.1:3457'
ROWS = '/tmp/cnki_rows.json'
LOG = '/tmp/cnki_pool.log'


def log(msg):
    line = time.strftime('%H:%M:%S ') + msg
    print(line, flush=True)
    open(LOG, 'a', encoding='utf-8').write(line + '\n')


def chrome_tabs():
    try:
        data = json.loads(urllib.request.urlopen(PROXY + '/targets', timeout=10).read().decode())
    except Exception:
        return []
    return [t for t in data if 'kns.cnki.net' in t['url']]


def ensure_window():
    out = subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to get count of windows'],
                         capture_output=True, text=True).stdout.strip()
    if out in ('', '0'):
        subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to make new window'],
                       capture_output=True)
        time.sleep(2)
        return False
    return True


def open_url(url):
    if not ensure_window():
        log('重建了 Chrome 窗口')
    script = ('tell application "Google Chrome"\n'
              '  set w to front window\n'
              '  set idx to active tab index of w\n'
              '  make new tab at end of tabs of w with properties {URL:"%s"}\n'
              '  set active tab index of w to idx\n'
              'end tell') % url
    subprocess.run(['osascript', '-e', script], capture_output=True)


def main():
    rows = json.load(open(ROWS, encoding='utf-8'))
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else len(rows)
    pool = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    queue = [r['href'] for r in rows[start:end]]
    opened = 0
    log('pool=%d queue=%d' % (pool, len(queue)))
    while queue or chrome_tabs():
        active = len(chrome_tabs())
        while active < pool and queue:
            open_url(queue.pop(0))
            opened += 1
            active += 1
            log('开第 %d 篇，当前 %d 个' % (opened, active))
            time.sleep(2)
        if not queue and not chrome_tabs():
            break
        time.sleep(5)
    log('结束，共开 %d 篇' % opened)


if __name__ == '__main__':
    main()
