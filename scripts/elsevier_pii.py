#!/usr/bin/env python3
"""批量提取 Elsevier 文章的 PII：doi.org 走代理跳转 → 从 Redirect 解析。"""
import json
import os
import re
import subprocess
import time
import urllib.parse

OUT = '/Users/ligenghao/Downloads/中南/自用论文2/论文'
META = os.path.join(OUT, 'metadata.json')
DST = '/tmp/elsevier_pii2.json'
LOG = '/tmp/pii2.log'


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


def main():
    meta = json.load(open(META, encoding='utf-8'))
    rows = [x for x in meta if x.get('download') != 'ok' and (x.get('doi') or '').startswith('10.1016')]
    done = json.load(open(DST, encoding='utf-8')) if os.path.exists(DST) else []
    seen = {d['doi'] for d in done}
    log('待提取 %d，已有 %d' % (len(rows), len(done)))
    for i, x in enumerate(rows, 1):
        doi = x['doi']
        if doi in seen:
            continue
        set_url('https://libvpn.zuel.edu.cn/%s?__proto__=https&__host__=doi.org' % doi)
        time.sleep(8)
        u = urllib.parse.unquote(current_url())
        m = re.search(r'science/article/(?:abs/)?pii/([A-Z0-9]{10,})', u)
        if m:
            done.append({'doi': doi, 'pii': m.group(1), 'title': x.get('title')})
            log('[%d] %s -> %s' % (i, doi, m.group(1)))
        else:
            log('[%d] %s 未拿到 PII（%s）' % (i, doi, u[:60]))
        json.dump(done, open(DST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        time.sleep(2)
    log('DONE %d / %d' % (len(done), len(rows)))


if __name__ == '__main__':
    main()
