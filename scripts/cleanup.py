#!/usr/bin/env python3
"""清理规则：无期刊信息（查不到评级）的记录一律丢掉。

- 已下载且无评级的文件 → 移入系统废纸篓
- 记录本身 → 从 metadata.json 移出，转到 .trash/metadata.dropped.json（可追溯）
"""
import json
import os
import shutil
import sys

import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import D

META = os.path.join(D, 'metadata.json')
TRASH_DIR = os.path.join(D, '.trash')
DROPPED = os.path.join(TRASH_DIR, 'metadata.dropped.json')

if sys.platform == 'darwin':
    TRASH = os.path.expanduser('~/.Trash')
elif os.name == 'nt':
    TRASH = os.path.expanduser('~/.Trash_win')
else:
    TRASH = os.path.expanduser('~/.local/share/Trash/files')


def is_dead(x):
    return ((x.get('final_level') or '未定') == '未定'
            or (x.get('download') or '') == 'dropped')


def main():
    meta = json.load(open(META, encoding='utf-8'))
    dead = [x for x in meta if is_dead(x) and (x.get('download') or '') != 'no_metadata']
    if not dead:
        print('没有需要清理的记录')
        return

    os.makedirs(TRASH_DIR, exist_ok=True)
    os.makedirs(TRASH, exist_ok=True)
    hist = []
    if os.path.exists(DROPPED):
        try:
            hist = json.load(open(DROPPED, encoding='utf-8'))
        except Exception:
            hist = []

    moved = 0
    for x in dead:
        f = x.get('file')
        if f and os.path.exists(os.path.join(D, f)):
            src = os.path.join(D, f)
            dst = os.path.join(TRASH, f)
            n = 1
            while os.path.exists(dst):
                n += 1
                dst = os.path.join(TRASH, '%s_%d.pdf' % (f[:-4], n))
            shutil.move(src, dst)
            moved += 1
        x['download'] = 'dropped'
        x['final_source'] = 'unverifiable'
        hist.append(x)

    alive = [x for x in meta if not (is_dead(x) and (x.get('download') or '') != 'no_metadata')]
    json.dump(hist, open(DROPPED, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(alive, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('清理：移动文件 %d 个，移出记录 %d 条（已存 %s）' % (moved, len(dead), DROPPED))


if __name__ == '__main__':
    main()
