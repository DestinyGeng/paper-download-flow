#!/usr/bin/env python3
"""守护 ~/Downloads：新下载的 PDF 自动重命名、校验、查重、入库。"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import D as OUT

DL = os.path.expanduser('~/Downloads')
META = os.path.join(OUT, 'metadata.json')
LOG = '/tmp/watch_downloads.log'
STATE = '/tmp/watch_processed.txt'


def log(msg):
    line = time.strftime('%H:%M:%S ') + msg
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(line + '\n')


def norm(v):
    return re.sub(r'[^0-9a-z\u4e00-\u9fa5]', '', (v or '').lower())


def fname(title):
    t = (title or 'untitled').strip()
    t = re.sub(r'[\\/:*?"<>|\n\r\t]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip(' .')
    t = re.sub(r'_[一二-龥]{2,4}$', '', t)
    return (t[:80] or 'untitled') + '.pdf'


def load_processed():
    if not os.path.exists(STATE):
        return set()
    return set(x.strip() for x in open(STATE, encoding='utf-8') if x.strip())


def save_processed(s):
    open(STATE, 'w', encoding='utf-8').write('\n'.join(sorted(s)))


def match_meta(name, meta):
    base = norm(os.path.splitext(name)[0])
    if len(base) < 8:
        return None
    for x in meta:
        t = norm(x.get('title'))
        if len(t) >= 8 and t[:20] == base[:20]:
            return x
    return None


def match_by_title(title, meta):
    t = norm(title)
    if len(t) < 10:
        return None
    for x in meta:
        if x.get('download') == 'ok':
            continue
        mt = norm(x.get('title'))
        if mt and mt[:30] == t[:30]:
            return x
    return None


def chrome_title():
    try:
        out = subprocess.run(
            ['osascript', '-e',
             'tell application "Google Chrome" to get title of active tab of front window'],
            capture_output=True, text=True, timeout=5)
        return out.stdout.strip()
    except Exception:
        return ''


def title_from_pdfinfo(path):
    try:
        out = subprocess.run(['pdfinfo', path], capture_output=True).stdout.decode('utf-8', 'replace')
        m = re.search(r'^Title: (.+)$', out, re.M)
        t = (m.group(1).strip() if m else '')
        if len(t) < 12 or re.search(r'proof|[0-9]+\.[0-9]+', t, re.I):
            return ''
        return t
    except Exception:
        return ''


def handle(path, meta):
    name = os.path.basename(path)
    if os.path.getsize(path) < 20000:
        log('skip small: ' + name)
        return
    with open(path, 'rb') as fh:
        if fh.read(4) != b'%PDF':
            log('skip not pdf: ' + name)
            return
    h = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    for f in os.listdir(OUT):
        if not f.lower().endswith('.pdf'):
            continue
        try:
            if hashlib.sha256(open(os.path.join(OUT, f), 'rb').read()).hexdigest() == h:
                os.remove(path)
                log('dup removed: ' + name + ' == ' + f)
                return
        except OSError:
            pass
    x = None
    # 优先：看板点「打开」时记录的 doi（意图追踪）
    try:
        pend = json.load(open('/tmp/board_pending.json', encoding='utf-8'))
        if time.time() - pend.get('ts', 0) < 900:
            pd = (pend.get('doi') or '').lower()
            for rec in meta:
                if (rec.get('doi') or '').lower() == pd and rec.get('download') != 'ok':
                    x = rec
                    log('意图追踪命中: %s' % (rec.get('title') or '')[:40])
                    break
    except Exception:
        pass
    if re.match(r'1-s2\.0-[A-Z0-9]+-main', name) and not x:
        page = chrome_title()
        if page:
            x = match_by_title(page, meta)
        if not x:
            pt = title_from_pdfinfo(path)
            if pt:
                x = match_by_title(pt, meta)
                if x:
                    log('PII 文件用 PDF 元数据匹配: %s' % (x.get('title') or '')[:40])
    if not x:
        x = match_meta(name, meta)
    target = fname(x.get('title')) if x else fname(name[:-4])
    dest = os.path.join(OUT, target)
    n = 1
    while os.path.exists(dest):
        n += 1
        dest = os.path.join(OUT, target[:-4] + '_v%d.pdf' % n)
    shutil.move(path, dest)
    info = subprocess.run(['pdfinfo', dest], capture_output=True).stdout.decode('utf-8', 'replace')
    pages = re.search(r'Pages:\s+(\d+)', info)
    log('OK %s -> %s (%s pages)' % (name[:36], os.path.basename(dest)[:46], pages.group(1) if pages else '?'))
    try:
        os.remove('/tmp/board_pending.json')
    except OSError:
        pass
    if x:
        x['download'] = 'ok'
        x['file'] = os.path.basename(dest)
        x['bytes'] = os.path.getsize(dest)
        x['sha256'] = h
        x['via'] = 'manual'
        json.dump(meta, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    try:
        import board
        board.build()
    except Exception:
        pass


def main():
    once = '--once' in sys.argv
    meta = json.load(open(META, encoding='utf-8'))
    meta_mtime = os.path.getmtime(META)
    done = load_processed()
    log('watch start, meta=%d' % len(meta))
    while True:
        try:
            m = os.path.getmtime(META)
            if m != meta_mtime:
                meta = json.load(open(META, encoding='utf-8'))
                meta_mtime = m
            for f in [x for x in os.listdir(DL) if x.lower().endswith('.pdf')]:
                p = os.path.join(DL, f)
                try:
                    s1 = os.path.getsize(p)
                    time.sleep(1.5)
                    s2 = os.path.getsize(p)
                    mt = int(os.path.getmtime(p))
                except OSError:
                    continue
                key = '%s:%d' % (f, mt)
                if key in done or s1 != s2 or s2 < 20000:
                    continue
                handle(p, meta)
                done.add(key)
                save_processed(done)
            try:
                import sync_status
                sync_status.main()
            except Exception:
                pass
        except Exception as exc:
            log('ERR ' + str(exc)[:80])
        if once:
            break
        time.sleep(4)


if __name__ == '__main__':
    main()