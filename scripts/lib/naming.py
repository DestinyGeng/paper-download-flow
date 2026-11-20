#!/usr/bin/env python3
"""统一命名：文件名 = 标题（去非法字符、去中文"标题_作者"的作者）。"""
import re

_INVALID = re.compile(r'[\\/:*?"<>|\n\r\t]+')
_SPACES = re.compile(r'\s+')
_AUTHOR_TAIL = re.compile(r'_[一二-龥]{2,4}$')


def fname(title):
    t = (title or 'untitled').strip()
    t = _INVALID.sub(' ', t)
    t = _SPACES.sub(' ', t).strip(' .')
    t = _AUTHOR_TAIL.sub('', t)
    return (t[:80] or 'untitled') + '.pdf'


def unique(base, exists):
    """exists(name) -> bool；重名时追加 _v2/_v3。"""
    name = fname(base)
    if not exists(name):
        return name
    n = 1
    while True:
        n += 1
        cand = name[:-4] + '_v%d.pdf' % n
        if not exists(cand):
            return cand
