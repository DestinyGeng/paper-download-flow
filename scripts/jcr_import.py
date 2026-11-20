#!/usr/bin/env python3
"""把 JCR 导出的 CSV 转成 classify.py 需要的输入。

用法：
    python3 jcr_import.py --csv ~/Downloads/jcr_export.csv --out refs/jcr.json

JCR 网页端的 Export 会给出期刊名、ISSN、JIF、JIF Quartile、Category 等列；
列名可能随版本变化，这里用模糊匹配，不写死。
"""
import argparse
import csv
import json
import os
import re
import sys


def pick(header, patterns):
    for pat in patterns:
        for col in header:
            if re.search(pat, col, re.I):
                return col
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        sys.exit('找不到文件: %s' % args.csv)

    with open(args.csv, encoding='utf-8-sig', newline='') as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit('CSV 为空')

    header = list(rows[0].keys())
    c_name = pick(header, [r'^journal name$', r'journal.*name', r'^title$'])
    c_issn = pick(header, [r'^issn$', r'issn$'])
    c_quart = pick(header, [r'jif.*quartile', r'^quartile', r'jcr.*quartile'])
    c_jif = pick(header, [r'jif$', r'^202\d jif', r'impact factor'])
    c_cat = pick(header, [r'^category$', r'categories'])
    c_abbr = pick(header, [r'jcr abbreviation', r'abbreviation'])

    if not c_name:
        sys.exit('列名里找不到期刊名，实际表头: %s' % header[:12])

    out = []
    for r in rows:
        name = (r.get(c_name) or '').strip()
        if not name:
            continue
        quart = (r.get(c_quart) or '').strip().upper() if c_quart else ''
        m = re.search(r'Q([1-4])', quart)
        out.append({
            'venue': name,
            'abbr': (r.get(c_abbr) or '').strip() if c_abbr else None,
            'issn': (r.get(c_issn) or '').strip() if c_issn else None,
            'jcr': 'Q%s' % m.group(1) if m else None,
            'jif': (r.get(c_jif) or '').strip() if c_jif else None,
            'category': (r.get(c_cat) or '').strip() if c_cat else None,
        })

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or '.', exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    have_q = sum(1 for x in out if x['jcr'])
    print(json.dumps({'rows': len(out), 'with_quartile': have_q,
                      'columns_used': {'name': c_name, 'quartile': c_quart,
                                       'issn': c_issn, 'jif': c_jif}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
