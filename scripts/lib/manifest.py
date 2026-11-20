#!/usr/bin/env python3
"""统一文献记录结构（对齐 academic-search 的 manifest 字段）。"""
import time

FIELDS = [
    'doi', 'title', 'year', 'authors', 'venue', 'issn', 'type',
    'cites', 'abstract', 'oa_pdf', 'landing', 'query',
    'level', 'level_source', 'final_level', 'final_source',
    'download', 'file', 'bytes', 'sha256', 'via',
]


def blank(doi=None, title=''):
    rec = {k: None for k in FIELDS}
    rec['doi'] = doi
    rec['title'] = title
    rec['download'] = 'not_requested'
    rec['fetched_at'] = time.strftime('%Y-%m-%d')
    return rec


def normalize(rec):
    """补齐缺失字段，保持键集合稳定。"""
    out = blank(rec.get('doi'), rec.get('title'))
    out.update({k: v for k, v in rec.items() if k in FIELDS or k == 'fetched_at'})
    out['download'] = rec.get('download') or 'not_requested'
    return out


def counts(records):
    from collections import Counter
    return dict(Counter(r.get('download') for r in records))
