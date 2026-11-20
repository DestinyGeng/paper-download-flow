#!/usr/bin/env python3
"""生成分类清单 HTML：按命中关键词数（3/2/1）分档，档内按评级排序。"""
import html
import json
import os
import re

D = '/Users/ligenghao/Downloads/中南/自用论文2/论文'
META = os.path.join(D, 'metadata.json')
TARGET = os.path.join(D, '分类清单.html')
LV = {'A+': 0, 'A': 1, 'A-': 2, 'B+': 3, 'B': 4, 'C': 5, '未定': 6}
COLOR = {'A+': '#c0392b', 'A': '#e67e22', 'A-': '#d4a017', 'B': '#2e9e5b', 'C': '#888', '未定': '#888'}


def norm(t):
    return re.sub(r'[-_/]', ' ', (t or '').lower())


PAIRS = re.compile(r'pair[s]?\s*trad|配对交易|配对套利|配对策略')
COPULA = re.compile(r'copula')
CROSS = re.compile(r'跨市场|cross.?market')


def link_of(x):
    doi = x.get('doi') or ''
    if doi:
        return 'https://doi.org/' + doi
    return x.get('landing') or x.get('link') or ''


def main():
    meta = json.load(open(META, encoding='utf-8'))
    rows = [x for x in meta if x.get('download') not in ('dropped',)]
    for x in rows:
        s = norm(x.get('title'))
        x['_h'] = sum([bool(PAIRS.search(s)), bool(COPULA.search(s)), bool(CROSS.search(s))])
        t = []
        if PAIRS.search(s):
            t.append('配对')
        if COPULA.search(s):
            t.append('copula')
        if CROSS.search(s):
            t.append('跨市场')
        x['_tag'] = '+'.join(t)
        x['_lv'] = x.get('final_level') or '未定'
    parts = []
    for h in (3, 2, 1):
        items = sorted([x for x in rows if x['_h'] == h],
                       key=lambda x: (LV.get(x['_lv'], 9), -(x.get('year') or 0)))
        if not items:
            continue
        trs = []
        for i, x in enumerate(items, 1):
            st = '✅' if x.get('download') == 'ok' else '⬜'
            link = link_of(x)
            act = ('<a class="open" href="%s" target="_blank">打开</a>' % html.escape(link)) if link else ''
            trs.append('<tr class="%s"><td>%d</td><td><span style="color:%s;font-weight:700">%s</span></td>'
                       '<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                       % ('done' if x.get('download') == 'ok' else 'todo', i, COLOR.get(x['_lv'], '#888'),
                          x['_lv'], st, html.escape(x['_tag']), html.escape((x.get('title') or '')[:90]),
                          html.escape((x.get('venue') or '')[:26]), x.get('year') or '—', act))
        parts.append('<h2>命中 %d 个关键词（%d 条）</h2>\n<table><tr><th>#</th><th>评级</th><th>状态</th>'
                     '<th>命中</th><th>标题</th><th>期刊</th><th>年</th><th>操作</th></tr>\n%s\n</table>'
                     % (h, len(items), '\n'.join(trs)))
    doc = ('''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>配对交易文献分类</title>
<style>
body{font-family:-apple-system,"PingFang SC",sans-serif;margin:24px;background:#f7f8fa;color:#222}
h1{font-size:20px;margin:0 0 6px}h2{font-size:16px;margin:26px 0 8px}
.sum{color:#555;margin-bottom:10px;font-size:13px}
table{border-collapse:collapse;width:100%%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:10px}
th,td{padding:6px 9px;border-bottom:1px solid #eef0f2;font-size:13px;text-align:left}
th{background:#fafbfc;position:sticky;top:0}
tr.todo td{color:#888}
a.open{display:inline-block;padding:2px 9px;background:#2e6ce0;color:#fff;border-radius:4px;text-decoration:none;font-size:12px}
</style></head><body>
<h1>配对交易文献分类</h1>
<div class="sum">按命中关键词数分档（配对交易 / copula / 跨市场），档内按评级 A→C 排序 ｜ 共 %d 条 ｜ ✅ 已下载 %d</div>
%s
</body></html>''' % (len(rows), sum(1 for x in rows if x.get('download') == 'ok'), '\n'.join(parts)))
    open(TARGET, 'w', encoding='utf-8').write(doc)
    print('生成分类清单.html：%d 条' % len(rows))


if __name__ == '__main__':
    main()
