# hit-movies-tracker

Generates an HTML page of the Top 100 HD movies from Pirate Bay, enriched with IMDB ratings, genres, posters, and YouTube trailer links. No API keys required.

## Features

- Fetches the current Top 100 HD-Movies from Pirate Bay
- Looks up each movie on IMDB: rating, genre, poster, cast
- Searches YouTube for a trailer and links directly to the video
- Two view modes: **list** (table) and **tile** (cards)
- Mobile preview button: **📱/🖥** — forces mobile styles on desktop
- Click-to-sort on all column headers: **Title**, **Size**, **Date**, **Rating** — synced across both views
- Genre filter — dynamic `<select>` dropdown, built from visible movies only
- Auto-filters out horror and adult content
- ✕ to hide a movie and all its duplicates (no confirmation)
- Semi-transparent ▶ play button over poster for trailer
- Expandable details: poster, genre, rating, cast
- Full caching — re-generation takes ~0.2 sec
- Incremental IMDB cache: only stores IDs seen in TPB (~50-200KB instead of 1GB)
- TPB page hash: skips refresh when movie list hasn't changed
- Sync: new movies are added, removed ones are cleaned up along with their posters

## Setup

```powershell
git clone https://github.com/your-username/hit-movies-tracker.git
cd hit-movies-tracker
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Usage

**One-time generation (from cache):**

```powershell
python generate_page.py
```

**Refresh from Pirate Bay (with cache):**

```powershell
python generate_page.py --refresh
# → fetches fresh listing
# → if movies are the same — uses cache without re-generation
# → otherwise adds new movies, removes missing ones, enriches with IMDB
```

**Full re-generation without cache:**

```powershell
python generate_page.py --refresh --nocache
# → forces full update even if movie list hasn't changed
```

**Via HTTP server (with 🔄 refresh button on page):**

```powershell
python server.py
# → http://localhost:8765
```

**Quick launch:**

```powershell
refresh.bat
# → runs generate_page.py --refresh and opens torrents.html
```

## How it works

### No API keys needed

1. **Pirate Bay** — parses HTML of `/top/207`
2. **IMDB ID** — via autocomplete API `v2.sg.media-imdb.com` (prefers results with poster)
3. **Rating & genre** — from official IMDB datasets (`title.ratings.tsv.gz`, `title.basics.tsv.gz`, ~8MB)
4. **Poster** — downloaded from IMDB, stored locally in `posters/`
5. **Trailer** — searched via YouTube, linked directly

### `--refresh` optimization

On `--refresh`, the script computes a SHA256 hash of the movie table from the TPB page. If the hash matches the stored one (`piratebay_hash.txt`), all processing (IMDB datasets, search, enrichment) is skipped and cached data is used. Force full refresh with `--nocache`.

### Caches

| File | Purpose |
|------|---------|
| `imdb_ratings_cache.json` | IMDB ratings (only needed IDs, ~50-200KB) |
| `imdb_basics_cache.json` | IMDB genres (only needed IDs, ~50-200KB) |
| `imdb_search_cache.json` | Search results title→ID + poster + cast |
| `youtube_cache.json` | YouTube trailer links |
| `piratebay_page.html` | Snapshot of the Pirate Bay page |
| `piratebay_hash.txt` | SHA256 hash of movie table for `--refresh` optimization |
| `torrents_data.json` | All enriched torrent data |
| `posters/` | Locally cached posters |

## Project structure

```
hit-movies-tracker/
├── generate_page.py              # Main generation script
├── server.py                     # HTTP server with 🔄 button
├── refresh.bat                   # Quick --refresh + open browser
├── piratebay-imdb-trailer.user.js # Tampermonkey userscript
├── requirements.txt              # Dependencies
├── AGENTS.md                     # AI assistant instructions
├── README.md                     # Documentation (Russian)
├── README-en.md                  # Documentation (English)
├── torrents.html                 # Generated page (gitignored)
├── posters/                      # Posters (gitignored)
├── *cache.json                   # Cache files (gitignored)
└── *cache.txt                    # Hashes, other cache (gitignored)
```

## Tech stack

- Python 3.10+
- requests, BeautifulSoup4
- No API keys
- Vanilla JS on the generated page

## Language

- UI on generated page — Russian
- Code (variables, functions, comments) — English
- EN documentation — this file
