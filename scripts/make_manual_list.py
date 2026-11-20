#!/usr/bin/env python3
"""生成待人工下载清单（按出版商分组，带可直接点的代理链接）。"""
import json
import os
import re
from collections import defaultdict

OUT = '/Users/ligenghao/Downloads/中南/自用论文2/论文'
META = os.path.join(OUT, 'metadata.json')
TARGET = os.path.join(OUT, '待人工下载直链.md')

PUB_NAME = {
    '10.1016': 'Elsevier / ScienceDirect', '10.1080': 'Taylor & Francis', '10.1007': 'Springer',
    '10.1111': 'Wiley', '10.1002': 'Wiley', '10.1109': 'IEEE Xplore', '10.1287': 'INFORMS',
    '10.1093': 'Oxford', '10.1017': 'Cambridge', '10.1142': 'World Scientific',
    '10.3390': 'MDPI (OA)', '10.2139': 'SSRN', '10.1145': 'ACM',
}


def proxy(path, host):
    return 'https://libvpn.zuel.edu.cn%s?__proto__=https&__host__=%s' % (path, host)


def main():
    meta = json.load(open(META, encoding='utf-8'))
    todo = [x for x in meta if x.get('download') != 'ok' and x.get('doi')]
    groups = defaultdict(list)
    for x in todo:
        doi = x['doi']
        pre = doi.split('/')[0]
        land = x.get('landing') or ''
        m = re.search(r'/pii/([A-Z0-9]+)', land)
        if pre == '10.1016' and m:
            url = proxy('/science/article/pii/' + m.group(1), 'www.sciencedirect.com')
        elif pre == '10.1007':
            url = proxy('/article/' + doi, 'link.springer.com')
        elif pre == '10.1080':
            url = proxy('/doi/full/' + doi, 'www.tandfonline.com')
        elif pre in ('10.1111', '10.1002'):
            url = proxy('/doi/pdfdirect/' + doi + '?download=true', 'onlinelibrary.wiley.com')
        else:
            url = 'https://doi.org/' + doi
        groups[pre].append((x.get('year'), x.get('title'), doi, url))

    lines = ['# 待人工下载（%d 条）' % len(todo), '',
             '按出版商分组。点链接 → 页面里点 **PDF / View PDF / Download**。', '']
    for pre, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        name = PUB_NAME.get(pre, pre)
        lines.append('## %s（%d 条）' % (name, len(items)))
        lines.append('')
        lines.append('| 年 | 标题 | DOI | 链接 |')
        lines.append('|---|---|---|---|')
        for y, t, doi, url in sorted(items, key=lambda z: -(z[0] or 0))[:80]:
            lines.append('| %s | %s | %s | %s |' % (y or '—', (t or '')[:56].replace('|', '/'), doi, url))
        lines.append('')
    open(TARGET, 'w', encoding='utf-8').write('\n'.join(lines))
    print('生成 %s，共 %d 条，%d 个出版商' % (TARGET, len(todo), len(groups)))


if __name__ == '__main__':
    main()
