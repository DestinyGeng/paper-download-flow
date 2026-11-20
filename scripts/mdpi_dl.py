#!/usr/bin/env python3
"""用浏览器批量下载 MDPI（Cloudflare 需要真实浏览器）。"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

PROXY = 'http://127.0.0.1:3457'
D = '/Users/ligenghao/Downloads/中南/自用论文2/论文'
DL = os.path.expanduser('~/Downloads')
LOG = '/tmp/mdpi.log'


def log(m):
    line = time.strftime('%H:%M:%S ') + m
    print(line, flush=True)
    open(LOG, 'a', encoding='utf-8').write(line + '\n')


def tid():
    return json.loads(urllib.request.urlopen(PROXY + '/targets', timeout=10).read().decode())[0]['targetId']


def main():
    meta = json.load(open(os.path.join(D, 'metadata.json'), encoding='utf-8'))
    rows = [x for x in meta if (x.get('doi') or '').startswith('10.3390')
            and x.get('download') != 'ok' and x.get('final_level') in ('A+', 'A', 'A-', 'B+', 'B')]
    log('MDPI 待下 %d' % len(rows))
    T = tid()
    for i, x in enumerate(rows, 1):
        doi = x['doi']
        suffix = doi.split('/', 1)[1]
        cands = [x.get('oa_pdf'), 'https://www.mdpi.com/%s/pdf' % suffix]
        got = None
        for u in [c for c in cands if c]:
            before = {f for f in os.listdir(DL)}
            try:
                urllib.request.urlopen(PROXY + '/navigate?target=' + T + '&url=' + urllib.parse.quote(u, safe=''), timeout=50)
            except Exception:
                pass
            for _ in range(7):
                time.sleep(3)
                new = {f for f in os.listdir(DL)} - before
                new = [f for f in new if not f.startswith('~$') and not f.endswith('.crdownload')]
                if new:
                    got = new[0]
                    break
            if got:
                break
        if got:
            name = re.sub(r'[\\/:*?"<>|]+', ' ', (x.get('title') or 'untitled'))[:80].strip() + '.pdf'
            src = os.path.join(DL, got)
            dst = os.path.join(D, name)
            n = 1
            while os.path.exists(dst):
                n += 1
                dst = os.path.join(D, name[:-4] + '_v%d.pdf' % n)
            os.replace(src, dst)
            x['download'] = 'ok'
            x['file'] = os.path.basename(dst)
            x['via'] = 'browser-mdpi'
            log('[%d] OK %s' % (i, os.path.basename(dst)[:44]))
        else:
            log('[%d] fail %s' % (i, doi))
        json.dump(meta, open(os.path.join(D, 'metadata.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = sum(1 for x in rows if x.get('download') == 'ok')
    log('完成 %d/%d' % (ok, len(rows)))


if __name__ == '__main__':
    main()
