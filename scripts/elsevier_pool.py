#!/usr/bin/env python3
"""Elsevier 标签页池：维持 N 个文章页，关一个补一个，不抢焦点。"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

PROXY = 'http://127.0.0.1:3457'
OUT = '/Users/ligenghao/Downloads/中南/自用论文2/论文'
LOG = '/tmp/elsevier_pool.log'


def log(msg):
    line = time.strftime('%H:%M:%S ') + msg
    print(line, flush=True)
    open(LOG, 'a', encoding='utf-8').write(line + '\n')


def chrome_tabs():
    try:
        data = json.loads(urllib.request.urlopen(PROXY + '/targets', timeout=10).read().decode())
    except Exception:
        return []
    return [t for t in data if 'sciencedirect' in t['url'].lower()]


def ensure_window():
    out = subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to get count of windows'],
                         capture_output=True, text=True).stdout.strip()
    if out in ('', '0'):
        subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to make new window'],
                       capture_output=True)
        time.sleep(2)


def open_url(url):
    ensure_window()
    script = ('tell application "Google Chrome"\n'
              '  set w to front window\n'
              '  set idx to active tab index of w\n'
              '  make new tab at end of tabs of w with properties {URL:"%s"}\n'
              '  set active tab index of w to idx\n'
              'end tell') % url
    subprocess.run(['osascript', '-e', script], capture_output=True)


def main():
    pool = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    meta = json.load(open(os.path.join(OUT, 'metadata.json'), encoding='utf-8'))
    todo = [x for x in meta if x.get('download') != 'ok' and (x.get('doi') or '').startswith('10.1016')]
    queue = []
    for x in todo:
        m = re.search(r'/pii/([A-Z0-9]+)', x.get('landing') or '')
        if m:
            queue.append('https://libvpn.zuel.edu.cn/science/article/pii/%s?__proto__=https&__host__=www.sciencedirect.com' % m.group(1))
    log('pool=%d queue=%d' % (pool, len(queue)))
    opened = 0
    while queue or chrome_tabs():
        active = len(chrome_tabs())
        while active < pool and queue:
            open_url(queue.pop(0))
            opened += 1
            active += 1
            log('开第 %d 篇，当前 %d 个' % (opened, active))
            time.sleep(2)
        time.sleep(5)
    log('结束，共开 %d 篇' % opened)


if __name__ == '__main__':
    main()
