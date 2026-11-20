#!/usr/bin/env python3
"""半自动：逐篇打开 CNKI 文章页，等你下载完再翻下一篇。

你只需要：过验证 → 点「PDF下载」。
脚本检测到 ~/Downloads 出现新 PDF 后，等 8 秒自动开下一篇。
"""
import json
import os
import subprocess
import sys
import time

DL = os.path.expanduser('~/Downloads')
ROWS = '/tmp/cnki_rows.json'
LOG = '/tmp/cnki_open.log'
WAIT_PER_PAPER = 240   # 每篇最多等 4 分钟


def log(msg):
    line = time.strftime('%H:%M:%S ') + msg
    print(line, flush=True)
    open(LOG, 'a', encoding='utf-8').write(line + '\n')


def snapshot():
    return {f for f in os.listdir(DL) if f.lower().endswith('.pdf') and not f.startswith('~$')}


def set_url(url):
    subprocess.run(['osascript', '-e',
                    'tell application "Google Chrome" to set URL of active tab of front window to "%s"' % url],
                   capture_output=True)


def activate():
    subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to activate'], capture_output=True)


def main():
    rows = json.load(open(ROWS, encoding='utf-8'))
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else len(rows)
    log('open-mode %d..%d of %d' % (start, end, len(rows)))
    activate()
    done = 0
    for i in range(start, min(end, len(rows))):
        r = rows[i]
        title = (r.get('title') or '')[:34]
        before = snapshot()
        set_url(r['href'])
        log('#%d 已打开：%s' % (i, title))
        deadline = time.time() + WAIT_PER_PAPER
        got = None
        while time.time() < deadline:
            time.sleep(3)
            new = snapshot() - before
            if new:
                got = sorted(new)[-1]
                break
        if got:
            log('   ✔ 检测到下载：%s（等 8 秒开下一篇）' % got[:42])
            done += 1
            time.sleep(8)
        else:
            log('   ✖ 4 分钟未检测到下载，跳过：%s' % title)
    log('结束，成功检测 %d 篇' % done)


if __name__ == '__main__':
    main()
