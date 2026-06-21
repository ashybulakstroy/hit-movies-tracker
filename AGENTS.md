# AGENTS.md — ThePiraBay

Проект: генератор HTML-страницы торрентов с Pirate Bay / TPB Party, обогащённой рейтингом IMDB и ссылками на YouTube трейлеры.

## Структура проекта

| Файл | Назначение |
|------|-----------|
| `generate_page.py` | Python-скрипт — скачивает Top 100 HD-Movies с выбранного источника, обогащает IMDB рейтингом/жанрами/постером и YouTube трейлером, генерирует `torrents.html` |
| `piratebay-imdb-trailer.user.js` | Tampermonkey-юзерскрипт — добавляет IMDB рейтинг и YouTube трейлер прямо на страницу Pirate Bay |
| `requirements.txt` | Зависимости Python |
| `data/imdb_ratings_cache.json` | Кеш рейтингов (только нужные ID, ~50-200KB) |
| `data/imdb_basics_cache.json` | Кеш жанров (только нужные ID, ~50-200KB) |
| `data/imdb_search_cache.json` | Кеш поиска название→ID + постер + актёры (вечный) |
| `data/youtube_cache.json` | Кеш YouTube трейлеров (название→прямая ссылка, вечный) |
| `data/piratebay_page.html` | Кеш HTML-страницы Pirate Bay (источник `piratebay`) |
| `data/torrents_data.json` | Кеш обогащённых данных по торрентам (источник `piratebay`) |
| `data/tpbparty_page.html` | Кеш HTML-страницы TPB Party (источник `tpbparty`) |
| `data/torrents_data_tpbparty.json` | Кеш обогащённых данных по торрентам (источник `tpbparty`) |
| `torrents.html` | Сгенерированная HTML-страница |
| `server.py` | HTTP-сервер для просмотра страницы и обновления по кнопке 🔄 |
| `data/posters/` | Локально сохранённые постеры IMDB |

## Источники

В проекте два источника, переключаются кнопками вверху страницы:

| Ключ (`--source`) | Название | URL | Парсер |
|-------------------|----------|-----|--------|
| `piratebay` | Pirate Bay | `https://1.piratebays.to/top/207` | `parse_piratebay()` |
| `tpbparty` | TPB Party | `https://tpb.party/top/207` | `parse_tpbparty()` |

Каждый источник имеет свои кеш-файлы (page + torrents_data).

## Уникализация

После парсинга применяется `deduplicate()` — удаление дубликатов по `movie_title + movie_year`. Первый фильм в списке — главный, остальные дубли исключаются.

## Запуск

```powershell
.venv\Scripts\Activate.ps1
python generate_page.py --source piratebay   # Pirate Bay
python generate_page.py --source tpbparty     # TPB Party
# → создаёт torrents.html
```

## Через сервер (с кнопкой обновления + переключением источника)

```powershell
python server.py
# → http://localhost:8765?source=piratebay
# Кнопки Pirate Bay / TPB Party вверху страницы
# Кнопка 🔄 перезапускает генерацию для текущего источника
```

Порт сервера задаётся через переменную окружения `SERVER_PORT`:

```powershell
$env:SERVER_PORT = "8877"
python server.py
```

## Как это работает (без API-ключей)

1. **IMDB autocomplete API** (`v2.sg.media-imdb.com`) — поиск фильма по названию → IMDB ID (ttXXXXXXX)
2. **IMDB официальный датасет** (`datasets.imdbws.com/title.ratings.tsv.gz`, ~8MB) — ID → рейтинг + количество голосов
3. **YouTube search URL** — конструируется из названия фильма

IMDB `ratings` и `basics` скачиваются только если локальный кеш в `data/` не содержит нужные ID. Если удалённый dataset не содержит нужный ID, он сохраняется в кеше как отсутствующий, чтобы не скачивать dataset повторно ради того же ID. При сетевой ошибке используется имеющийся локальный кеш.

## Язык

- Сообщения, коммиты, документация — только на русском.
- Код (переменные, функции, классы) — на английском.

## Поиск решений

- Все вопросы и проблемы сначала искать в интернете (websearch/webfetch).
- Не полагаться только на свои знания — использовать актуальные источники.

## Глобальная инструкция: сначала проверь — потом докладывай

Перед тем как сказать пользователю «всё готово»:

1. **Запусти код** — убедись что нет ошибок выполнения.
2. **Проверь синтаксис** — `python -m py_compile generate_page.py` (или `python -m compileall .`)
3. **Проверь поведение** — что результат соответствует задаче (например, открыть HTML, проверить кнопки, переключить источник).
4. **Проверь регрессию** — если менял одно, не сломалось ли другое (например, при переключении источника старые данные сохранились).
5. **Только после этого** — сообщи пользователю, что сделано и что работает.
6. **Не говори «всё готово»**, пока сам не убедился.
