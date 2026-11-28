#!/usr/bin/env python3
"""关键词输入弹窗：中英文关键词（各最多 5 个）+ 输出目录 + 年份范围。"""
import json
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

MAX_KW = 10

DEFAULTS = {
    'zh': '配对交易, 统计套利, 跨市场套利',
    'en': 'pairs trading, statistical arbitrage, cointegration',
    'out': os.path.expanduser('~/论文'),
    'years': 0,
    'pages': 5,
    'target': 300,
}

PAGE_OPTIONS = [('标准（每词 5 页 · 250 条）', 5),
                ('深挖（每词 10 页 · 500 条）', 10),
                ('极深（每词 20 页 · 1000 条）', 20)]
TARGET_OPTIONS = [('50 篇', 50), ('100 篇', 100), ('300 篇', 300), ('500 篇', 500)]


def state_path():
    """上次输入的存放位置（不写进 App 包，升级/重装都不丢）。"""
    base = os.environ.get('PAPER_STATE_DIR')
    if not base:
        if sys.platform == 'darwin':
            base = os.path.expanduser('~/Library/Application Support/PaperDownloadFlow')
        else:
            base = os.path.expanduser('~/.config/paper-download-flow')
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, 'last_input.json')


def load_last():
    try:
        with open(state_path(), encoding='utf-8') as f:
            data = json.load(f)
        return {k: data.get(k, DEFAULTS[k]) for k in DEFAULTS}
    except Exception:
        return dict(DEFAULTS)


