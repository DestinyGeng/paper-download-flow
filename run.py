#!/usr/bin/env python3
"""Paper Download Flow 主入口。

流程：弹窗输入关键词/目录/年份 → 英文检索 → 中文检索 → 定级 → 看板
GUI 版带实时进度窗口；打包后（frozen）会自动改用系统 Python 跑子脚本。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

FROZEN = bool(getattr(sys, 'frozen', False))
HERE = getattr(sys, '_MEIPASS', None) if FROZEN else os.path.dirname(os.path.abspath(__file__))
HERE = HERE or os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'scripts'))

PROGRESS_PREFIX = '##PROGRESS## '


def _python():
    """返回能执行子脚本的 Python 解释器。

    PyInstaller 打包后 sys.executable 指向 App 自身，用它起子进程只会再弹一个
    GUI（旧版「一直出现新窗口、不开始检索」的根因），所以打包态改用系统 Python。
    """
    if not FROZEN:
        return sys.executable
    me = os.path.realpath(sys.executable)
    for cand in (shutil.which('python3'), '/opt/homebrew/bin/python3',
                 '/usr/local/bin/python3', '/usr/bin/python3'):
        if cand and os.path.exists(cand) and os.path.realpath(cand) != me:
            return cand
    return None


PY = _python()

# 允许把打包后的可执行文件当成 python 用：PaperDownloadFlow scripts/board.py [args]
if FROZEN and len(sys.argv) > 1 and sys.argv[1].endswith('.py'):
    _s = sys.argv[1]
    _path = _s if os.path.isabs(_s) else os.path.join(HERE, 'scripts', os.path.basename(_s))
    if not PY:
        sys.exit('找不到系统 Python 3，无法运行 %s' % _path)
    os.execv(PY, [PY, _path] + sys.argv[2:])

STAGE_NAMES = {'filter': '相关性筛选', 'download': '下载中', 'cnki': '知网检索', 'done': '完成'}


def run_step(cmd, label, env, ui=None):
    """跑一个子脚本，逐行把输出喂给 UI（或打屏），并解析 ##PROGRESS## 行。"""
    if ui:
        ui.set_stage(label)
        ui.add_line('')
        ui.add_line('=== %s ===' % label)
    else:
        print('\n=== %s ===' % label, flush=True)
    p = subprocess.Popen(cmd, cwd=HERE, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1)
    if ui:
        ui.proc = p
    for line in p.stdout:
        line = line.rstrip()
        if not line:
            continue
        if line.startswith(PROGRESS_PREFIX):
            if ui:
                try:
                    ui.on_progress(json.loads(line[len(PROGRESS_PREFIX):]))
                except Exception:
                    pass
            continue
        if ui:
            ui.add_line(line)
        else:
            print(line, flush=True)
    p.wait()
    if ui:
        ui.proc = None
        if ui.cancelled:
            raise SystemExit(0)
    return p.returncode


def build_commands(cfg):
    """返回 [(cmd, 阶段名), ...]。"""
    env = dict(os.environ)
    env['PAPER_OUT'] = cfg['out']
    env['PAPER_YEARS'] = str(cfg['years'] or 0)
    tmp = tempfile.mkdtemp(prefix='pdf-flow-')
    scripts = os.path.join(HERE, 'scripts')
    steps = []
    if cfg['en']:
        f = os.path.join(tmp, 'en.txt')
        open(f, 'w', encoding='utf-8').write('\n'.join(cfg['en']))
        steps.append(([PY, os.path.join(scripts, 'batch_collect.py'),
                       '--target', str(cfg.get('target') or 300),
                       '--pages', str(cfg.get('pages') or 5),
                       '--years', str(cfg['years'] or 0),
                       '--anchor', ','.join(cfg.get('anchor') or []),
                       '--queries-file', f], '英文检索 + 下载'))
    if cfg['zh']:
        f = os.path.join(tmp, 'zh.txt')
        open(f, 'w', encoding='utf-8').write('\n'.join(cfg['zh']))
        cmd = [PY, os.path.join(scripts, 'cnki_search.py'),
               '--queries-file', f, '--out', cfg['out'],
               '--anchor', ','.join(cfg.get('anchor') or [])]
        if cfg.get('new_paper'):
            cmd.append('--fresh')
        steps.append((cmd, '中文检索（CNKI）'))
    steps.append(([PY, os.path.join(scripts, 'apply_levels.py')], '期刊定级'))
    steps.append(([PY, os.path.join(scripts, 'board.py')], '生成看板'))
    return steps, env


