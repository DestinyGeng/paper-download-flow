#!/usr/bin/env python3
"""生成进度看板 HTML：列出全部标题，已下载打勾，未下载给「打开」入口。"""
import html
import re
import urllib.parse
import json
import os
import time

import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import D as OUT
META = os.path.join(OUT, 'metadata.json')
TARGET = os.path.join(OUT, '进度看板.html')
ORDER = ['奠基·A+', '奠基·A', '奠基·A-', '奠基·B+', '奠基·B', '奠基·C',
         'A+', 'A', 'A-', 'B+', 'B', 'C', '未定']

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="10">
<title>文献进度看板</title>
<style>
body{font-family:-apple-system,"PingFang SC",sans-serif;margin:24px;background:#f7f8fa;color:#222}
h1{font-size:20px;margin:0 0 6px}
.sum{color:#555;margin-bottom:16px;font-size:14px}
.bar{height:10px;background:#e3e6ea;border-radius:5px;overflow:hidden;margin:8px 0 20px;max-width:520px}
.bar i{display:block;height:100%;background:#2e9e5b}
table{border-collapse:collapse;width:100%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.08)}
th,td{padding:7px 10px;border-bottom:1px solid #eef0f2;font-size:13px;text-align:left;vertical-align:top}
th{background:#fafbfc}
tr.todo td{color:#888}
td.mark{width:26px;text-align:center}
td.lv{width:44px;font-weight:600}
td.lang{width:38px;color:#666}
td.hit{width:110px}
td.venue{width:210px;color:#666}
td.year{width:52px}
span.tag.f{background:#fff3e0;color:#e67e22}
span.tag.m{background:#fdecea;color:#c0392b}
span.tag{display:inline-block;padding:1px 6px;margin-right:4px;background:#eef4ff;color:#2e6ce0;border-radius:3px;font-size:11px}
a.open{display:inline-block;padding:2px 10px;background:#2e6ce0;color:#fff;border-radius:4px;text-decoration:none;font-size:12px}
span.file{color:#2e9e5b;font-size:12px}
h2{font-size:15px;margin:26px 0 8px}
</style></head><body>
<h1>文献进度看板</h1>
<div class="sum">共 __TOTAL__ 条 ｜ 已下载 __OK__ ｜ 待下载 __TODO__ ｜ 完成度 __PCT__%</div>
<div class="bar"><i style="width:__PCT__%"></i></div>
<h2>已完成（__OK__）</h2>
<table>
<tr><th></th><th>评级</th><th>语种</th><th>命中</th><th>标题</th><th>期刊</th><th>年</th><th>文件</th></tr>
__ROWS_DONE__
</table>
<h2>待下载 · B 及以上（__TODO__）—— 点「打开」后手动下载</h2>
<p class="sum">另有 __EXCLUDED__ 条 C 级/无期刊信息的记录已隐藏</p>
<table>
<tr><th></th><th>评级</th><th>标题</th><th>期刊</th><th>年</th><th>操作</th></tr>
__ROWS_TODO__
</table>
</body></html>"""


def level_of(x):
    base = x.get('final_level') or x.get('level') or '未定'
    if x.get('foundational'):
        return '奠基·' + base
    return base


def link_of(x):
    doi = x.get('doi') or ''
    return ('https://doi.org/' + doi) if doi else (x.get('landing') or '')


def row(x, ok):
    lv = x['_lv']
    lang = '中' if (x.get('lang') == 'zh' or 'cnki' in (link_of(x) or '')) else '英'
    link = link_of(x)
    _t = x.get('title') or ''
    _hit = []
    if re.search(r'pair[s]?\s*trad|配对', _t, re.I): _hit.append('配对')
    if re.search(r'copula', _t, re.I): _hit.append('copula')
    if re.search(r'跨市场|cross.?market', _t, re.I): _hit.append('跨市场')
    if re.search(r'engle|granger', _t, re.I): _hit.append('EG')
    hit_n = len(_hit)
    tag_html = '<span class="tag">%d·%s</span>' % (hit_n, '+'.join(_hit)) if _hit else ''
    if x.get('foundational') and x.get('cites'):
        tag_html = '<span class="tag f">奠:%s引</span>' % x['cites'] + tag_html
    if (x.get('download') or '') == 'needs_manual':
        tag_html = '<span class="tag m">需手动</span>' + tag_html
    title = html.escape(_t[:110])
    venue = html.escape((x.get('venue') or '')[:40])
    year = x.get('year') or ''
    if ok:
        action = '<span class="file">%s</span>' % html.escape((x.get('file') or '')[:44])
    elif link:
        doi = (x.get('doi') or '').strip()
        if doi:
            action = '<a class="open" href="/open?doi=%s" target="_blank">打开</a>' % urllib.parse.quote(doi, safe='')
        else:
            action = '<a class="open" href="%s" target="_blank">打开</a>' % html.escape(link)
    else:
        action = '<span>无链接</span>'
    return ('<tr class="%s"><td class="mark">%s</td><td class="lv">%s</td><td class="lang">%s</td><td class="hit">%s</td><td>%s</td>'
            '<td class="venue">%s</td><td class="year">%s</td><td>%s</td></tr>'
            % ('done' if ok else 'todo', '✅' if ok else '⬜', html.escape(lv), lang, tag_html, title, venue, year, action))


def build():
    meta = json.load(open(META, encoding='utf-8'))
    for x in meta:
        x['_lv'] = level_of(x)
    done = sorted([x for x in meta if x.get('download') == 'ok'],
                  key=lambda x: (ORDER.index(x['_lv']) if x['_lv'] in ORDER else 9, -(x.get('year') or 0)))
    all_todo = [x for x in meta if x.get('download') not in ('ok', 'dropped')]
    todo = sorted(all_todo,
                  key=lambda x: (ORDER.index(x['_lv']) if x['_lv'] in ORDER else 9, -(x.get('year') or 0)))
    excluded = sum(1 for x in meta if x.get('download') == 'dropped')
    ok_n = len(done)
    total = ok_n + len(todo)
    pct = round(ok_n * 100.0 / total, 1) if total else 0
    doc = (TEMPLATE.replace('__TOTAL__', str(total)).replace('__OK__', str(ok_n))
           .replace('__TODO__', str(len(todo))).replace('__PCT__', str(pct))
           .replace('__EXCLUDED__', str(excluded))
           .replace('__TS__', time.strftime('%H:%M:%S'))
           .replace('__ROWS_DONE__', '\n'.join(row(x, True) for x in done))
           .replace('__ROWS_TODO__', '\n'.join(row(x, False) for x in todo)))
    open(TARGET, 'w', encoding='utf-8').write(doc)
    print('看板：%d 已完成 / %d 待下载 -> %s' % (ok_n, len(todo), TARGET))


if __name__ == '__main__':
    build()