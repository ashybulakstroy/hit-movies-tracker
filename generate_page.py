#!/usr/bin/env python3
"""Генерирует HTML-страницу с торрентами, рейтингом IMDB и ссылками на трейлеры."""

import gzip
import io
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from html import escape

import requests
from bs4 import BeautifulSoup

CATEGORY_URL = "https://1.piratebays.to/top/207"
RATINGS_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
BASICS_URL = "https://datasets.imdbws.com/title.basics.tsv.gz"
PAGE_CACHE = "piratebay_page.html"
RATINGS_CACHE = "imdb_ratings_cache.json"
BASICS_CACHE = "imdb_basics_cache.json"
SEARCH_CACHE = "imdb_search_cache.json"
YOUTUBE_CACHE = "youtube_cache.json"
OUTPUT_FILE = "torrents.html"
TORRENTS_CACHE = "torrents_data.json"
POSTERS_DIR = "posters"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def fetch(url):
    r = SESSION.get(url, timeout=15)
    r.raise_for_status()
    return r.text


def load_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clean_title(raw):
    t = raw.strip()
    t = re.sub(r'^tt\d+\s*', '', t)
    t = re.sub(r'\s*\[.*?\]', '', t)
    # Год в скобках или просто четырёхзначный год
    year_m = re.search(r'\((\d{4})\)', t) or re.search(r'\b(19\d{2}|20\d{2})\b', t)
    year = year_m.group(1) if year_m else ''
    t = re.sub(r'\s*\(\d{4}\)\s*', ' ', t)
    t = re.sub(r'\(.*?\)', ' ', t)
    t = re.sub(r'\[.*?\]', ' ', t)
    t = re.sub(r'(?i)\b(1080p|720p|2160p|480p|WEBRip|WEB-DL|WEB|BluRay|BRRip|HDRip|DVDRip|DCPRip|'
               r'x264|x265|h264|h265|HEVC|AVC|AAC|AC3|DDP|DTS|MP4|MKV|AVI|'
               r'10bit|8bit|5\s*[. ]\s*1|2\s*[. ]\s*0|6CH|'
               r'REPACK|PROPER|READNFO|iNTERNAL|EXTENDED|UNRATED|DC|FINAL|COMPLETE|'
               r'YTS|RARBG|RMTeam|NeoNoir|SupaCvnt|FLUX|BTM|'
               r'WEBRip|WEB\s*[.-]\s*DL|WEB\s*Line|AMZN|DSNP|NF|MA|PMNTP|PLAY|Early\s*Release'
               r')\b', ' ', t, flags=re.I)
    t = re.sub(r'[._]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'\s*-\s*\w+$', '', t)
    t = re.sub(r'\s*[─╌-]\s*\w+$', '', t)
    t = re.sub(r'(?i)\b(LEAK|PLAY|DUAL|LINKS|SCREENER|TS|CAM|HDRip)\b', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t, year


def search_imdb(title, year):
    first_char = title[0].lower()
    url = f"https://v2.sg.media-imdb.com/suggestion/{first_char}/{urllib.parse.quote(title)}.json"
    try:
        r = SESSION.get(url, timeout=8)
        data = r.json()
        items = [it for it in data.get('d', []) if it.get('id', '').startswith('tt')]
        if not items:
            return None
        best = items[0]
        if year:
            exact = next((it for it in items if str(it.get('y')) == str(year)), None)
            if exact:
                best = exact
        img = ''
        img_data = best.get('i')
        if img_data:
            if isinstance(img_data, dict):
                img = img_data.get('imageUrl', '')
            elif isinstance(img_data, list) and len(img_data) > 0:
                img = img_data[0].get('imageUrl', '')
        return {'id': best['id'], 'poster': img, 'cast': best.get('s', '')}
    except Exception:
        return None


def clean_title_deep(raw):
    """Агрессивная очистка названия: удаляет всё, кроме имени и года."""
    t = raw.strip()
    # Удаляем хеши/ID в начале
    t = re.sub(r'^[a-fA-F0-9]{32,40}\s+', '', t)
    t = re.sub(r'^tt\d+\s*', '', t)
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'\(.*?\)', '', t)
    # Удаляем расширения и технические теги
    t = re.sub(r'(?i)\.(mp4|mkv|avi|m4v|webm|ts|m2ts)', ' ', t)
    t = re.sub(r'[._]', ' ', t)
    # Удаляем группы релизов в конце после - (тире)
    t = re.sub(r'\s*-\s*\S+$', '', t)
    # Удаляем качество, кодеки, источники
    t = re.sub(r'(?i)\b(1080p|720p|2160p|480p|WEBRip|WEB-DL|WEB|BluRay|BRRip|HDRip|DVDRip|'
               r'DCPRip|HDTS|HDRip|CAM|TS|TC|TELESYNC|'
               r'x264|x265|h264|h265|HEVC|AVC|AAC|AC3|DDP|DTS|MP4|MKV|AVI|'
               r'10bit|8bit|5[.\s]+1|2[.\s]+0|6CH|7CH|'
               r'REPACK|PROPER|READNFO|iNTERNAL|EXTENDED|UNRATED|DC|FINAL|COMPLETE|'
               r'YTS|RARBG|RMTeam|NeoNoir|SupaCvnt|FLUX|BTM|'
               r'WEBRip|WEB[.\s-]*DL|WEB\s*Line|AMZN|DSNP|NF|MA|PMNTP|PLAY|'
               r'Early\s*Release|VOSTFR|MULTi|DUAL|Line\s*Audio|'
               r'LEAK|PLAY|LINKS|SCREENER|HDRip|'
               r'BONE|SCOPE|UNiON|FS|BYNDR|Rapta|SyncUP|Asiimov|GalaxyRG|'
               r'HDTS|TELESYNC|VOSTFR|MULTi|DUAL|'
               r'10bits|YTS|YIFY|RARBG|RMTeam|NeoNoir)'
               r'\s*', ' ', t, flags=re.I)
    # Удаляем звёздочки и эмодзи
    t = re.sub(r'[⭐★☆\-—─╌●•·]', ' ', t)
    # Удаляем слова до года и после
    year_m = re.search(r'\b(19\d{2}|20\d{2})\b', t)
    year = year_m.group(1) if year_m else ''
    # Если есть год — берём всё до года + год
    if year:
        idx = t.find(year)
        before = t[:idx].strip()
        # Оставляем только 2-3 значимых слова до года
        words = before.split()
        # Если много слов, оставляем только значащие (не слишком короткие)
        before = ' '.join(words)
        t = f'{before} {year}'
    else:
        # Если нет года — берём первые 4 слова
        words = [w for w in t.split() if len(w) > 1]
        t = ' '.join(words[:4])
    t = re.sub(r'\s+', ' ', t).strip()
    return t, year


def search_imdb_deep(raw_name):
    """Расширенный поиск IMDB: несколько попыток с разной очисткой названия."""
    title, year = clean_title_deep(raw_name)
    queries = [title]

    # Варианты: без года, короче
    if year:
        queries.append(title.replace(f' {year}', '').strip())
    # Если название длинное — пробуем первую половину
    words = title.split()
    if len(words) > 4:
        queries.append(' '.join(words[:3]))
        if year:
            queries.append(f'{" ".join(words[:3])} {year}')
    # Если название всё ещё не короткое — пробуем первые 2 слова
    if len(words) > 5:
        queries.append(' '.join(words[:2]))

    for q in queries:
        if not q:
            continue
        first_char = q[0].lower()
        url = f"https://v2.sg.media-imdb.com/suggestion/{first_char}/{urllib.parse.quote(q)}.json"
        try:
            r = SESSION.get(url, timeout=8)
            data = r.json()
            items = [it for it in data.get('d', []) if it.get('id', '').startswith('tt')]
            if not items:
                continue
            # Сначала ищем точное совпадение по году
            if year:
                exact = next((it for it in items if str(it.get('y')) == str(year)), None)
                if exact:
                    return _parse_imdb_result(exact)
            # Иначе берём первый результат
            best = items[0]
            result = _parse_imdb_result(best)
            return result
        except Exception:
            continue
    return None


def _parse_imdb_result(item):
    img_data = item.get('i')
    img = ''
    if img_data:
        if isinstance(img_data, dict):
            img = img_data.get('imageUrl', '')
        elif isinstance(img_data, list) and len(img_data) > 0:
            img = img_data[0].get('imageUrl', '')
    return {'id': item['id'], 'poster': img, 'cast': item.get('s', '')}


def search_imdb_ids(torrents):
    total = len(torrents)
    imdb_cache = load_json(SEARCH_CACHE) or {}

    for i, t in enumerate(torrents, 1):
        title, year = t['movie_title'], t['movie_year']
        raw_name = t['name']
        if not title:
            continue
        cache_key = f"{title}|{year}".lower()

        result = None
        if cache_key in imdb_cache and imdb_cache[cache_key] is not None:
            result = imdb_cache[cache_key]
        else:
            print(f"  [{i}/{total}] {title}...", end=' ', flush=True)
            result = search_imdb(title, year)
            if result is None:
                deep_cache_key = f"deep:{raw_name.lower().strip()}"
                if deep_cache_key in imdb_cache and imdb_cache[deep_cache_key] is not None:
                    result = imdb_cache[deep_cache_key]
                else:
                    result = search_imdb_deep(raw_name)
                    if result is not None:
                        imdb_cache[deep_cache_key] = result
            if result is not None:
                imdb_cache[cache_key] = result
                save_json(SEARCH_CACHE, imdb_cache)
            time.sleep(0.1)

        if result:
            if isinstance(result, str):
                imdb_id = result
                poster, cast = '', ''
            else:
                imdb_id = result.get('id')
                poster = result.get('poster', '')
                cast = result.get('cast', '')
            t['imdb_id'] = imdb_id
            t['poster_url'] = download_poster(imdb_id, poster) if poster else ''
            t['cast'] = cast
            print(f"ID {imdb_id}", end='')
        else:
            print("не найдено", end='')

        print()

    return torrents


def fetch_imdb_rating(imdb_id):
    """Парсит рейтинг, жанр, постер со страницы IMDB для фильмов без рейтинга в датасете."""
    if not imdb_id:
        return {}
    url = f"https://www.imdb.com/title/{imdb_id}/"
    try:
        r = SESSION.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        if r.status_code != 200:
            return {}
        html = r.text
        result = {}
        # Рейтинг
        m = re.search(r'"ratingValue"\s*:\s*"([\d.]+)"', html)
        if m:
            result['rating'] = m.group(1)
        # Количество голосов
        m = re.search(r'"ratingCount"\s*:\s*(\d+)', html)
        if m:
            result['votes'] = m.group(1)
        # Жанры
        genres = re.findall(r'"genre"\s*:\s*"([^"]+)"', html)
        if genres:
            result['genres'] = ','.join(genres)
        # Постер
        m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
        if m:
            result['poster'] = m.group(1)
        return result
    except Exception:
        return {}


def search_youtube_trailer(title, year):
    query = f"{title} {year} official trailer"
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    try:
        r = SESSION.get(url, timeout=10)
        m = re.search(r'/watch\?v=([a-zA-Z0-9_-]{11})', r.text)
        if m:
            return f"https://www.youtube.com/watch?v={m.group(1)}"
    except Exception:
        pass
    return None


def download_poster(imdb_id, url):
    if not imdb_id or not url:
        return ''
    os.makedirs(POSTERS_DIR, exist_ok=True)
    ext = os.path.splitext(url.split('/')[-1].split('@')[0])[0] or 'jpg'
    local_path = f"{POSTERS_DIR}/{imdb_id}.jpg"
    if os.path.exists(local_path):
        return local_path
    try:
        r = SESSION.get(url, timeout=15)
        if r.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(r.content)
            return local_path
    except Exception:
        pass
    return url


def parse_pirate_date(raw):
    now = datetime.now(timezone.utc)
    raw = raw.strip()

    # YYYY-MM-DD HH:MM
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})', raw)
    if m:
        dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                      int(m.group(4)), int(m.group(5)), tzinfo=timezone.utc)
        return dt.timestamp()

    # Today HH:MM
    m = re.match(r'^(?:Today|Сегодня)\s+(\d{1,2}):(\d{2})', raw)
    if m:
        dt = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        return dt.timestamp()

    # Y-day / Yesterday / Вчера HH:MM
    m = re.match(r'^(?:Y[- ]?day|Yesterday|Вчера)\s+(\d{1,2}):(\d{2})', raw)
    if m:
        dt = (now - timedelta(days=1)).replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        return dt.timestamp()

    # MM-DD HH:MM (current year)
    m = re.match(r'^(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})', raw)
    if m:
        dt = datetime(now.year, int(m.group(1)), int(m.group(2)),
                      int(m.group(3)), int(m.group(4)), tzinfo=timezone.utc)
        return dt.timestamp()

    # X mins/hours/days ago
    m = re.match(r'(\d+)\s+(min|mins|minute|minutes)', raw)
    if m:
        return (now - timedelta(minutes=int(m.group(1)))).timestamp()
    m = re.match(r'(\d+)\s+(hour|hours)', raw)
    if m:
        return (now - timedelta(hours=int(m.group(1)))).timestamp()
    m = re.match(r'(\d+)\s+(day|days)', raw)
    if m:
        return (now - timedelta(days=int(m.group(1)))).timestamp()
    m = re.match(r'(\d+)\s+(week|weeks)', raw)
    if m:
        return (now - timedelta(weeks=int(m.group(1)))).timestamp()

    return 0


