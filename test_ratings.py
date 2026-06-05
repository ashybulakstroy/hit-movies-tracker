import gzip
import json
import os
import time
import io
import requests

RATINGS_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
CACHE_FILE = "imdb_ratings_cache.json"
CACHE_TTL = 86400


def download_ratings():
    print("Скачиваю IMDB ratings dataset...")
    r = requests.get(RATINGS_URL, stream=True, timeout=60)
    r.raise_for_status()
    
    buf = io.BytesIO(r.content)
    ratings = {}
    with gzip.GzipFile(fileobj=buf, mode='rb') as gz:
        with io.TextIOWrapper(gz, encoding='utf-8') as f:
            f.readline()  # header
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    ratings[parts[0]] = {'rating': parts[1], 'votes': parts[2]}
    return ratings


def get_ratings():
    if os.path.exists(CACHE_FILE):
        mtime = os.path.getmtime(CACHE_FILE)
        if time.time() - mtime < CACHE_TTL:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    ratings = download_ratings()
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(ratings, f)
    return ratings


def search_imdb(title):
    first_char = title[0].lower()
    url = f"https://v2.sg.media-imdb.com/suggestion/{first_char}/{title}.json"
    r = requests.get(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }, timeout=8)
    data = r.json()
    for item in data.get('d', []):
        if item.get('id', '').startswith('tt'):
            return item['id']
    return None


def main():
    ratings = get_ratings()
    print(f"Всего записей: {len(ratings)}")

    imdb_id = search_imdb("Project Hail Mary")
    print(f"Project Hail Mary -> ID: {imdb_id}")
    if imdb_id and imdb_id in ratings:
        print(f"  Rating: {ratings[imdb_id]['rating']} ({ratings[imdb_id]['votes']} votes)")
    else:
        print("  Not found in dataset")


if __name__ == '__main__':
    main()
