#!/usr/bin/env python3
"""关键词输入弹窗：中英文关键词（各最多 5 个）+ 输出目录 + 年份范围。"""
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

MAX_KW = 5
SPLIT = r'[,，]+'
YEAR_OPTIONS = ['不限', '最近 3 年', '最近 5 年', '最近 10 年']
YEAR_MAP = {'不限': 0, '最近 3 年': 3, '最近 5 年': 5, '最近 10 年': 10}


def ask_keywords():
    """返回 dict：{'zh': [...], 'en': [...], 'out': '...', 'years': int}；取消返回 None。"""
    root = tk.Tk()
    root.title('Paper Download Flow · 设置')
    root.geometry('620x660')
    root.resizable(False, False)
    result = {'value': None}

    tk.Label(root, text='Paper Download Flow', font=('PingFang SC', 15, 'bold')).pack(pady=(14, 2))
    tk.Label(root, text='中英文关键词（各最多 5 个，只用逗号分隔——中英文逗号都行）',
             fg='#555').pack(pady=(0, 10))

    body = tk.Frame(root)
    body.pack(fill='both', expand=True, padx=22)

    tk.Label(body, text='中文关键词', anchor='w').pack(fill='x')
    zh_text = tk.Text(body, height=4, font=('PingFang SC', 12))
    zh_text.pack(fill='x', pady=(2, 10))
    zh_text.insert('1.0', '配对交易, 统计套利, 跨市场套利')

    tk.Label(body, text='英文关键词', anchor='w').pack(fill='x')
    en_text = tk.Text(body, height=4, font=('Menlo', 12))
    en_text.pack(fill='x', pady=(2, 10))
    en_text.insert('1.0', 'pairs trading, statistical arbitrage, cointegration')

    tk.Label(body, text='输出目录（PDF 与清单存放位置）', anchor='w').pack(fill='x')
    out_row = tk.Frame(body)
    out_row.pack(fill='x', pady=(2, 10))
    out_var = tk.StringVar(value=os.environ.get('PAPER_OUT') or os.path.expanduser('~/论文'))
    out_entry = tk.Entry(out_row, textvariable=out_var, font=('Menlo', 11))
    out_entry.pack(side='left', fill='x', expand=True)

    def browse():
        d = filedialog.askdirectory(initialdir=os.path.dirname(out_var.get()) or os.path.expanduser('~'))
        if d:
            out_var.set(d)

    ttk.Button(out_row, text='浏览…', command=browse).pack(side='left', padx=(6, 0))

    tk.Label(body, text='年份范围', anchor='w').pack(fill='x')
    year_var = tk.StringVar(value='不限')
    ttk.Combobox(body, textvariable=year_var, values=YEAR_OPTIONS,
                 state='readonly').pack(fill='x', pady=(2, 8))

    status = tk.Label(root, text='中文 0/5 ｜ 英文 0/5', fg='#555')
    status.pack(pady=(2, 0))

    def parse(widget):
        return [x.strip() for x in re.split(SPLIT, widget.get('1.0', 'end').strip()) if x.strip()]

    def refresh(*_):
        zh, en = parse(zh_text), parse(en_text)
        status.config(text='中文 %d/5 ｜ 英文 %d/5' % (len(zh), len(en)),
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
        result['value'] = {'zh': zh, 'en': en, 'out': out, 'years': YEAR_MAP.get(year_var.get(), 0)}
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
