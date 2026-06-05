# AGENTS.md — ThePiraBay

Проект: генератор HTML-страницы торрентов с Pirate Bay, обогащённой рейтингом IMDB и ссылками на YouTube трейлеры.

## Структура проекта

| Файл | Назначение |
|------|-----------|
| `generate_page.py` | Python-скрипт — скачивает Top 100 HD-Movies с Pirate Bay, обогащает IMDB рейтингом/жанрами/постером и YouTube трейлером, генерирует `torrents.html` |
| `piratebay-imdb-trailer.user.js` | Tampermonkey-юзерскрипт — добавляет IMDB рейтинг и YouTube трейлер прямо на страницу Pirate Bay |
| `requirements.txt` | Зависимости Python |
| `imdb_ratings_cache.json` | Кеш рейтингов (только нужные ID, ~50-200KB) |
| `imdb_basics_cache.json` | Кеш жанров (только нужные ID, ~50-200KB) |
| `imdb_search_cache.json` | Кеш поиска название→ID + постер + актёры (вечный) |
| `youtube_cache.json` | Кеш YouTube трейлеров (название→прямая ссылка, вечный) |
| `piratebay_page.html` | Кеш HTML-страницы Pirate Bay |
| `torrents_data.json` | Кеш обогащённых данных по торрентам (IMDB, постер, жанр, трейлер) |
| `torrents.html` | Сгенерированная HTML-страница |
| `server.py` | HTTP-сервер для просмотра страницы и обновления по кнопке 🔄 |
| `posters/` | Локально сохранённые постеры IMDB |

## Как запустить

```powershell
.venv\Scripts\Activate.ps1
python generate_page.py
# → создаёт torrents.html
```

## Через сервер (с кнопкой обновления)

```powershell
python server.py
# → http://localhost:8765
# Кнопка 🔄 на странице перезапускает генерацию
```

## Как это работает (без API-ключей)

1. **IMDB autocomplete API** (`v2.sg.media-imdb.com`) — поиск фильма по названию → IMDB ID (ttXXXXXXX)
2. **IMDB официальный датасет** (`datasets.imdbws.com/title.ratings.tsv.gz`, ~8MB) — ID → рейтинг + количество голосов
3. **YouTube search URL** — конструируется из названия фильма

## Язык

- Сообщения, коммиты, документация — только на русском.
- Код (переменные, функции, классы) — на английском.

## Поиск решений

- Все вопросы и проблемы сначала искать в интернете (websearch/webfetch).
- Не полагаться только на свои знания — использовать актуальные источники.
