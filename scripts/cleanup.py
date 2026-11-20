#!/usr/bin/env python3
"""清理规则：无期刊信息（查不到评级）的记录一律删除/放弃。

- 已下载且无评级的文件 → 移入系统废纸篓
- 未下载且无评级的记录 → 标记 dropped，不再尝试
"""
import json
import os
import shutil
import sys
import time

import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import D
META = os.path.join(D, 'metadata.json')
if sys.platform == 'darwin':
    TRASH = os.path.expanduser('~/.Trash')
elif os.name == 'nt':
    TRASH = os.path.expanduser('~/.Trash_win')
else:
    TRASH = os.path.expanduser('~/.local/share/Trash/files')
os.makedirs(TRASH, exist_ok=True)


def main():
    meta = json.load(open(META, encoding='utf-8'))
    dead = [x for x in meta if (x.get('final_level') or '未定') == '未定'
            and (x.get('download') or '') not in ('dropped', 'no_metadata')]
    if not dead:
        print('没有需要清理的记录')
        return
    moved = skipped = 0
    for x in dead:
        f = x.get('file')
        if x.get('download') == 'ok' and f:
            src = os.path.join(D, f)
            if os.path.exists(src):
                dst = os.path.join(TRASH, f)
                n = 1
                while os.path.exists(dst):
                    n += 1
                    dst = os.path.join(TRASH, '%s_%d.pdf' % (f[:-4], n))
                shutil.move(src, dst)
                moved += 1
            x['file'] = None
        x['download'] = 'dropped'
        x['final_source'] = 'unverifiable'
        skipped += 1
    json.dump(meta, open(META, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('清理：删除文件 %d 个，放弃记录 %d 条' % (moved, skipped))


if __name__ == '__main__':
    main()