def load_ratings(needed_ids, refresh=False):
    cached = load_json(RATINGS_CACHE) or {}
    if not refresh and cached and needed_ids.issubset(cached.keys()):
        return {k: v for k, v in cached.items() if k in needed_ids}
    try:
        print("Скачиваю IMDB ratings dataset (~8MB)...")
        r = SESSION.get(RATINGS_URL, stream=True, timeout=120)
        r.raise_for_status()
        keep_ids = needed_ids
        if not refresh and cached:
            keep_ids = set(cached.keys()) | needed_ids
        ratings = {}
        buf = io.BytesIO(r.content)
        with gzip.GzipFile(fileobj=buf, mode='rb') as gz:
            with io.TextIOWrapper(gz, encoding='utf-8') as f:
                f.readline()
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        tid = parts[0]
                        if tid in keep_ids:
                            ratings[tid] = {'rating': parts[1], 'votes': parts[2]}
        if not refresh and cached:
            ratings = {**cached, **ratings}
        save_json(RATINGS_CACHE, ratings)
        return {k: v for k, v in ratings.items() if k in needed_ids}
    except Exception as e:
        print(f"   Не удалось скачать ratings: {e}")
        if cached:
            return {k: v for k, v in cached.items() if k in needed_ids}
        return {}


def load_basics(needed_ids, refresh=False):
    cached = load_json(BASICS_CACHE) or {}
    if not refresh and cached and needed_ids.issubset(cached.keys()):
        return {k: v for k, v in cached.items() if k in needed_ids}
    try:
        print("Скачиваю IMDB basics dataset (жанры, ~8MB)...")
        r = SESSION.get(BASICS_URL, stream=True, timeout=120)
        r.raise_for_status()
        keep_ids = needed_ids
        if not refresh and cached:
            keep_ids = set(cached.keys()) | needed_ids
        basics = {}
        buf = io.BytesIO(r.content)
        with gzip.GzipFile(fileobj=buf, mode='rb') as gz:
            with io.TextIOWrapper(gz, encoding='utf-8') as f:
                f.readline()
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 9:
                        tid = parts[0]
                        g = parts[8] if parts[8] != r'\N' else ''
                        if tid in keep_ids:
                            basics[tid] = {'type': parts[1], 'genres': g}
        if not refresh and cached:
            basics = {**cached, **basics}
        save_json(BASICS_CACHE, basics)
        return {k: v for k, v in basics.items() if k in needed_ids}
    except Exception as e:
        print(f"   Не удалось скачать basics: {e}")
        if cached:
            return {k: v for k, v in cached.items() if k in needed_ids}
        return {}


