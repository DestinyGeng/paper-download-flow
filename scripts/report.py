#!/usr/bin/env python3
"""生成 文献清单.md：元数据 + 摘要 + 评级。"""
import os


def write_report(state, outdir):
    good = [x for x in state if x.get('download') == 'ok']
    good.sort(key=lambda x: (-(x.get('cites') or 0)))
    rows = ['| # | 年份 | 标题 | 第一作者 | 期刊 | DOI | 评级 | 中文摘要 | 文件 |',
            '|---|---|---|---|---|---|---|---|---|']
    for i, x in enumerate(good, 1):
        authors = x.get('authors') or []
        first = authors[0] if authors else '—'
        lvl = x.get('level') or '待核'
        if x.get('level_source') != 'guide':
            lvl += '?'
        rows.append('| %d | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            i, x.get('year') or '—',
            (x.get('title') or '')[:80].replace('|', '/'),
            first[:24],
            (x.get('venue') or '—')[:28].replace('|', '/'),
            x.get('doi') or '—', lvl,
            (x.get('zh_abstract') or '—').replace('|', '/'),
            x.get('file') or ''))
    body = ['# 文献清单（自动采集）', '',
            '共 %d 篇下载成功。评级依据校定指南，带 ? 表示指南未列、需 JCR 复核。' % len(good),
            '', '## 索引', ''] + rows + ['', '## 逐篇摘要', '']
    for i, x in enumerate(good, 1):
        body.append('### %d. %s' % (i, x.get('title') or ''))
        body.append('')
        body.append('- 年份：%s ｜ 期刊：%s ｜ DOI：%s' % (
            x.get('year') or '—', x.get('venue') or '—', x.get('doi') or '—'))
        body.append('- 评级：**%s**%s' % (
            x.get('level') or '待核',
            '（指南列出）' if x.get('level_source') == 'guide' else '（指南未列，需 JCR）'))
        body.append('- 摘要：%s' % (x.get('zh_abstract') or (x.get('abstract') or '无摘要')[:180]))
        body.append('')
    open(os.path.join(outdir, '文献清单.md'), 'w', encoding='utf-8').write('\n'.join(body))
    print('report: 文献清单.md %d 篇' % len(good), flush=True)