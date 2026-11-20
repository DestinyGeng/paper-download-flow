#!/usr/bin/env python3
"""输出一句话汇总。"""
import json
import os
import time
from collections import Counter

OUT = '/Users/ligenghao/Downloads/中南/自用论文2/论文'
META = os.path.join(OUT, 'metadata.json')


def main():
    meta = json.load(open(META, encoding='utf-8'))
    ok = [x for x in meta if x.get('download') == 'ok']
    pdfs = [f for f in os.listdir(OUT) if f.lower().endswith('.pdf')]
    size = sum(os.path.getsize(os.path.join(OUT, f)) for f in pdfs) / 1e6
    fail = Counter((x.get('download') or '').split(':')[0] for x in meta if x.get('download') != 'ok')
    lv = Counter(x.get('final_level') or '未定' for x in ok)
    keep = sum(1 for x in ok if x.get('final_level') in ('A+', 'A', 'A-', 'B+', 'B'))
    print('=' * 52)
    print('文献采集汇总  %s' % time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 52)
    print('记录 %d ｜ 下载成功 %d ｜ 目录 PDF %d（%.0f MB）' % (len(meta), len(ok), len(pdfs), size))
    print('评级: ' + ' / '.join('%s=%d' % (k, v) for k, v in sorted(lv.items())))
    print('B 及以上: %d 篇' % keep)
    if fail:
        print('失败: ' + ' / '.join('%s=%d' % (k or 'unknown', v) for k, v in fail.most_common(6)))
    print('产物: %s' % OUT)
    print('=' * 52)


if __name__ == '__main__':
    main()
