#!/usr/bin/env python3
"""Локальный HTTP-сервер: раздаёт torrents.html и обрабатывает /refresh."""

import http.server
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
BASE_DIR = Path(__file__).resolve().parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/refresh':
            return self.do_refresh()
        if parsed.path == '/' or parsed.path == '':
            return self.do_index()
        return super().do_GET()

    def do_index(self):
        index_path = BASE_DIR / 'torrents.html'
        if not index_path.exists():
            self.send_error(404, 'torrents.html не найден. Сначала запустите generate_page.py')
            return
        html = index_path.read_text('utf-8')
        # Вставляем кнопку обновления после строки с rating
        button = '<a class="rf" href="/refresh" title="Обновить данные с Pirate Bay" style="font-size:14px;margin-left:8px;text-decoration:none;cursor:pointer">🔄</a>'
        html = html.replace('</p>', f' {button}</p>', 1)
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def do_refresh(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write('<html><body><h2>Обновляю данные... (подождите)</h2><pre>'.encode())
        self.wfile.flush()
        proc = subprocess.Popen(
            [sys.executable, 'generate_page.py', '--refresh'],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        for line in proc.stdout:
            self.wfile.write(line.encode('utf-8'))
            self.wfile.flush()
        proc.wait()
        self.wfile.write('</pre><p><a href="/">Готово. Вернуться на главную</a></p></body></html>'.encode())


if __name__ == '__main__':
    print(f'Сервер запущен: http://localhost:{PORT}')
    print('Нажми Ctrl+C для остановки.')
    http_server = http.server.HTTPServer(('', PORT), Handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()
