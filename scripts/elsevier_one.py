#!/usr/bin/env python3
"""Elsevier 逐篇：doi 跳转拿 PII → 打开文章页 → 等你下载 → 下一篇。"""
import json
import os
import re
import subprocess
import time
import urllib.parse

OUT = '/Users/ligenghao/Downloads/中南/自用论文2/论文'
META = os.path.join(OUT, 'metadata.json')
DL = os.path.expanduser('~/Downloads')
LOG = '/tmp/elsevier_one.log'


def log(m):
    line = time.strftime('%H:%M:%S ') + m
    print(line, flush=True)
    open(LOG, 'a', encoding='utf-8').write(line + '\n')


def set_url(u):
    subprocess.run(['osascript', '-e',
                    'tell application "Google Chrome" to set URL of active tab of front window to "%s"' % u],
                   capture_output=True)


def current_url():
    return subprocess.run(['osascript', '-e',
                           'tell application "Google Chrome" to get URL of active tab of front window'],
                          capture_output=True, text=True).stdout.strip()


def snap():
    return {f for f in os.listdir(DL) if f.lower().endswith('.pdf') and not f.startswith('~$')}


def main():
    meta = json.load(open(META, encoding='utf-8'))
    rows = [x for x in meta if x.get('download') != 'ok' and (x.get('doi') or '').startswith('10.1016')]
    log('Elsevier 待处理 %d' % len(rows))
    for i, x in enumerate(rows, 1):
        doi = x['doi']
        title = (x.get('title') or '')[:34]
        set_url('https://libvpn.zuel.edu.cn/%s?__proto__=https&__host__=doi.org' % doi)
        time.sleep(8)
        u = urllib.parse.unquote(current_url())
        m = re.search(r'science/article/(?:abs/)?pii/([A-Z0-9]{10,})', u)
        if not m:
            log('[%d] 拿不到 PII：%s' % (i, title))
            continue
        pii = m.group(1)
        set_url('https://libvpn.zuel.edu.cn/science/article/pii/%s?__proto__=https&__host__=www.sciencedirect.com' % pii)
        log('[%d] 已打开：%s（PII %s）等你点 View PDF' % (i, title, pii))
        before = snap()
        deadline = time.time() + 180
        got = None
        while time.time() < deadline:
            time.sleep(3)
            new = snap() - before
            if new:
                got = sorted(new)[-1]
                break
        if got:
            log('    ✔ 下载：%s' % got[:40])
            time.sleep(6)
        else:
            log('    ✖ 3 分钟没下载，跳过')
    log('结束')


if __name__ == '__main__':
    main()