def load_page(refresh=False):
    if refresh or not os.path.exists(PAGE_CACHE):
        print(f"Загружаю Pirate Bay...")
        html = fetch(CATEGORY_URL)
        with open(PAGE_CACHE, 'w', encoding='utf-8') as f:
            f.write(html)
        return html
    with open(PAGE_CACHE, 'r', encoding='utf-8') as f:
        return f.read()


def parse_torrents(html):
    soup = BeautifulSoup(html, 'html.parser')
    torrents = []
    rows = soup.select('#searchResult tbody tr')
    for row in rows:
        name_el = row.select_one('a.detLink')
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        tds = row.find_all('td')
        cat_el = row.select_one('.vertTh a')
        category = cat_el.get_text(strip=True) if cat_el else ''
        uploaded = tds[2].get_text(strip=True) if len(tds) > 2 else ''
        size = tds[4].get_text(strip=True) if len(tds) > 4 else ''
        seeders = tds[5].get_text(strip=True) if len(tds) > 5 else '0'
        leechers = tds[6].get_text(strip=True) if len(tds) > 6 else '0'
        uploader_el = tds[7].select_one('a') if len(tds) > 7 else None
        uploader = uploader_el.get_text(strip=True) if uploader_el else ''
        magnet_el = row.select_one('a[href^="magnet:"]')
        magnet = magnet_el['href'] if magnet_el else ''
        detail_el = row.select_one('a.detLink')
        detail_url = 'https://1.piratebays.to' + detail_el['href'] if detail_el and detail_el.get('href') else ''

        movie_title, movie_year = clean_title(name)

        torrents.append({
            'name': name,
            'movie_title': movie_title,
            'movie_year': movie_year,
            'category': category,
            'uploaded': uploaded,
            'uploaded_ts': parse_pirate_date(uploaded),
            'size': size,
            'seeders': int(seeders.replace(',', '') or 0),
            'leechers': int(leechers.replace(',', '') or 0),
            'uploader': uploader,
            'magnet': magnet,
            'detail_url': detail_url,
            'imdb_id': None,
            'imdb_rating': None,
            'imdb_votes': None,
            'genre': '',
            'poster_url': '',
            'cast': '',
            'youtube_url': None,
        })
    return torrents


