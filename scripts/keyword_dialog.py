#!/usr/bin/env python3
"""关键词输入弹窗：中英文关键词 + 输出目录 + 规模选项 + 领域锚词。"""
import json
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

MAX_KW = 10

DEFAULTS = {
    'zh': '美国股市 溢出, 风险传染 渠道',
    'en': 'spillover US stock market, contagion channel stock market',
    'out': os.path.expanduser('~/论文'),
    'years': 0,
    'pages': 5,
    'target': 300,
    'anchor': '',
}

PAGE_OPTIONS = [('标准（每词 5 页 · 250 条）', 5),
                ('深挖（每词 10 页 · 500 条）', 10),
                ('极深（每词 20 页 · 1000 条）', 20)]
TARGET_OPTIONS = [('50 篇', 50), ('100 篇', 100), ('300 篇', 300), ('500 篇', 500)]

# 三条固定的推荐模板（中文, 英文）
TEMPLATES = [
    ('美国股市 溢出', 'spillover US stock market'),
    ('风险传染 渠道', 'contagion channel stock market'),
    ('波动率溢出 跨市场', 'volatility spillover cross-market'),
]

SPLIT = r'[,，]+'
YEAR_OPTIONS = ['不限', '最近 3 年', '最近 5 年', '最近 10 年']
YEAR_MAP = {'不限': 0, '最近 3 年': 3, '最近 5 年': 5, '最近 10 年': 10}


def is_compound(s, lang):
    """复合词判定：英文 ≥2 个词；中文含空格或长度 ≥4 视为复合。"""
    s = (s or '').strip()
    if not s:
        return True
    if lang == 'en':
        return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]*", s)) >= 2
    return len([t for t in re.split(r'\s+', s) if t]) >= 2 or len(s) >= 4


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


CNKI_CACHE = '/tmp/cnki_all.json'


def clear_cnki_cache():
    """新论文：清掉上次知网积累的检索结果，避免旧题目混进新清单。"""
    try:
        if os.path.exists(CNKI_CACHE):
            os.remove(CNKI_CACHE)
            return True
    except Exception:
        pass
    return False


