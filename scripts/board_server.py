#!/usr/bin/env python3
"""看板实时服务：/open?doi=xxx 记录「正在下载哪篇」并跳转，/ 返回看板。"""
import json
import os
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
PENDING = '/tmp/board_pending.json'
_last = {'mtime': 0, 'html': b''}


def html_now():
    try:
        m = os.path.getmtime(os.path.join(board.OUT, 'metadata.json'))
    except OSError:
        m = 0
    if m != _last['mtime'] or not _last['html']:
        try:
            board.build()
            _last['html'] = open(board.TARGET, 'rb').read()
            _last['mtime'] = m
        except Exception:
            pass
    return _last['html']


def find_link(doi):
    try:
        meta = json.load(open(os.path.join(board.OUT, 'metadata.json'), encoding='utf-8'))
    except Exception:
        return None
    for x in meta:
        if (x.get('doi') or '').lower() == doi.lower():
            return x.get('landing') or ('https://doi.org/' + doi), x.get('title')
    return None, None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/open'):
            q = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(q)
            doi = (params.get('doi') or [''])[0]
            link, title = find_link(doi) if doi else (None, None)
            if doi:
                json.dump({'doi': doi, 'title': title, 'ts': time.time()},
                          open(PENDING, 'w', encoding='utf-8'), ensure_ascii=False)
            target = link or ('https://doi.org/' + doi if doi else '/')
            self.send_response(302)
            self.send_header('Location', target)
            self.end_headers()
            return
        data = html_now()
        if not data:
            self.send_error(500, 'board not ready')
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    print('看板服务: http://127.0.0.1:%d/' % PORT, flush=True)
    HTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
