#!/usr/bin/env python3
"""订阅库下载：按 DOI 前缀构造出版商 PDF 直链，用浏览器触发下载。

流程：新标签页打开 PDF 直链 → Chrome 自动下载到 ~/Downloads → 检测新增文件
     → 移到 论文/ 并重命名 → 校验 → sha256 查重 → 记录。

用法：
    python3 subscribed_download.py --publishers wiley --limit 20
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.parse
import urllib.request

PROXY = 'http://127.0.0.1:3457'
DL = os.path.expanduser('~/Downloads')
OUT = '/Users/ligenghao/Downloads/中南/自用论文2/论文'
META = os.path.join(OUT, 'metadata.json')

TEMPLATES = {
    'wiley':    'https://libvpn.zuel.edu.cn/doi/pdfdirect/{doi}?download=true&__proto__=https&__host__=onlinelibrary.wiley.com',
    'tandf':    'https://libvpn.zuel.edu.cn/doi/pdf/{doi}?download=true&__proto__=https&__host__=www.tandfonline.com',
    'springer': 'https://libvpn.zuel.edu.cn/content/pdf/{doi}.pdf?__proto__=https&__host__=link.springer.com',
}
PUB_DOI = {
    'wiley': ('10.1111', '10.1002', '10.1002'),
    'tandf': ('10.1080',),
    'springer': ('10.1007',),
}


def http(path, timeout=60):
    return json.load(urllib.request.urlopen(PROXY + path, timeout=timeout))


def ev(expr, tid):
    req = urllib.request.Request(PROXY + '/eval?target=' + tid, data=expr.encode(),
                                 headers={'Content-Type': 'text/plain'})
    return json.load(urllib.request.urlopen(req, timeout=30)).get('value')


MAIN_TARGET = None


def open_tab(url):
    """复用同一个标签页导航；PDF 不会触发 load 事件，502 属正常。"""
    global MAIN_TARGET
    if MAIN_TARGET is None:
        tabs = http('/targets')
        MAIN_TARGET = tabs[0]['targetId']
    try:
        http('/navigate?target=' + MAIN_TARGET + '&url=' + urllib.parse.quote(url, safe=''), timeout=60)
    except Exception:
        pass
    return MAIN_TARGET


def close_tab(tid):
    try:
        http('/close?target=' + tid, timeout=15)
    except Exception:
        pass


def pdfs_in_downloads():
    return {f for f in os.listdir(DL) if f.lower().endswith('.pdf')}


def wait_new_pdf(before, timeout=25):
    start = time.time()
    while time.time() - start < timeout:
        now = pdfs_in_downloads()
        added = now - before
        if added:
            f = sorted(added)[-1]
            p = os.path.join(DL, f)
            time.sleep(1)
            try:
                if os.path.getsize(p) > 20000:
                    return p
            except OSError:
                pass
        time.sleep(2)
    return None


def fname(title):
    """文件名 = 标题（去非法字符，截断 80 字）。"""
    t = (title or 'untitled').strip()
    t = re.sub(r'[\\/:*?"<>|\n\r\t]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip(' .')
    return (t[:80] or 'untitled') + '.pdf'


def slug(title):
    words = re.findall(r'[A-Za-z0-9]+', title or '')[:4]
    return ''.join(words) or 'paper'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--publishers', default='wiley')
    ap.add_argument('--limit', type=int, default=20)
    args = ap.parse_args()
    pubs = [p.strip() for p in args.publishers.split(',')]
    meta = json.load(open(META, encoding='utf-8'))
    seen_sha = set()
    for f in os.listdir(OUT):
        if f.lower().endswith('.pdf'):
            try:
                seen_sha.add(hashlib.sha256(open(os.path.join(OUT, f), 'rb').read()).hexdigest())
            except OSError:
                pass

    targets = []
    for x in meta:
        if x.get('download') == 'ok' or not x.get('doi'):
            continue
        pre = x['doi'].split('/')[0]
        for pub in pubs:
            if pre in PUB_DOI.get(pub, ()):
                targets.append((pub, x))
                break
    targets = targets[:args.limit]
    print('targets:', len(targets), flush=True)

    stats = {'ok': 0, 'fail': 0, 'dup': 0}
    for i, (pub, x) in enumerate(targets, 1):
        before = pdfs_in_downloads()
        url = TEMPLATES[pub].format(doi=x['doi'])
        tid = None
        try:
            tid = open_tab(url)
            time.sleep(3)
            path = wait_new_pdf(before, timeout=25)
            if not path:
                x['download'] = 'sub_fail:no_file'
                stats['fail'] += 1
                print('  [%d/%d] no file  %s' % (i, len(targets), (x.get('title') or '')[:50]), flush=True)
                continue
            h = hashlib.sha256(open(path, 'rb').read()).hexdigest()
            if h in seen_sha:
                os.remove(path)
                x['download'] = 'dup_sha'
                stats['dup'] += 1
                print('  [%d/%d] dup      %s' % (i, len(targets), (x.get('title') or '')[:50]), flush=True)
                continue
            first = re.sub(r'[^A-Za-z]', '', (x['authors'][0].split()[-1] if x.get('authors') else '')) or 'Anon'
            name = fname(x.get('title'))
            dest = os.path.join(OUT, name)
            n = 1
            while os.path.exists(dest):
                n += 1
                dest = os.path.join(OUT, name[:-4] + '_v%d.pdf' % n)
            shutil.move(path, dest)
            info = subprocess.run(['pdfinfo', dest], capture_output=True).stdout.decode('utf-8', 'replace')
            pages = re.search(r'Pages:\s+(\d+)', info)
            seen_sha.add(h)
            x['download'] = 'ok'
            x['file'] = os.path.basename(dest)
            x['bytes'] = os.path.getsize(dest)
            x['sha256'] = h
            x['via'] = pub
            stats['ok'] += 1
            print('  [%d/%d] OK %3s pages  %s' % (i, len(targets), pages.group(1) if pages else '?', x['title'][:46]), flush=True)
        except Exception as exc:
            x['download'] = 'sub_fail:%s' % str(exc)[:40]
            stats['fail'] += 1
            print('  [%d/%d] ERR %s' % (i, len(targets), str(exc)[:60]), flush=True)
        finally:
            pass
            if i % 5 == 0:
                json.dump(meta, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    json.dump(meta, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('DONE', stats, flush=True)


if __name__ == '__main__':
    main()