def enrich(torrents, ratings, basics):
    total = len(torrents)
    yt_cache = load_json(YOUTUBE_CACHE) or {}

    for i, t in enumerate(torrents, 1):
        title, year = t['movie_title'], t['movie_year']
        if not title:
            continue
        cache_key = f"{title}|{year}".lower()
        imdb_id = t.get('imdb_id')

        print(f"  [{i}/{total}] {title}...", end=' ', flush=True)

        if imdb_id:
            genre = basics.get(imdb_id, {}).get('genres', '')
            if not genre:
                rating_data = fetch_imdb_rating(imdb_id)
                if rating_data.get('genres'):
                    genre = rating_data['genres']
                if not t.get('poster_url') and rating_data.get('poster'):
                    t['poster_url'] = download_poster(imdb_id, rating_data['poster'])
                if rating_data.get('rating'):
                    t['imdb_rating'] = rating_data['rating']
                    t['imdb_votes'] = rating_data.get('votes', '')
                    print(f"IMDB {rating_data['rating']} (scraped)", end='')
            t['genre'] = genre

            if imdb_id in ratings:
                t['imdb_rating'] = ratings[imdb_id]['rating']
                t['imdb_votes'] = ratings[imdb_id]['votes']
                print(f"IMDB {ratings[imdb_id]['rating']}", end='')
            elif not t.get('imdb_rating'):
                print(f"ID {imdb_id} — нет рейтинга", end='')

        if cache_key in yt_cache:
            t['youtube_url'] = yt_cache[cache_key]
        else:
            yt_url = search_youtube_trailer(title, year)
            t['youtube_url'] = yt_url
            yt_cache[cache_key] = yt_url
            save_json(YOUTUBE_CACHE, yt_cache)
            if yt_url:
                print(f", трейлер ✓", end='')
            time.sleep(0.1)

        print()

    return torrents


