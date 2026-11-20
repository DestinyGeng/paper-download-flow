#!/usr/bin/env python3
"""Paper Download Flow 主入口。

流程：弹窗输入关键词/目录/年份 → 英文检索 → 中文检索 → 定级 → 看板
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'scripts'))

try:
    import tkinter  # noqa: F401
except ImportError:
    print('当前 Python 缺少 tkinter（图形界面依赖），无法弹出输入窗口。')
    print('')
    print('解决办法（任选其一）：')
    print('  1) 用自带 tkinter 的 Python 运行，例如：')
    print('     /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 run.py')
    print('  2) 给当前 Python 安装 tkinter，例如：')
    print('     brew install python-tk@3.14')
    print('  3) 不用图形界面，直接用命令行：')
    print('     sh run_all.sh 500 3')
    sys.exit(1)

from keyword_dialog import ask_keywords


def run(cmd, desc, env):
    print('\n=== %s ===' % desc, flush=True)
    print('>', ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=HERE, env=env)
    if r.returncode != 0:
        print('（退出码 %d，继续）' % r.returncode, flush=True)


def main():
    cfg = ask_keywords()
    if not cfg:
        print('已取消。')
        return
    print('中文关键词:', cfg['zh'] or '（无）')
    print('英文关键词:', cfg['en'] or '（无）')
    print('输出目录:', cfg['out'])
    print('年份范围:', cfg['years'] or '不限')

    env = dict(os.environ)
    env['PAPER_OUT'] = cfg['out']
    env['PAPER_YEARS'] = str(cfg['years'] or 0)

    tmp = tempfile.mkdtemp(prefix='pdf-flow-')
    if cfg['en']:
        f = os.path.join(tmp, 'en.txt')
        open(f, 'w', encoding='utf-8').write('\n'.join(cfg['en']))
        run([sys.executable, os.path.join(HERE, 'scripts', 'batch_collect.py'),
             '--target', '300', '--pages', '5', '--years', str(cfg['years'] or 0),
             '--queries-file', f], '英文检索 + OA 下载', env)
    if cfg['zh']:
        f = os.path.join(tmp, 'zh.txt')
        open(f, 'w', encoding='utf-8').write('\n'.join(cfg['zh']))
        run([sys.executable, os.path.join(HERE, 'scripts', 'cnki_search.py'),
             '--queries-file', f], '中文检索（CNKI）', env)

    run([sys.executable, os.path.join(HERE, 'scripts', 'apply_levels.py')], '定级', env)
    run([sys.executable, os.path.join(HERE, 'scripts', 'board.py')], '生成看板', env)
    print('\n完成。输出目录：%s' % cfg['out'])
    print('看板：%s/进度看板.html' % cfg['out'])


if __name__ == '__main__':
    main()
