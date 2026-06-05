import requests, json

# Check IMDB autocomplete for rating data
r = requests.get(
    'https://v2.sg.media-imdb.com/suggestion/p/project%20hail%20mary.json',
    headers={'User-Agent': 'Mozilla/5.0'}
)
data = r.json()
for item in data.get('d', []):
    print(json.dumps(item, indent=2, ensure_ascii=False)[:300])
    print('---')

# Also check the 'tt' daily download dataset - direct URL
r2 = requests.head('https://datasets.imdbws.com/title.ratings.tsv.gz')
print(f'\nRatings dataset: status={r2.status_code}, size={r2.headers.get("Content-Length", "?")}')
