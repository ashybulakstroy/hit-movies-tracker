# hit-movies-tracker

Generates an HTML page of the Top 100 HD movies from Pirate Bay, enriched with IMDB ratings, genres, posters, and YouTube trailer links. No API keys required.

## Features

- Fetches the current Top 100 HD-Movies from Pirate Bay
- Looks up each movie on IMDB: rating, genre, poster, cast
- Searches YouTube for a trailer and links directly to the video
- Two view modes: **list** (table) and **tile** (cards)
- Toggle button: **"View: tiles/list"**
- Mobile preview button: **📱/🖥** — forces mobile styles on desktop
- Click-to-sort on all column headers: **Title**, **Size**, **Date**, **Rating** — synced across both views
- Semi-transparent ▶ play button over the poster for trailer preview
- Expandable details: poster, genre, rating, cast
- Auto-filters out horror and adult content
- ✕ to hide a movie and all its duplicates (no confirmation)
- Full caching — re-generation takes ~0.2 sec
- Incremental IMDB cache: only stores IDs seen in TPB (~50-200KB instead of 1GB)
- Sync: new movies are added, removed ones are cleaned up

## Setup

```powershell
git clone https://github.com/ваш-username/hit-movies-tracker.git
cd hit-movies-tracker
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Usage

**One-time generation:**

```powershell
python generate_page.py
# → creates torrents.html
```

**Refresh data from Pirate Bay:**

```powershell
python generate_page.py --refresh
# → fetches fresh listing, adds new movies, removes missing ones
# → updates IMDB/poster/genre/trailer only for new entries
```

**Via HTTP server (with 🔄 refresh button on the page):**

```powershell
python server.py
# → http://localhost:8765
```

## How it works

### No API keys needed

1. **Pirate Bay** — parses the HTML of `/top/207`
2. **IMDB ID** — via autocomplete API `v2.sg.media-imdb.com` (search by title)
3. **Rating & genre** — from official IMDB datasets (`title.ratings.tsv.gz`, `title.basics.tsv.gz`, ~8MB)
4. **Poster** — downloaded from IMDB and stored locally in `posters/`
5. **Trailer** — searched via YouTube, linked directly

### Caches

| File | Purpose |
|------|---------|
| `imdb_ratings_cache.json` | IMDB ratings (only needed IDs, ~50-200KB) |
| `imdb_basics_cache.json` | IMDB genres (only needed IDs, ~50-200KB) |
| `imdb_search_cache.json` | Search results title→ID + poster + cast |
| `youtube_cache.json` | YouTube trailer links |
| `piratebay_page.html` | Snapshot of the Pirate Bay page |
| `torrents_data.json` | All enriched torrent data |
| `posters/` | Locally cached posters |

On re-run without `--refresh`, all data is served from cache — generation takes seconds.

## Project structure

```
hit-movies-tracker/
├── generate_page.py              # Main generation script
├── server.py                     # HTTP server with 🔄 refresh button
├── torrents.html                 # Generated page (gitignored)
├── requirements.txt              # Dependencies
├── posters/                      # Posters (gitignored)
├── *cache.json                   # Cache files (gitignored)
├── README.md                     # Documentation (Russian)
├── README-en.md                  # Documentation (English)
└── piratebay-imdb-trailer.user.js  # Tampermonkey userscript
```

## Tech stack

- Python 3.10+
- requests, BeautifulSoup4
- No API keys
- Vanilla JS on the generated page

## Language

- Code (variables, functions, comments) — English
- UI text on the generated page — English
- This README — English
