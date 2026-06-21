#!/usr/bin/env python3
"""Локальный HTTP-сервер: раздаёт torrents.html и обрабатывает /refresh."""

import http.server
import json
import logging
import os
import subprocess
import sys
import threading
from html import escape
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PORT_ENV = 'SERVER_PORT'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get(PORT_ENV, os.environ.get('PORT', '8765')))
os.environ[PORT_ENV] = str(PORT)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'server.log'
SOURCE_KEYS = ('piratebay', 'tpbparty')
GENERATION_LOCK = threading.Lock()


def setup_logging():
    DATA_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger('thepirabay.server')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s [%(process)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        ))
        logger.addHandler(handler)
    return logger


LOGGER = setup_logging()


def get_source(parsed_url):
    qs = parse_qs(parsed_url.query)
    return qs.get('source', ['piratebay'])[0]


LAST_SOURCE_FILE = DATA_DIR / 'last_source.txt'


def get_last_source():
    try:
        with open(LAST_SOURCE_FILE, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def set_last_source(source):
    DATA_DIR.mkdir(exist_ok=True)
    with open(LAST_SOURCE_FILE, 'w') as f:
        f.write(source)


def generate_for_source(source, refresh=False):
    args = [sys.executable, '-u', 'generate_page.py', '--source', source]
    if refresh:
        args.append('--refresh')
    mode = 'refresh' if refresh else 'cache'
    LOGGER.info('Ожидание блокировки генерации: source=%s mode=%s', source, mode)
    with GENERATION_LOCK:
        LOGGER.info('Запуск генерации: source=%s mode=%s', source, mode)
        result = run_generator(args, source, mode, check=True)
    LOGGER.info('Генерация завершена: source=%s mode=%s returncode=%s', source, mode, result.returncode)
    return result


def run_generator(args, source, mode, check, stream=None):
    proc = subprocess.Popen(
        args,
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    output_lines = []
    for line in proc.stdout:
        output_lines.append(line)
        LOGGER.info('Генератор source=%s mode=%s: %s', source, mode, line.rstrip())
        if stream is not None:
            stream.write(line.encode('utf-8'))
            stream.flush()
    returncode = proc.wait()
    output = ''.join(output_lines)
    if check and returncode != 0:
        raise subprocess.CalledProcessError(returncode, args, output=output)
    return subprocess.CompletedProcess(args, returncode, stdout=output, stderr='')


def startup_sync_all_sources():
    LOGGER.info('Стартовая синхронизация всех источников начата: %s', ', '.join(SOURCE_KEYS))
    for source in SOURCE_KEYS:
        try:
            generate_for_source(source, refresh=True)
            set_last_source(source)
            LOGGER.info('Стартовая синхронизация источника завершена: source=%s', source)
        except subprocess.CalledProcessError as e:
            output = (e.stdout or '') + (e.stderr or '')
            LOGGER.error('Стартовая синхронизация источника завершилась ошибкой: source=%s returncode=%s output=\n%s',
                         source, e.returncode, output.rstrip())
        except Exception:
            LOGGER.exception('Необработанная ошибка стартовой синхронизации: source=%s', source)
    LOGGER.info('Стартовая синхронизация всех источников завершена')


def start_background_sync():
    thread = threading.Thread(target=startup_sync_all_sources, name='startup-sync', daemon=True)
    thread.start()
    return thread


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def log_message(self, format, *args):
        LOGGER.info('%s - %s', self.client_address[0], format % args)

    def do_GET(self):
        parsed = urlparse(self.path)
        LOGGER.info('GET %s', self.path)
        try:
            if parsed.path == '/refresh':
                return self.do_refresh(parsed)
            if parsed.path == '/' or parsed.path == '':
                return self.do_index(parsed)
            return super().do_GET()
        except Exception:
            LOGGER.exception('Необработанная ошибка при обработке GET %s', self.path)
            raise

    def do_index(self, parsed_url):
        source = get_source(parsed_url)
        index_path = BASE_DIR / 'torrents.html'
        last_source = get_last_source()

        if last_source != source or not index_path.exists():
            if GENERATION_LOCK.locked():
                self.send_response(202)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                safe_source = escape(source)
                safe_log = escape(str(LOG_FILE))
                html = (
                    '<html><body>'
                    '<h2>Синхронизация ещё идёт</h2>'
                    f'<p>Источник <strong>{safe_source}</strong> будет доступен после завершения текущей генерации.</p>'
                    f'<p><a href="/?source={safe_source}">Обновить страницу</a></p>'
                    f'<p>Лог: <code>{safe_log}</code></p>'
                    '</body></html>'
                )
                self.wfile.write(html.encode('utf-8'))
                return
            try:
                generate_for_source(source)
            except subprocess.CalledProcessError as e:
                output = (e.stdout or '') + (e.stderr or '')
                LOGGER.error('Ошибка генерации index: source=%s returncode=%s output=\n%s',
                             source, e.returncode, output.rstrip())
                self.send_error(500, f'Не удалось сгенерировать страницу: {output[-1000:]}')
                return
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
        LOGGER.info('Refresh запущен: source=%s', source)
        self.wfile.write(f'<html><body><h2>Обновляю данные... (подождите)</h2><pre>'.encode())
        self.wfile.flush()
        LOGGER.info('Ожидание блокировки refresh: source=%s', source)
        with GENERATION_LOCK:
            result = run_generator(
                [sys.executable, '-u', 'generate_page.py', '--refresh', '--source', source],
                source,
                'refresh',
                check=False,
                stream=self.wfile,
            )
            returncode = result.returncode
        if returncode == 0:
            LOGGER.info('Refresh завершён успешно: source=%s returncode=%s', source, returncode)
            set_last_source(source)
            self.wfile.write(f'</pre><p><a href="/?source={source}">Готово. Вернуться на главную</a></p></body></html>'.encode())
        else:
            LOGGER.error('Refresh завершён с ошибкой: source=%s returncode=%s', source, returncode)
            self.wfile.write(f'</pre><p>Ошибка генерации (код {returncode}).</p></body></html>'.encode())


if __name__ == '__main__':
    print(f'Сервер запущен: http://localhost:{PORT}')
    print(f'Лог сервера: {LOG_FILE}')
    print('Нажми Ctrl+C для остановки.')
    LOGGER.info('Сервер запущен: http://localhost:%s base_dir=%s log=%s', PORT, BASE_DIR, LOG_FILE)
    start_background_sync()
    http_server = http.server.ThreadingHTTPServer(('', PORT), Handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info('Сервер остановлен пользователем')
        http_server.server_close()