def save_last(cfg):
    try:
        with open(state_path(), 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
    except Exception:
        pass  # 存不了就算了，不能因此让流程失败
SPLIT = r'[,，]+'
YEAR_OPTIONS = ['不限', '最近 3 年', '最近 5 年', '最近 10 年']
YEAR_MAP = {'不限': 0, '最近 3 年': 3, '最近 5 年': 5, '最近 10 年': 10}


def ask_keywords():
    """返回 dict：{'zh': [...], 'en': [...], 'out': '...', 'years': int}；取消返回 None。"""
    root = tk.Tk()
    root.title('Paper Download Flow · 设置')
    root.geometry('620x740')
    root.resizable(False, False)
    result = {'value': None}

    tk.Label(root, text='Paper Download Flow', font=('PingFang SC', 15, 'bold')).pack(pady=(14, 2))
    tk.Label(root, text='中英文关键词（各最多 %d 个，只用逗号分隔——中英文逗号都行）' % MAX_KW,
             fg='#555').pack(pady=(0, 4))
    tk.Label(root, text='每页 50 条，检索深度决定翻几页；去重后按相关性排序，再截到下载上限',
             fg='#999', font=('PingFang SC', 10)).pack(pady=(0, 10))

    body = tk.Frame(root)
    body.pack(fill='both', expand=True, padx=22)

    tk.Label(body, text='中文关键词', anchor='w').pack(fill='x')
    zh_text = tk.Text(body, height=4, font=('PingFang SC', 12))
    zh_text.pack(fill='x', pady=(2, 10))
    last = load_last()
    zh_text.insert('1.0', last['zh'])

    tk.Label(body, text='英文关键词', anchor='w').pack(fill='x')
    en_text = tk.Text(body, height=4, font=('Menlo', 12))
    en_text.pack(fill='x', pady=(2, 10))
    en_text.insert('1.0', last['en'])

    tk.Label(body, text='输出目录（PDF 与清单存放位置）', anchor='w').pack(fill='x')
    out_row = tk.Frame(body)
    out_row.pack(fill='x', pady=(2, 10))
    out_var = tk.StringVar(value=os.environ.get('PAPER_OUT') or last['out'])
    out_entry = tk.Entry(out_row, textvariable=out_var, font=('Menlo', 11))
    out_entry.pack(side='left', fill='x', expand=True)

    def browse():
        d = filedialog.askdirectory(initialdir=os.path.dirname(out_var.get()) or os.path.expanduser('~'))
        if d:
            out_var.set(d)

    ttk.Button(out_row, text='浏览…', command=browse).pack(side='left', padx=(6, 0))

    depth_row = tk.Frame(body)
    depth_row.pack(fill='x')
    tk.Label(depth_row, text='检索深度', anchor='w').pack(side='left')
    tk.Label(depth_row, text='下载上限', anchor='w').pack(side='left', padx=(16, 0))

    pick_row = tk.Frame(body)
    pick_row.pack(fill='x', pady=(2, 8))
    page_var = tk.StringVar()
    target_var = tk.StringVar()
    _page_names = [t for t, _ in PAGE_OPTIONS]
    _target_names = [t for t, _ in TARGET_OPTIONS]
    page_var.set(next((t for t, v in PAGE_OPTIONS if v == last.get('pages', 5)), _page_names[0]))
    target_var.set(next((t for t, v in TARGET_OPTIONS if v == last.get('target', 300)), _target_names[2]))
    ttk.Combobox(pick_row, textvariable=page_var, values=_page_names,
                 state='readonly', width=28).pack(side='left')
    ttk.Combobox(pick_row, textvariable=target_var, values=_target_names,
                 state='readonly', width=14).pack(side='left', padx=(10, 0))

    tk.Label(body, text='年份范围', anchor='w').pack(fill='x')
    _years = {'不限': 0, '最近 3 年': 3, '最近 5 年': 5, '最近 10 年': 10}
    _rev = {v: k for k, v in _years.items()}
    year_var = tk.StringVar(value=_rev.get(last['years'], '不限'))
    ttk.Combobox(body, textvariable=year_var, values=YEAR_OPTIONS,
                 state='readonly').pack(fill='x', pady=(2, 8))

    status = tk.Label(root, text='中文 0/%d ｜ 英文 0/%d' % (MAX_KW, MAX_KW), fg='#555')
    status.pack(pady=(2, 0))

    def parse(widget):
        return [x.strip() for x in re.split(SPLIT, widget.get('1.0', 'end').strip()) if x.strip()]

    def refresh(*_):
        zh, en = parse(zh_text), parse(en_text)
        status.config(text='中文 %d/%d ｜ 英文 %d/%d' % (len(zh), MAX_KW, len(en), MAX_KW),
                      fg='#c0392b' if len(zh) > MAX_KW or len(en) > MAX_KW else '#555')

    zh_text.bind('<KeyRelease>', refresh)
    en_text.bind('<KeyRelease>', refresh)
    refresh()

    def on_ok():
        zh, en = parse(zh_text), parse(en_text)
        if len(zh) > MAX_KW or len(en) > MAX_KW:
            messagebox.showwarning('超出限制', '中文和英文关键词各最多 %d 个。' % MAX_KW)
            return
        if not zh and not en:
            messagebox.showwarning('没有关键词', '至少输入一个中文或英文关键词。')
            return
        out = out_var.get().strip() or os.path.expanduser('~/论文')
        cfg = {'zh': zh, 'en': en, 'out': out, 'years': YEAR_MAP.get(year_var.get(), 0),
               'pages': dict(PAGE_OPTIONS).get(page_var.get(), 5),
               'target': dict(TARGET_OPTIONS).get(target_var.get(), 300)}
        save_last({'zh': '\n'.join(zh) if zh else '', 'en': '\n'.join(en) if en else '',
                   'out': out, 'years': cfg['years'],
                   'pages': cfg['pages'], 'target': cfg['target']})
        result['value'] = cfg
        root.destroy()

    def on_cancel():
        root.destroy()

    btns = tk.Frame(root)
    btns.pack(pady=14)
    ttk.Button(btns, text='开始检索', command=on_ok).pack(side='left', padx=10)
    ttk.Button(btns, text='取消', command=on_cancel).pack(side='left', padx=10)

    root.bind('<Return>', lambda e: on_ok())
    root.bind('<Escape>', lambda e: on_cancel())
    root.attributes('-topmost', True)
    root.update()
    root.lift()
    root.focus_force()
    root.after(300, lambda: root.attributes('-topmost', False))
    root.mainloop()
    return result['value']


if __name__ == '__main__':
    print(ask_keywords())
