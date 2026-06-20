#!/usr/bin/env python3
"""Локальный HTTP-сервер: раздаёт torrents.html и обрабатывает /refresh."""

import http.server
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
BASE_DIR = Path(__file__).resolve().parent


def get_source(parsed_url):
    qs = parse_qs(parsed_url.query)
    return qs.get('source', ['piratebay'])[0]


LAST_SOURCE_FILE = 'last_source.txt'


def get_last_source():
    try:
        with open(BASE_DIR / LAST_SOURCE_FILE, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def set_last_source(source):
    with open(BASE_DIR / LAST_SOURCE_FILE, 'w') as f:
        f.write(source)


def generate_for_source(source):
    subprocess.run(
        [sys.executable, 'generate_page.py', '--source', source],
        cwd=str(BASE_DIR),
        capture_output=True,
    )


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/refresh':
            return self.do_refresh(parsed)
        if parsed.path == '/' or parsed.path == '':
            return self.do_index(parsed)
        return super().do_GET()

    def do_index(self, parsed_url):
        source = get_source(parsed_url)
        index_path = BASE_DIR / 'torrents.html'
        last_source = get_last_source()

        if last_source != source or not index_path.exists():
            generate_for_source(source)
            set_last_source(source)
            if not index_path.exists():
                self.send_error(404, 'Не удалось сгенерировать страницу')
                return

        html = index_path.read_text('utf-8')
        button = f'<a class="rf" href="/refresh?source={source}" title="Обновить данные" style="font-size:14px;margin-left:8px;text-decoration:none;cursor:pointer">🔄</a>'
        html = html.replace('</span>', f'{button}</span>', 1)
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def do_refresh(self, parsed_url):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        source = get_source(parsed_url)
        self.wfile.write(f'<html><body><h2>Обновляю данные... (подождите)</h2><pre>'.encode())
        self.wfile.flush()
        proc = subprocess.Popen(
            [sys.executable, 'generate_page.py', '--refresh', '--source', source],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        for line in proc.stdout:
            self.wfile.write(line.encode('utf-8'))
            self.wfile.flush()
        proc.wait()
        self.wfile.write(f'</pre><p><a href="/?source={source}">Готово. Вернуться на главную</a></p></body></html>'.encode())


if __name__ == '__main__':
    print(f'Сервер запущен: http://localhost:{PORT}')
    print('Нажми Ctrl+C для остановки.')
    http_server = http.server.HTTPServer(('', PORT), Handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()
