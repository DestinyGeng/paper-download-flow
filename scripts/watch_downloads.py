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

DL = os.path.expanduser('~/Downloads')
OUT = '/Users/ligenghao/Downloads/中南/自用论文2/论文'
META = os.path.join(OUT, 'metadata.json')
LOG = '/tmp/watch_downloads.log'
STATE = '/tmp/watch_processed.txt'


def log(msg):
    line = time.strftime('%H:%M:%S ') + msg
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(line + '\n')


def fname(title):
    t = (title or 'untitled').strip()
    t = re.sub(r'[\\/:*?"<>|\n\r\t]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip(' .')
    t = re.sub(r'_[一二-龥]{2,4}$', '', t)   # 去掉中文"标题_作者"里的作者
    return (t[:80] or 'untitled') + '.pdf'


def load_processed():
    if not os.path.exists(STATE):
        return set()
    return set(x.strip() for x in open(STATE, encoding='utf-8') if x.strip())


def save_processed(s):
    open(STATE, 'w', encoding='utf-8').write('\n'.join(sorted(s)))


def match_meta(name, meta):
    pii = re.search(r'1-s2\.0-([A-Z0-9]+)-main', name)
    if pii:
        for x in meta:
            if pii.group(1) in (x.get('landing') or ''):
                return x
    base = os.path.splitext(name)[0].lower()
    for x in meta:
        t = (x.get('title') or '').lower()
        if t and (t[:40] in base or base[:40] in t):
            return x
    return None


def handle(path, meta):
    name = os.path.basename(path)
    if os.path.getsize(path) < 20000:
        log('skip small: ' + name)
        return
    with open(path, 'rb') as fh:
        head = fh.read(4)
    if head != b'%PDF':
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
    if x:
        x['download'] = 'ok'
        x['file'] = os.path.basename(dest)
        x['bytes'] = os.path.getsize(dest)
        x['sha256'] = h
        x['via'] = 'manual'
        json.dump(meta, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import board
        board.build()
    except Exception:
        pass


def main():
    once = '--once' in sys.argv
    meta = json.load(open(META, encoding='utf-8'))
    done = load_processed()
    log('watch start, meta=%d' % len(meta))
    while True:
        try:
            for f in [x for x in os.listdir(DL) if x.lower().endswith('.pdf') and x not in done]:
                p = os.path.join(DL, f)
                try:
                    s1 = os.path.getsize(p)
                    time.sleep(1.5)
                    s2 = os.path.getsize(p)
                except OSError:
                    continue
                if s1 != s2 or s2 < 20000:
                    continue
                handle(p, meta)
                done.add(f)
                save_processed(done)
        except Exception as exc:
            log('ERR ' + str(exc)[:80])
        if once:
            break
        time.sleep(4)


if __name__ == '__main__':
    main()