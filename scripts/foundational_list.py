#!/usr/bin/env python3
"""生成奠基论文清单（引用 >= 100），按引用排序，标注期刊等级。"""
import json, os, re, html
from collections import Counter

D = '/Users/ligenghao/Downloads/中南/自用论文2/论文'
GUIDE = '/Users/ligenghao/Downloads/中南/自用论文2/论文下载流/data/zuel-guide.json'
VER = '/Users/ligenghao/Downloads/中南/自用论文2/论文下载流/data/journal-verification.json'

def norm(t): return re.sub(r"[^0-9a-z]", "", (t or "").lower())

def load_levels():
    guide = json.load(open(GUIDE, encoding='utf-8'))
    ver = json.load(open(VER, encoding='utf-8')) if os.path.exists(VER) else {}
    out = {}
    for g in guide:
        if isinstance(g, dict) and g.get('cn'):
            out[norm(g['cn'])] = g.get('level')
    for issn, v in ver.items():
        if issn.startswith('name:') or not v.get('found'): continue
        z = v.get('zone') or ''; q = (v.get('jcr') or [None])[0]
        lv = 'A' if z == '1区' else ('B+' if q == 'Q1' else ('B' if z == '2区' else 'C'))
        out.setdefault(norm(issn), lv)
    return out

def cat(r):
    s = (r.get('title') or '').lower()
    if re.search(r'pair[s]?\s*trad|配对交易', s): return '配对交易'
    if 'copula' in s: return 'copula'
    if 'arbitrage' in s: return '统计套利 / 套利'
    if 'cointegrat' in s: return '协整方法（计量基础）'
    if 'mean revers' in s: return '均值回归'
    if 'spread' in s: return '价差 / 跨期'
    return '其他'

def main():
    rows = json.load(open('/tmp/foundational_filtered.json', encoding='utf-8'))
    lv = load_levels()
    for r in rows:
        r['_lv'] = lv.get(norm(r.get('issn')), '?')
        r['_cat'] = cat(r)
    pass
    order = ['配对交易', '统计套利 / 套利', 'copula', '协整方法（计量基础）', '均值回归', '价差 / 跨期', '其他']
    md = ["# 奠基论文清单（引用 >= 100）", "", "按引用量排序，不限期刊等级。", ""]
    parts = []
    for c in order:
        items = sorted([r for r in rows if r['_cat'] == c], key=lambda z: -z['cites'])
        if not items: continue
        md.append("## " + c + "（" + str(len(items)) + " 篇）")
        md.append("")
        md.append("| 引用 | 评级 | 年 | 标题 | 期刊 |")
        md.append("|---|---|---|---|---|")
        trs = []
        for r in items:
            doi = r.get('doi') or ''
            link = ('https://doi.org/' + doi) if doi else '#'
            t = html.escape((r.get('title') or '')[:100])
            v = html.escape((r.get('venue') or '')[:40])
            md.append("| " + str(r["cites"]) + " | " + str(r["_lv"]) + " | " + str(r.get("year") or "-") + " | " + (r.get("title") or "")[:56] + " | " + (r.get("venue") or "")[:26] + " |")
            trs.append("<tr><td class=cites>" + str(r["cites"]) + "</td><td><b>" + str(r["_lv"]) + "</b></td><td>" + str(r.get("year") or "-") + "</td><td><a href=\"" + link + "\" target=_blank>" + t + "</a></td><td class=venue>" + v + "</td></tr>")
        md.append("")
        parts.append("<h2>" + c + "（" + str(len(items)) + " 篇）</h2><table><tr><th>引用</th><th>评级</th><th>年</th><th>标题</th><th>期刊</th></tr>" + "".join(trs) + "</table>")
    open(os.path.join(D, "奠基论文清单.md"), "w", encoding="utf-8").write("\n".join(md))
    html_doc = "<!DOCTYPE html><html lang=zh-CN><head><meta charset=utf-8><title>奠基论文清单</title><style>body{font-family:-apple-system,PingFang SC,sans-serif;margin:24px;background:#f7f8fa;color:#222}h1{font-size:20px;margin:0 0 4px}h2{font-size:15px;margin:24px 0 6px}.sum{color:#555;margin-bottom:12px;font-size:13px}table{border-collapse:collapse;width:100%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.07);margin-bottom:8px}th,td{padding:6px 9px;border-bottom:1px solid #eef0f2;font-size:13px;text-align:left}th{background:#fafbfc}td.cites{width:64px;font-weight:700;color:#2e6ce0}td.venue{width:280px;color:#666}a{color:#222;text-decoration:none}a:hover{color:#2e6ce0}</style></head><body><h1>奠基论文清单（引用 ≥ 100）</h1><div class=sum>共 " + str(len(rows)) + " 篇 ｜ 按引用量排序 ｜ 不限期刊等级</div>" + "".join(parts) + "</body></html>"
    open(os.path.join(D, "奠基论文清单.html"), "w", encoding="utf-8").write(html_doc)
    print("生成完成:", len(rows), "篇")
    print(dict(Counter(r["_cat"] for r in rows)))

if __name__ == '__main__':
    main()