class RunWindow:
    """阶段标签 + 进度条 + 滚动日志 + 取消。"""

    def __init__(self, root, outdir):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.root = root
        self.outdir = outdir
        self.cancelled = False
        self.proc = None
        root.title('Paper Download Flow · 运行中')
        root.geometry('760x560')

        top = tk.Frame(root)
        top.pack(fill='x', padx=14, pady=(12, 4))
        self.stage = tk.Label(top, text='准备中…', font=('PingFang SC', 13, 'bold'), anchor='w')
        self.stage.pack(side='left')
        self.counter = tk.Label(top, text='', fg='#555')
        self.counter.pack(side='right')

        self.bar = ttk.Progressbar(root, mode='determinate', maximum=100)
        self.bar.pack(fill='x', padx=14, pady=(0, 8))

        wrap = tk.Frame(root)
        wrap.pack(fill='both', expand=True, padx=14)
        self.log = tk.Text(wrap, height=18, wrap='word', font=('Menlo', 11))
        sb = tk.Scrollbar(wrap, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set, state='disabled')
        self.log.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        bot = tk.Frame(root)
        bot.pack(fill='x', padx=14, pady=10)
        self.status = tk.Label(bot, text='', fg='#555', anchor='w')
        self.status.pack(side='left')
        self.open_btn = ttk.Button(bot, text='打开输出目录', state='disabled',
                                   command=self.open_out)
        self.open_btn.pack(side='right')
        self.cancel_btn = ttk.Button(bot, text='取消', command=self.cancel)
        self.cancel_btn.pack(side='right', padx=6)

    # --- 线程安全的 UI 更新 ---
    def _ui(self, fn, *a):
        self.root.after(0, lambda: fn(*a))

    def set_stage(self, text):
        def _():
            self.stage.config(text=text)
            self.bar['value'] = 0
            self.counter.config(text='')
        self._ui(_)

    def add_line(self, line):
        def _():
            self.log.config(state='normal')
            self.log.insert('end', line + '\n')
            self.log.see('end')
            self.log.config(state='disabled')
        self._ui(_)

    def on_progress(self, payload):
        stage = payload.get('stage') or ''
        done = payload.get('done') or 0
        total = payload.get('total') or 0

        def _():
            if total:
                self.bar['maximum'] = total
                self.bar['value'] = done
                self.counter.config(text='%d / %d' % (done, total))
            if stage:
                self.stage.config(text=STAGE_NAMES.get(stage, stage))
        self._ui(_)

    def cancel(self):
        self.cancelled = True
        self.status.config(text='正在取消…')
        p = self.proc
        if p and p.poll() is None:
            try:
                p.terminate()
            except Exception:
                pass

    def open_out(self):
        try:
            subprocess.Popen(['open', self.outdir])
        except Exception:
            pass

    def finish(self, ok=True):
        def _():
            if ok:
                self.stage.config(text='完成')
                self.counter.config(text='')
                self.bar['value'] = self.bar['maximum']
                self.status.config(text='全部完成　输出目录：%s' % self.outdir, fg='#1a7f37')
                self.cancel_btn.config(state='disabled')
                self.open_btn.config(state='normal')
            else:
                self.stage.config(text='已取消')
                self.status.config(text='已取消', fg='#c0392b')
                self.cancel_btn.config(state='disabled')
        self._ui(_)


def worker(win, cfg):
    steps, env = build_commands(cfg)
    try:
        for cmd, label in steps:
            code = run_step(cmd, label, env, ui=win)
            if code not in (0, None):
                win.add_line('（%s 退出码 %s，继续）' % (label, code))
        board = os.path.join(cfg['out'], '进度看板.html')
        if os.path.exists(board):
            win.add_line('看板：%s' % board)
            try:
                subprocess.Popen(['open', board])
            except Exception:
                pass
        win.finish(True)
    except SystemExit:
        win.finish(False)
    except Exception as exc:
        win.add_line('出错了：%s' % exc)
        win.finish(False)


def main():
    import tkinter as tk
    from keyword_dialog import ask_keywords

    if len(sys.argv) > 1 and '--cli' in sys.argv:
        cfg = ask_keywords()
        if not cfg:
            print('已取消。')
            return
        cfg['new_paper'] = True
        steps, env = build_commands(cfg)
        for cmd, label in steps:
            run_step(cmd, label, env)
        print('\n完成。输出目录：%s' % cfg['out'])
        return

    if FROZEN and not PY:
        import tkinter.messagebox as mb
        mb.showerror('缺少 Python', '打包版需要系统里有 Python 3（python3）。')
        return

    cfg = ask_keywords()
    if not cfg:
        return
    root = tk.Tk()
    win = RunWindow(root, cfg['out'])
    threading.Thread(target=worker, args=(win, cfg), daemon=True).start()
    root.mainloop()


if __name__ == '__main__':
    main()
