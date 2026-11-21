#!/usr/bin/env python3
"""看板实时服务：metadata 变化时才重新生成，否则直接返回缓存。"""
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
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


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
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
