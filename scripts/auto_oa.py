#!/usr/bin/env python3
"""自动下载 OA：用 DOI 查 OpenAlex 拿 OA 链接，能下就下，下不了标记手动。

规则：
  - 有 OA 且能拿到 PDF -> 下载 + 校验 + 入库
  - 无 OA / 403 / 验证码 / 超时 -> 标记 needs_manual（不再重试）
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36'}
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import D
META = os.path.join(D, 'metadata.json')
LOG = '/tmp/auto_oa.log'


def log(m):
    line = time.strftime('%H:%M:%S ') + m
    print(line, flush=True)
    open(LOG, 'a', encoding='utf-8').write(line + '\n')


def oa_of(doi):
    if not doi:
        return None
    u = 'https://api.openalex.org/works/https://doi.org/%s?mailto=research@example.org' % urllib.parse.quote(doi)
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25))
    except Exception:
        return None
    best = (d.get('best_oa_location') or {})
    url = best.get('pdf_url') or best.get('landing_page_url')
    if not url:
        for loc in (d.get('locations') or []):
            if loc.get('pdf_url'):
                return loc['pdf_url']
    return url


def try_pdf(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45)
        ctype = (r.headers.get('content-type') or '').lower()
        data = r.read()
        if data[:4] == b'%PDF' and len(data) > 20000:
            return data
        return None
    except Exception:
        return None


def fname(title):
    t = re.sub(r'[\\/:*?"<>|\n\r\t]+', ' ', (title or 'untitled'))
    t = re.sub(r'\s+', ' ', t).strip(' .')
    t = re.sub(r'_[一二-龥]{2,4}$', '', t)
    return (t[:80] or 'untitled') + '.pdf'


def main():
    meta = json.load(open(META, encoding='utf-8'))
    todo = [x for x in meta if x.get('download') not in ('ok', 'dropped', 'needs_manual')]
    log('待处理 %d' % len(todo))
    ok = manual = 0
    for i, x in enumerate(todo, 1):
        if (x.get('lang') or 'en') == 'zh':
            x['download'] = 'needs_manual'
            manual += 1
            log('[%d] 中文 -> 手动: %s' % (i, (x.get('title') or '')[:36]))
            continue
        url = oa_of(x.get('doi'))
        if not url:
            x['download'] = 'needs_manual'
            manual += 1
            log('[%d] 无OA -> 手动: %s' % (i, (x.get('title') or '')[:36]))
            continue
        data = try_pdf(url)
        if not data:
            x['download'] = 'needs_manual'
            manual += 1
            log('[%d] 下不了 -> 手动: %s' % (i, (x.get('title') or '')[:36]))
            continue
        name = fname(x.get('title'))
        path = os.path.join(D, name)
        n = 1
        while os.path.exists(path):
            n += 1
            path = os.path.join(D, name[:-4] + '_v%d.pdf' % n)
        open(path, 'wb').write(data)
        x['download'] = 'ok'
        x['file'] = os.path.basename(path)
        x['bytes'] = len(data)
        x['sha256'] = hashlib.sha256(data).hexdigest()
        x['via'] = 'auto-oa'
        ok += 1
        log('[%d] OK %s' % (i, os.path.basename(path)[:44]))
        json.dump(meta, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        time.sleep(0.5)
    json.dump(meta, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log('完成: 下载 %d | 转手动 %d' % (ok, manual))


if __name__ == '__main__':
    main()