def generate_html(torrents):
    rows = []
    tiles = []

    for t in torrents:
        rating = t['imdb_rating'] or '—'
        rating_cls = ''
        if t['imdb_rating']:
            r = float(t['imdb_rating'])
            rating_cls = 'rh' if r >= 8 else 'rm' if r >= 7 else 'rl'
        imdb_url = f"https://www.imdb.com/title/{t['imdb_id']}/" if t['imdb_id'] else '#'
        trailer_q = urllib.parse.quote(f"{t['movie_title']} {t['movie_year']} official trailer")
        trailer_url = t.get('youtube_url') or f"https://www.youtube.com/results?search_query={trailer_q}"
        votes_str = f" ({t['imdb_votes']})" if t['imdb_votes'] else ''
        votes_title = f' title="{t["imdb_votes"]} голосов"' if t['imdb_votes'] else ''
        date_ts = t.get('uploaded_ts', 0)
        clean_t = escape(t['movie_title'].lower().strip())

        poster = t.get('poster_url', '') or ''
        cast_str = t.get('cast', '') or ''
        genre = t.get('genre', '') or ''
        poster_html = f'<div class="pc" data-yt="{escape(trailer_url)}" onclick="pt(this)"><img src="{escape(poster)}" class="ps" alt=""><span class="pb">▶</span></div>' if poster else ''
        cast_html = f'<p class="ca">{escape(cast_str)}</p>' if cast_str else ''
        genre_html = f'<p class="gn">{escape(genre)}</p>' if genre else ''
        esize = escape(t['size'])

        rows.append(f'''<tr data-date="{date_ts}" data-title="{clean_t}" data-genre="{escape(genre.lower())}">
<td><a href="{escape(t['detail_url'])}" class="tn" target="_blank">{escape(t['name'])}</a>
<div class="ml">
<span class="tg" onclick="td(this)">+</span>
<span class="un">{escape(t['uploader'])}</span>
<a href="{trailer_url}" onclick="window.open(this.href,'tr','width=960,height=540,menubar=no,toolbar=no,location=no');return false" class="bt">▶ Трейлер</a>
<a href="{imdb_url}" target="_blank"{votes_title}><span class="rb {rating_cls}">IMDB {escape(str(rating))}{escape(votes_str)}</span></a>
<span class="rmv" onclick="hm(this)">✕</span>
</div>
<div class="dtc" style="display:none"><div class="dc">{poster_html}<div class="dx">{genre_html}<div class="rbi"><span class="rb {rating_cls}">IMDB {escape(str(rating))}{escape(votes_str)}</span></div>{cast_html}</div></div></div>
</td>
<td>{esize}</td>
<td>{escape(t['uploaded'])}</td>
<td><a href="{escape(t['magnet'])}" class="bm">🧲</a></td>
</tr>''')

        poster_card = f'<div class="pc" data-yt="{escape(trailer_url)}" onclick="pt(this)"><img src="{escape(poster)}" class="tps" alt=""><span class="pb">▶</span></div>' if poster else ''
        cast_short = escape(cast_str)[:120] + '…' if len(cast_str) > 120 else escape(cast_str)

        tiles.append(f'''<div class="tile-card" data-date="{date_ts}" data-title="{clean_t}" data-genre="{escape(genre.lower())}">
{poster_card}
<div class="tile-body">
<a href="{escape(t['detail_url'])}" class="tile-title" target="_blank">{escape(t['name'])}</a>
<div class="tile-info">
<span class="rb {rating_cls}">IMDB {escape(str(rating))}</span>
{'' if not genre else f'<span class="tile-genre">{escape(genre)}</span>'}
</div>
{'' if not cast_short else f'<div class="tile-cast">{cast_short}</div>'}
<div class="tile-actions">
<a href="{trailer_url}" onclick="window.open(this.href,'tr','width=960,height=540,menubar=no,toolbar=no,location=no');return false" class="bt">▶ Трейлер</a>
<a href="{escape(t['magnet'])}" class="bm">🧲</a>
<a href="{imdb_url}" target="_blank" class="tile-imdb">IMDB</a>
<span class="rmv" onclick="htm(this)">✕</span>
</div>
</div>
</div>''')

    with_r = sum(1 for t in torrents if t['imdb_rating'])

    html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>HD-Movies Top 100 + IMDB</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#fff;color:#1a1a1a;padding:20px}}
