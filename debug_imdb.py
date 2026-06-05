import requests, json, re

h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 1. Autocomplete API
r = requests.get('https://v2.sg.media-imdb.com/suggestion/p/project%20hail%20mary.json', headers=h)
print('Autocomplete status:', r.status_code)
data = r.json()
if data.get('d'):
    for item in data['d']:
        print(f"  ID: {item.get('id')}, Title: {item.get('l')}, Year: {item.get('y')}")
else:
    print('  No results')

# 2. Title page
r2 = requests.get('https://www.imdb.com/title/tt12042730/', headers=h)
print(f'\nTitle page status: {r2.status_code}, length: {len(r2.text)}')

ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', r2.text, re.DOTALL)
if ld:
    try:
        d2 = json.loads(ld.group(1))
        ar = d2.get('aggregateRating', {})
        print(f"Rating: {ar.get('ratingValue')}, Votes: {ar.get('ratingCount')}")
    except Exception as e:
        print('JSON-LD error:', e)
        print('First 300 chars:', ld.group(1)[:300])
else:
    print('No JSON-LD')
    m = re.search(r'data-testid="hero-rating-bar__aggregate-rating__score"[^>]*>([\d.]+)', r2.text)
    print(f'Rating from HTML: {m.group(1) if m else "NOT FOUND"}')
    idx = r2.text.find('aggregateRating')
    if idx > 0:
        print(f'aggregateRating at {idx}: ...{r2.text[idx:idx+200]}...')
    else:
        idx = r2.text.find('ratingValue')
        print(f'ratingValue at {idx}: ...{r2.text[idx:idx+200] if idx>0 else "NOT FOUND"}...')
        if idx < 0:
            print('First 1000 chars of HTML:', r2.text[:1000])
