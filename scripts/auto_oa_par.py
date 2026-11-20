#!/usr/bin/env python3
"""并发版自动下载 OA：先并发查 OA 链接，再并发下载。"""
import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36'}
D = '/Users/ligenghao/Downloads/中南/自用论文2/论文'
META = os.path.join(D, 'metadata.json')
LOG = '/tmp/auto_oa_par.log'
OA_WORKERS = 20
DL_WORKERS = 8


def log(m):
    line = time.strftime('%H:%M:%S ') + m
    print(line, flush=True)
    open(LOG, 'a', encoding='utf-8').write(line + '\n')


def fetch_oa(rec):
    doi = rec.get('doi')
    if not doi:
        return rec, None
    u = 'https://api.openalex.org/works/https://doi.org/%s?select=best_oa_location,locations&mailto=research@example.org' % urllib.parse.quote(doi)
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=12))
    except Exception:
        return rec, None
    best = d.get('best_oa_location') or {}
    url = best.get('pdf_url') or best.get('landing_page_url')
    if not url:
        for loc in (d.get('locations') or []):
            if loc.get('pdf_url'):
                return rec, loc['pdf_url']
    return rec, url


def download(item):
    rec, url = item
    if not url:
        return rec, None
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30)
        data = r.read()
        if data[:4] == b'%PDF' and len(data) > 20000:
            return rec, data
    except Exception:
        pass
    return rec, None


def fname(title):
    t = re.sub(r'[\\/:*?"<>|\n\r\t]+', ' ', (title or 'untitled'))
    t = re.sub(r'\s+', ' ', t).strip(' .')
    t = re.sub(r'_[一二-龥]{2,4}$', '', t)
    return (t[:80] or 'untitled') + '.pdf'


def main():
    meta = json.load(open(META, encoding='utf-8'))
    todo = [x for x in meta if x.get('download') not in ('ok', 'dropped', 'needs_manual')]
    log('待处理 %d' % len(todo))
    # 中文直接转手动
    zh = [x for x in todo if (x.get('lang') or 'en') == 'zh']
    for x in zh:
        x['download'] = 'needs_manual'
    en = [x for x in todo if (x.get('lang') or 'en') != 'zh']
    log('中文转手动 %d | 英文待查 %d' % (len(zh), len(en)))

    # 阶段 1：并发查 OA
    t0 = time.time()
    oa_items = []
    with ThreadPoolExecutor(max_workers=OA_WORKERS) as ex:
        futs = {ex.submit(fetch_oa, x): x for x in en}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                oa_items.append(f.result())
            except Exception:
                oa_items.append((futs[f], None))
            if i % 20 == 0:
                log('  查OA %d/%d' % (i, len(en)))
    with_url = [it for it in oa_items if it[1]]
    log('查完：%d 条有 OA 链接，耗时 %.0fs' % (len(with_url), time.time() - t0))

    # 阶段 2：并发下载
    t1 = time.time()
    ok = 0
    with ThreadPoolExecutor(max_workers=DL_WORKERS) as ex:
        futs = [ex.submit(download, it) for it in with_url]
        for i, f in enumerate(as_completed(futs), 1):
            rec, data = f.result()
            if data:
                name = fname(rec.get('title'))
                path = os.path.join(D, name)
                n = 1
                while os.path.exists(path):
                    n += 1
                    path = os.path.join(D, name[:-4] + '_v%d.pdf' % n)
                open(path, 'wb').write(data)
                rec['download'] = 'ok'
                rec['file'] = os.path.basename(path)
                rec['bytes'] = len(data)
                rec['sha256'] = hashlib.sha256(data).hexdigest()
                rec['via'] = 'auto-oa-par'
                ok += 1
                log('  OK %s' % os.path.basename(path)[:44])
            else:
                rec['download'] = 'needs_manual'
            if i % 10 == 0:
                log('  下载 %d/%d' % (i, len(with_url)))
    for it in oa_items:
        rec, url = it
        if rec.get('download') not in ('ok', 'needs_manual'):
            rec['download'] = 'needs_manual'
    json.dump(meta, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log('完成：下载 %d 篇，耗时 %.0fs' % (ok, time.time() - t1))


if __name__ == '__main__':
    main()
