#!/usr/bin/env python3
"""看板实时服务：每次请求重新生成 HTML，保证数据最新。"""
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            board.build()
        except Exception:
            pass
        try:
            data = open(board.TARGET, 'rb').read()
        except Exception as exc:
            self.send_error(500, str(exc))
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