def ask_keywords():
    """返回 dict：zh/en/out/years/pages/target/anchor；取消返回 None。"""
    root = tk.Tk()
    root.title('Paper Download Flow · 设置')
    root.geometry('640x820')
    root.resizable(False, False)
    result = {'value': None}
    last = load_last()

    tk.Label(root, text='Paper Download Flow', font=('PingFang SC', 15, 'bold')).pack(pady=(12, 2))
    tk.Label(root, text='用复合词，别用单词（单词召回全是噪声）— 中英文各最多 %d 个' % MAX_KW,
             fg='#555').pack(pady=(0, 8))

    body = tk.Frame(root)
    body.pack(fill='both', expand=True, padx=22)

    # 推荐模板
    tpl_row = tk.Frame(body)
    tpl_row.pack(fill='x', pady=(0, 6))
    tk.Label(tpl_row, text='推荐模板：', fg='#777', font=('PingFang SC', 10)).pack(side='left')

    tk.Label(body, text='中文关键词', anchor='w').pack(fill='x')
    zh_text = tk.Text(body, height=3, font=('PingFang SC', 12))
    zh_text.pack(fill='x', pady=(2, 8))
    zh_text.insert('1.0', last['zh'])

    tk.Label(body, text='英文关键词', anchor='w').pack(fill='x')
    en_text = tk.Text(body, height=3, font=('Menlo', 12))
    en_text.pack(fill='x', pady=(2, 8))
    en_text.insert('1.0', last['en'])

    def parse(widget):
        return [x.strip() for x in re.split(SPLIT, widget.get('1.0', 'end').strip()) if x.strip()]

    def add_template(zh, en):
        cur = parse(zh_text)
        if zh not in cur:
            zh_text.insert('end', ('' if not cur else '\n') + zh)
        cur = parse(en_text)
        if en not in cur:
            en_text.insert('end', ('' if not cur else '\n') + en)
        refresh()

    for zh, en in TEMPLATES:
        ttk.Button(tpl_row, text=zh, width=13,
                   command=lambda z=zh, e=en: add_template(z, e)).pack(side='left', padx=2)

    tk.Label(body, text='输出目录（PDF 与清单存放位置）', anchor='w').pack(fill='x')
    out_row = tk.Frame(body)
    out_row.pack(fill='x', pady=(2, 8))
    out_var = tk.StringVar(value=os.environ.get('PAPER_OUT') or last['out'])
    tk.Entry(out_row, textvariable=out_var, font=('Menlo', 11)).pack(side='left', fill='x', expand=True)

    def browse():
        d = filedialog.askdirectory(initialdir=os.path.dirname(out_var.get()) or os.path.expanduser('~'))
        if d:
            out_var.set(d)

    ttk.Button(out_row, text='浏览…', command=browse).pack(side='left', padx=(6, 0))

    # 锚词
    tk.Label(body, text='领域锚词（按题目自定，逗号分隔；标题里一个都不出现就丢弃）',
             anchor='w').pack(fill='x')
    anchor_var = tk.StringVar(value=last.get('anchor') or '')
    tk.Entry(body, textvariable=anchor_var, font=('PingFang SC', 11)).pack(fill='x', pady=(2, 8))

    # 规模
    depth_row = tk.Frame(body)
    depth_row.pack(fill='x')
    tk.Label(depth_row, text='检索深度', anchor='w').pack(side='left')
    tk.Label(depth_row, text='下载上限', anchor='w').pack(side='left', padx=(16, 0))
    tk.Label(depth_row, text='年份范围', anchor='w').pack(side='left', padx=(16, 0))

    pick_row = tk.Frame(body)
    pick_row.pack(fill='x', pady=(2, 8))
    page_var = tk.StringVar()
    target_var = tk.StringVar()
    year_var = tk.StringVar()
    _page_names = [t for t, _ in PAGE_OPTIONS]
    _target_names = [t for t, _ in TARGET_OPTIONS]
    page_var.set(next((t for t, v in PAGE_OPTIONS if v == last.get('pages', 5)), _page_names[0]))
    target_var.set(next((t for t, v in TARGET_OPTIONS if v == last.get('target', 300)), _target_names[2]))
    _rev = {v: k for k, v in YEAR_MAP.items()}
    year_var.set(_rev.get(last['years'], '不限'))
    ttk.Combobox(pick_row, textvariable=page_var, values=_page_names,
                 state='readonly', width=26).pack(side='left')
    ttk.Combobox(pick_row, textvariable=target_var, values=_target_names,
                 state='readonly', width=11).pack(side='left', padx=(8, 0))
    ttk.Combobox(pick_row, textvariable=year_var, values=YEAR_OPTIONS,
                 state='readonly', width=11).pack(side='left', padx=(8, 0))

    mode = {'new': False}
    mode_label = tk.Label(root, text='当前模式：继续上一轮（保留知网缓存）',
                          fg='#8a6d3b', justify='left', font=('PingFang SC', 10))
    mode_label.pack(pady=(2, 0))

    status = tk.Label(root, text='', fg='#555', justify='left')
    status.pack(pady=(4, 0))
    tip = tk.Label(root, text='', fg='#c0392b', justify='left', font=('PingFang SC', 10))
    tip.pack(pady=(0, 2))

    def single_words():
        bad = []
        for s in parse(zh_text):
            if not is_compound(s, 'zh'):
                bad.append(s)
        for s in parse(en_text):
            if not is_compound(s, 'en'):
                bad.append(s)
        return bad

    def refresh(*_):
        zh, en = parse(zh_text), parse(en_text)
        zbad = [s for s in zh if not is_compound(s, 'zh')]
        ebad = [s for s in en if not is_compound(s, 'en')]
        over = len(zh) > MAX_KW or len(en) > MAX_KW
        status.config(
            text='中文 %d/%d（%s %d 单词） ｜ 英文 %d/%d（%s %d 单词）' % (
                len(zh), MAX_KW, '🔴' if zbad else '🟢', len(zbad),
                len(en), MAX_KW, '🔴' if ebad else '🟢', len(ebad)),
            fg='#c0392b' if over else '#555')
        if zbad or ebad:
            tip.config(text='提示：' + '、'.join((zbad + ebad)[:4]) +
                            ' 这类单词太泛，建议写成「股市 溢出」「risk spillover」这种复合词')
        else:
            tip.config(text='')

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
        bad = single_words()
        if bad and len(bad) * 2 >= (len(zh) + len(en)):
            go = messagebox.askyesno(
                '单词检索词偏多',
                '检测到 %d 个单词检索词：%s\n\n单词在知网/OpenAlex 的召回很散，'
                '建议改成复合词（如「股市 溢出」）。\n仍然开始检索吗？'
                % (len(bad), '、'.join(bad[:5])))
            if not go:
                return
        out = out_var.get().strip() or os.path.expanduser('~/论文')
        anchors = [w.strip() for w in re.split(SPLIT, anchor_var.get()) if w.strip()]
        cfg = {'zh': zh, 'en': en, 'out': out, 'years': YEAR_MAP.get(year_var.get(), 0),
               'pages': dict(PAGE_OPTIONS).get(page_var.get(), 5),
               'target': dict(TARGET_OPTIONS).get(target_var.get(), 300),
               'anchor': anchors, 'new_paper': mode['new']}
        save_last({'zh': '\n'.join(zh), 'en': '\n'.join(en), 'out': out,
                   'years': cfg['years'], 'pages': cfg['pages'],
                   'target': cfg['target'], 'anchor': ','.join(anchors)})
        result['value'] = cfg
        root.destroy()

    def on_cancel():
        root.destroy()

    def start_new_paper():
        gone = clear_cnki_cache()
        mode['new'] = True
        mode_label.config(
            text='当前模式：开启新论文（知网缓存%s）' % ('已清空' if gone else '本来就没有'),
            fg='#1a7f37')

    btns = tk.Frame(root)
    btns.pack(pady=12)
    ttk.Button(btns, text='开启新论文搜索（清空缓存）', command=start_new_paper).pack(side='left', padx=6)
    ttk.Button(btns, text='开始检索', command=on_ok).pack(side='left', padx=6)
    ttk.Button(btns, text='取消', command=on_cancel).pack(side='left', padx=6)

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
