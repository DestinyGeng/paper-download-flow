#!/usr/bin/env python3
"""重新生成 文献清单.md。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report import write_report

OUT = '/Users/ligenghao/Downloads/中南/自用论文2/论文'


def main():
    meta = json.load(open(os.path.join(OUT, 'metadata.json'), encoding='utf-8'))
    write_report(meta, OUT)


if __name__ == '__main__':
    main()
