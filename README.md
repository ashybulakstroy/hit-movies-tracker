# hit-movies-tracker

Генератор HTML-страницы топ-100 HD-фильмов с Pirate Bay, обогащённой рейтингом IMDB, жанрами, постерами и ссылками на YouTube-трейлеры.

## Возможности

- Скачивает актуальный список топ-100 HD-Movies с Pirate Bay
- Находит каждый фильм в IMDB: рейтинг, жанр, постер, актёров
- Ищет трейлер на YouTube и даёт прямую ссылку на видео
- Генерирует красивую HTML-страницу с сортировкой по дате
- На постере — полупрозрачная кнопка ▶ для просмотра трейлера
- Раскрывающиеся детали: постер, жанр, рейтинг, актёры
- Фильтр: автоматически скрывает ужасы и секс-контент
- Кнопка ✕ для скрытия фильма и всех одноимённых
- Кеширование всех данных — повторная генерация за 0.2 сек
- Синхронизация: новые фильмы добавляются, удалённые — убираются

## Установка

```powershell
git clone https://github.com/ваш-username/hit-movies-tracker.git
cd hit-movies-tracker
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Использование

**Однократная генерация:**

```powershell
python generate_page.py
# → создаёт torrents.html
```

**Обновление данных с Pirate Bay:**

```powershell
python generate_page.py --refresh
# → скачивает свежий список, добавляет новые, удаляет пропавшие
# → обновляет IMDB/постер/жанр/трейлер только для новых фильмов
```

**Через HTTP-сервер (с кнопкой 🔄 на странице):**

```powershell
python server.py
# → http://localhost:8765
```

## Как это работает

### Без API-ключей

1. **Pirate Bay** — парсится HTML страницы `/top/207`
2. **IMDB ID** — через autocomplete API `v2.sg.media-imdb.com` (поиск по названию)
3. **Рейтинг и жанр** — из официальных датасетов IMDB (`title.ratings.tsv.gz`, `title.basics.tsv.gz`, ~8MB)
4. **Постер** — скачивается с IMDB и сохраняется локально в `posters/`
5. **Трейлер** — поиск через YouTube, ссылка на прямое видео

### Кеши

| Файл | Назначение |
|------|-----------|
| `imdb_ratings_cache.json` | Рейтинги IMDB (из датасета, ~8MB) |
| `imdb_basics_cache.json` | Жанры IMDB (из датасета, ~8MB) |
| `imdb_search_cache.json` | Результаты поиска название→ID + постер + актёры |
| `youtube_cache.json` | Ссылки на YouTube-трейлеры |
| `piratebay_page.html` | Слепок страницы Pirate Bay |
| `torrents_data.json` | Все обогащённые данные по торрентам |
| `posters/` | Локальные копии постеров |

При повторном запуске без `--refresh` данные берутся из кеша — генерация занимает доли секунды.

## Структура проекта

```
hit-movies-tracker/
├── generate_page.py          # Основной скрипт генерации
├── server.py                 # HTTP-сервер с кнопкой обновления
├── torrents.html             # Сгенерированная страница (в gitignore)
├── requirements.txt          # Зависимости
├── posters/                  # Постеры (в gitignore)
├── *cache.json               # Файлы кеша (в gitignore)
└── piratebay-imdb-trailer.user.js  # Tampermonkey-скрипт
```

## Стек

- Python 3.10+
- requests, BeautifulSoup4
- Никаких API-ключей
- vanilla JS на сгенерированной странице

## Язык

- Документация, README — русский
- Код (переменные, функции, комментарии) — английский