.c{{max-width:1200px;margin:0 auto}}
h1{{font-size:28px;margin-bottom:4px;color:#1a1a1a}}
.sub{{color:#666;margin-bottom:20px;font-size:13px}}
.sub a{{color:#1a73e8}}
.sub .tv{{display:inline-block;padding:2px 8px;font-size:11px;font-weight:600;color:#fff;background:#1a73e8;border-radius:4px;cursor:pointer;user-select:none;margin-left:8px;border:none;vertical-align:middle}}
.sub .tv:hover{{background:#1557b0}}
table{{width:100%;border-collapse:collapse}}
th{{position:sticky;top:0;background:#f5f5f5;padding:12px 16px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:#666;border-bottom:2px solid #e0e0e0;cursor:pointer;user-select:none}}
th:hover{{background:#e8e8e8}}
th .ar{{font-size:10px;margin-left:4px}}
tr{{border-bottom:1px solid #eee;transition:background .15s}}
tr:hover{{background:#f9f9f9}}
td{{padding:12px 16px;font-size:14px;vertical-align:middle}}
.tg{{display:inline-block;width:20px;height:20px;line-height:18px;text-align:center;font-size:14px;font-weight:700;color:#666;border:1px solid #ccc;border-radius:3px;cursor:pointer;vertical-align:middle;margin-right:8px;user-select:none;background:#f0f0f0;flex-shrink:0}}
.tg:hover{{background:#ddd;border-color:#999}}
.dtc{{border-top:1px solid #e0e0e0;margin-top:8px;padding-top:8px}}
.dc{{display:flex;gap:16px;align-items:flex-start}}
.ps{{max-width:360px;border-radius:4px;flex-shrink:0;display:block}}
.pc{{position:relative;display:inline-block;flex-shrink:0;cursor:pointer;line-height:0}}
.pb{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:64px;color:rgba(255,255,255,0.85);text-shadow:0 0 20px rgba(0,0,0,0.6);transition:color .2s,transform .2s;pointer-events:none}}
.pc:hover .pb{{color:#fff;transform:translate(-50%,-50%) scale(1.1)}}
.dx{{flex:1}}
.dx .rbi{{margin-bottom:8px}}
.gn{{font-size:36px;color:#888;margin-bottom:6px}}
.ca{{font-size:39px;color:#555;line-height:1.5;margin:0}}
.tn{{color:#1a73e8;text-decoration:none;font-weight:600;display:block;margin-bottom:2px;line-height:1.4;font-size:28px}}
.tn:hover{{text-decoration:underline}}
.ml{{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:4px 0 8px}}
.bt{{display:inline-block;padding:2px 8px;font-size:11px;font-weight:600;color:#fff;background:#da3633;border-radius:4px;text-decoration:none;white-space:nowrap}}
.bt:hover{{background:#b62324}}
.rb{{display:inline-block;padding:2px 8px;font-size:11px;font-weight:700;border-radius:4px;white-space:nowrap;text-decoration:none}}
.rbi .rb{{font-size:33px}}
.rh{{background:#f5c518;color:#000}}
.rm{{background:#b0881a;color:#fff}}
.rl{{background:#e0e0e0;color:#666}}
.un{{font-size:12px;color:#888}}
.rmv{{display:inline-block;width:18px;height:18px;line-height:16px;text-align:center;font-size:11px;font-weight:700;color:#fff;background:#da3633;border-radius:3px;cursor:pointer;user-select:none;flex-shrink:0;margin-left:6px}}
.rmv:hover{{background:#b62324}}
.bm{{font-size:16px;text-decoration:none;color:#333}}
.st{{margin:16px 0;padding:12px 16px;background:#f5f5f5;border-radius:6px;font-size:13px;color:#666;border:1px solid #e0e0e0}}
.tile-grid{{display:none;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}}
.tile-card{{border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;transition:box-shadow .2s}}
.tile-card:hover{{box-shadow:0 2px 12px rgba(0,0,0,.1)}}
.tps{{width:100%;display:block;border-radius:0}}
.tile-body{{padding:8px 10px}}
.tile-title{{font-size:20px;font-weight:600;color:#1a73e8;text-decoration:none;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:1.3;margin-bottom:4px}}
.tile-title:hover{{text-decoration:underline}}
.tile-info{{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:4px}}
.tile-genre{{font-size:18px;color:#888}}
.tile-cast{{font-size:18px;color:#555;line-height:1.4;margin-bottom:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.tile-actions{{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:4px}}
.tile-imdb{{font-size:18px;color:#555;text-decoration:none}}
.tile-imdb:hover{{text-decoration:underline}}
body.tile table{{display:none}}
body.tile .tile-grid{{display:grid}}
body.tile .st{{display:none}}
@media(max-width:768px){{table,thead,tbody,tr,td,th{{display:block}}thead{{display:none}}td{{padding:6px 10px}}tr{{padding:10px 0}}.tile-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="c">
<div class="sub">
<span>Источник: <a href="{escape(CATEGORY_URL)}" target="_blank">{escape(CATEGORY_URL)}</a>
• Всего: <strong>{len(torrents)}</strong> торрентов
• С рейтингом: <strong>{with_r}</strong></span>
<span class="tv" onclick="tv()" id="tvb">Вид: плитка</span>
</div>

<table id="tbl">
<thead><tr>
<th onclick="st(0,'f')">Название <span class="ar"></span></th>
<th onclick="st(1,'f')">Размер <span class="ar"></span></th>
<th onclick="st(2,'n')">Дата <span class="ar"></span></th>
<th>Скачать</th>
</tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody>
</table>

<div class="tile-grid" id="tile-grid">
{chr(10).join(tiles)}
</div>

<p class="st">✕ — скрыть фильм и все одноимённые. Кликните на «Дата» для сортировки. Очистить скрытые: очистите localStorage.</p>
</div>
<script>
var sd={{i:-1,d:1}};
function st(c,t){{var tb=document.querySelector('#tbl tbody'),r=Array.from(tb.children),a=sd.i===c?sd.d*-1:1;
r.sort(function(x,y){{var va=x.children[c].getAttribute('data-s')||(t==='n'?x.getAttribute('data-date')||'0':x.children[c].textContent.trim()),vb=y.children[c].getAttribute('data-s')||(t==='n'?y.getAttribute('data-date')||'0':y.children[c].textContent.trim());if(t==='n'){{return a*(parseFloat(va)-parseFloat(vb))}}return a*va.localeCompare(vb)}});
r.forEach(function(r){{tb.appendChild(r)}});sd.i=c;sd.d=a;
document.querySelectorAll('th .ar').forEach(function(e){{e.textContent=''}});document.querySelectorAll('th')[c].querySelector('.ar').textContent=a>0?'▲':'▼'}}
function td(el){{var r=el.closest('td').querySelector('.dtc');if(!r)return;var on=r.style.display!=='none';r.style.display=on?'none':'';el.textContent=on?'+':'−'}}
function pt(el){{var u=el.getAttribute('data-yt');if(!u)return;window.open(u,'tr','width=960,height=540,menubar=no,toolbar=no,location=no')}}
function hm(el){{var t=el.closest('tr').getAttribute('data-title');if(!t)return;var h=JSON.parse(localStorage.getItem('ph')||'[]');if(h.indexOf(t)===-1)h.push(t);localStorage.setItem('ph',JSON.stringify(h));document.querySelectorAll('tr[data-title="'+t+'"]').forEach(function(r){{r.style.display='none'}});fh()}}
function htm(el){{var t=el.closest('.tile-card').getAttribute('data-title');if(!t)return;var h=JSON.parse(localStorage.getItem('ph')||'[]');if(h.indexOf(t)===-1)h.push(t);localStorage.setItem('ph',JSON.stringify(h));document.querySelectorAll('.tile-card[data-title="'+t+'"],tr[data-title="'+t+'"]').forEach(function(r){{r.style.display='none'}})}}
function fh(){{var h=JSON.parse(localStorage.getItem('ph')||'[]');h.forEach(function(t){{document.querySelectorAll('tr[data-title="'+t+'"]').forEach(function(r){{r.style.display='none'}})}})}}
function fht(){{var h=JSON.parse(localStorage.getItem('ph')||'[]');h.forEach(function(t){{document.querySelectorAll('.tile-card[data-title="'+t+'"]').forEach(function(r){{r.style.display='none'}})}})}}
var sx=/(?:\\bhorror\\b|\\b(?:sex|porn|xxx|erotic|adult|nsfw|onlyfans)\\b)/i;
(function(){{var trs=document.querySelectorAll('#tbl tbody tr');trs.forEach(function(r){{var g=r.getAttribute('data-genre')||'',t=r.getAttribute('data-title')||'';if(sx.test(g)||sx.test(t))r.style.display='none'}});fh();fht();
var isTile=localStorage.getItem('tv')==='tile';if(isTile){{document.body.classList.add('tile');document.getElementById('tvb').textContent='Вид: список'}}}})()
function tv(){{var b=document.body;b.classList.toggle('tile');var isTile=b.classList.contains('tile');localStorage.setItem('tv',isTile?'tile':'list');document.getElementById('tvb').textContent=isTile?'Вид: список':'Вид: плитка'}}
</script>
</body>
</html>'''
    return html


def main():
    refresh = '--refresh' in sys.argv

    if not refresh and os.path.exists(TORRENTS_CACHE):
        print("Загружаю кеш торрентов...")
        torrents = load_json(TORRENTS_CACHE)

    else:
        print("1. Загружаю Pirate Bay...")
        html = load_page(refresh=True)

        print("2. Парсю торренты...")
        fresh = parse_torrents(html)
        print(f"   Найдено: {len(fresh)} торрентов")

        cached = load_json(TORRENTS_CACHE) or []
        cache_by_url = {t['detail_url']: t for t in cached if t.get('detail_url')}
        fresh_by_url = {t['detail_url']: t for t in fresh if t.get('detail_url')}

        kept = []
        new_list = []
        for url, ft in fresh_by_url.items():
            if url in cache_by_url:
                old = cache_by_url[url]
                old['seeders'] = ft['seeders']
                old['leechers'] = ft['leechers']
                old['size'] = ft['size']
                old['uploaded'] = ft['uploaded']
                old['uploaded_ts'] = ft['uploaded_ts']
                kept.append(old)
            else:
                new_list.append(ft)

        removed_count = 0
        for url, ct in cache_by_url.items():
            if url not in fresh_by_url:
                imdb_id = ct.get('imdb_id')
                if imdb_id:
                    poster_path = f"{POSTERS_DIR}/{imdb_id}.jpg"
                    if os.path.exists(poster_path):
                        os.remove(poster_path)
                        print(f"   Удалён постер: {poster_path}")
                removed_count += 1

        missing = [t for t in kept if not t.get('imdb_id') or not t.get('imdb_rating')]

        if new_list:
            print(f"\n3. Новых фильмов: {len(new_list)}. Ищу IMDB ID...")
            search_imdb_ids(new_list)

        if missing:
            print(f"\n4. Дозаполняю {len(missing)} фильмов без IMDB...")
            search_imdb_ids(missing)

        needed_ids = set()
        for t in kept + new_list:
            if t.get('imdb_id'):
                needed_ids.add(t['imdb_id'])

        if needed_ids:
            print(f"\n5. Загружаю IMDB ratings для {len(needed_ids)} фильмов...")
            ratings = load_ratings(needed_ids, refresh)
            print(f"   Получено рейтингов: {sum(1 for k in needed_ids if k in ratings)}/{len(needed_ids)}")

            print(f"\n6. Загружаю IMDB basics (жанры) для {len(needed_ids)} фильмов...")
            basics = load_basics(needed_ids, refresh)
            print(f"   Получено жанров: {sum(1 for k in needed_ids if k in basics)}/{len(needed_ids)}")
        else:
            ratings = {}
            basics = {}

        if new_list:
            print(f"\n7. Обогащаю данные для {len(new_list)} новых фильмов...")
            enrich(new_list, ratings, basics)

        if missing:
            print(f"\n8. Дозаполняю данные для {len(missing)} фильмов...")
            enrich(missing, ratings, basics)

        torrents = kept + new_list
        torrents.sort(key=lambda t: t.get('uploaded_ts', 0) or 0, reverse=True)

        removed_msg = f", удалено: {removed_count}" if removed_count else ""
        print(f"   Осталось: {len(torrents)} (новых: {len(new_list)}{removed_msg})")

        save_json(TORRENTS_CACHE, torrents)

    print("\n9. Генерирую HTML...")
    output = generate_html(torrents)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"\n✅ Готово: {OUTPUT_FILE}")
    print(f"   Открой файл в браузере.")


if __name__ == '__main__':
    main()
