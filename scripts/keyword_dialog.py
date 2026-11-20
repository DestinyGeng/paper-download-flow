#!/usr/bin/env python3
"""关键词输入弹窗：中文/英文各最多 5 个。"""
import tkinter as tk
from tkinter import messagebox, ttk

MAX_KW = 5
SPLIT = r'[,，]+'


def ask_keywords():
    """弹出窗口，返回 (中文关键词列表, 英文关键词列表)。取消返回 (None, None)。"""
    root = tk.Tk()
    root.title('Paper Download Flow · 关键词')
    root.geometry('560x440')
    root.resizable(False, False)

    result = {'zh': None, 'en': None}

    tk.Label(root, text='中英文关键词（各最多 5 个，只用逗号分隔——中英文逗号都行）',
             font=('PingFang SC', 13, 'bold')).pack(pady=(16, 6))

    frame = tk.Frame(root)
    frame.pack(fill='both', expand=True, padx=20)

    tk.Label(frame, text='中文关键词', anchor='w').pack(fill='x')
    zh_text = tk.Text(frame, height=6, font=('PingFang SC', 12))
    zh_text.pack(fill='x', pady=(2, 12))
    zh_text.insert('1.0', '配对交易, 统计套利, 跨市场套利')

    tk.Label(frame, text='英文关键词', anchor='w').pack(fill='x')
    en_text = tk.Text(frame, height=6, font=('Menlo', 12))
    en_text.pack(fill='x', pady=(2, 6))
    en_text.insert('1.0', 'pairs trading, statistical arbitrage, cointegration')

    status = tk.Label(root, text='中文 0/5 ｜ 英文 0/5', fg='#555')
    status.pack(pady=(4, 0))

    def parse(widget):
        import re
        raw = widget.get('1.0', 'end').strip()
        items = [x for x in re.split(SPLIT, raw) if x]
        return items

    def refresh(*_):
        zh = parse(zh_text)
        en = parse(en_text)
        status.config(text='中文 %d/5 ｜ 英文 %d/5' % (len(zh), len(en)),
                      fg='#c0392b' if len(zh) > MAX_KW or len(en) > MAX_KW else '#555')

    zh_text.bind('<KeyRelease>', refresh)
    en_text.bind('<KeyRelease>', refresh)
    refresh()

    def on_ok():
        zh = parse(zh_text)
        en = parse(en_text)
        if len(zh) > MAX_KW or len(en) > MAX_KW:
            messagebox.showwarning('超出限制', '中文和英文关键词各最多 %d 个。' % MAX_KW)
            return
        if not zh and not en:
            messagebox.showwarning('没有关键词', '至少输入一个中文或英文关键词。')
            return
        result['zh'] = zh
        result['en'] = en
        root.destroy()

    def on_cancel():
        root.destroy()

    btns = tk.Frame(root)
    btns.pack(pady=12)
    ttk.Button(btns, text='开始检索', command=on_ok).pack(side='left', padx=10)
    ttk.Button(btns, text='取消', command=on_cancel).pack(side='left', padx=10)

    root.bind('<Return>', lambda e: on_ok())
    root.bind('<Escape>', lambda e: on_cancel())

    # 强制置顶并聚焦
    root.attributes('-topmost', True)
    root.update()
    root.lift()
    root.focus_force()
    root.after(300, lambda: root.attributes('-topmost', False))
    root.mainloop()
    return result['zh'], result['en']


if __name__ == '__main__':
    zh, en = ask_keywords()
    print('中文:', zh)
    print('英文:', en)