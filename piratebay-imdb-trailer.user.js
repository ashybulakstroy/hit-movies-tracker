// ==UserScript==
// @name         TPB IMDB Rating & YouTube Trailer
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Добавляет рейтинг IMDB и ссылку на YouTube трейлер к каждому торренту на Pirate Bay
// @author       You
// @match        *://*.piratebays.to/*
// @match        *://*.thepiratebay.org/*
// @match        *://*.piratebay.org/*
// @match        *://*.tpb.party/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=thepiratebay.org
// @grant        GM_xmlhttpRequest
// @grant        GM_addStyle
// @connect      v2.sg.media-imdb.com
// @connect      www.imdb.com
// ==/UserScript==

(function () {
    'use strict';

    const CACHE_KEY = 'tpb_imdb_cache';
    let ratingCache = {};

    try {
        const stored = localStorage.getItem(CACHE_KEY);
        if (stored) ratingCache = JSON.parse(stored);
    } catch (e) {}

    function saveCache() {
        try { localStorage.setItem(CACHE_KEY, JSON.stringify(ratingCache)); } catch (e) {}
    }

    function extractMovieName(raw) {
        let title = raw.trim();
        title = title.replace(/^tt\d+\s*/, '');
        title = title.replace(/\s*\[.*?\]/g, '');
        const yearMatch = title.match(/\((\d{4})\)/);
        const year = yearMatch ? yearMatch[1] : '';
        title = title.replace(/\s*\(\d{4}\)\s*/g, ' ');
        title = title.replace(/\(.*?\)/g, '');
        title = title.replace(/\s+(REPACK|PROPER|READNFO|iNTERNAL|EXTENDED|UNRATED|DC|FINAL|COMPLETE)\s*/gi, ' ');
        title = title.replace(/\s+/g, ' ').trim();
        title = title.replace(/\./g, ' ');
        title = title.replace(/\s+/g, ' ').trim();
        title = title.replace(/\.(mp4|avi|mkv|webm|WEBRip|x264|x265|BluRay|WEB-DL|HDTV|DVDRip).*/i, '');
        title = title.replace(/\s+/g, ' ').trim();
        return { title, year };
    }

    function searchIMDB(title, year) {
        return new Promise((resolve) => {
            const firstChar = title.charAt(0).toLowerCase();
            const query = encodeURIComponent(title);
            const url = `https://v2.sg.media-imdb.com/suggestion/${firstChar}/${query}.json`;

            GM_xmlhttpRequest({
                method: 'GET',
                url: url,
                onload: function (res) {
                    try {
                        const data = JSON.parse(res.responseText);
                        if (data.d && data.d.length) {
                            const results = data.d.filter(item => item.id && item.id.startsWith('tt'));
                            if (results.length) {
                                if (year) {
                                    const exact = results.find(r => String(r.y) === String(year));
                                    if (exact) {
                                        resolve({ id: exact.id, title: exact.l, year: exact.y });
                                        return;
                                    }
                                }
                                resolve({ id: results[0].id, title: results[0].l, year: results[0].y });
                                return;
                            }
                        }
                        resolve(null);
                    } catch (e) { resolve(null); }
                },
                onerror: () => resolve(null),
                timeout: 8000,
            });
        });
    }

    function fetchIMDBRating(imdbId) {
        return new Promise((resolve) => {
            const url = `https://www.imdb.com/title/${imdbId}/`;
            GM_xmlhttpRequest({
                method: 'GET',
                url: url,
                headers: {
                    'Accept': 'text/html,application/xhtml+xml',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                },
                onload: function (res) {
                    try {
                        const html = res.responseText;

                        // Пробуем JSON-LD
                        const ldMatch = html.match(/<script type="application\/ld\+json">(.*?)<\/script>/s);
                        if (ldMatch) {
                            const ld = JSON.parse(ldMatch[1]);
                            if (ld.aggregateRating && ld.aggregateRating.ratingValue) {
                                resolve({
                                    rating: String(ld.aggregateRating.ratingValue),
                                    votes: ld.aggregateRating.ratingCount
                                        ? Number(ld.aggregateRating.ratingCount).toLocaleString()
                                        : '',
                                });
                                return;
                            }
                        }

                        // Парсим из HTML как запасной вариант
                        const ratingMatch = html.match(/"ratingValue":\s*"*([\d.]+)"*/);
                        if (ratingMatch) {
                            resolve({ rating: ratingMatch[1], votes: '' });
                            return;
                        }
                        const starMatch = html.match(/data-testid="hero-rating-bar__aggregate-rating__score"\s*>\s*([\d.]+)/);
                        if (starMatch) {
                            resolve({ rating: starMatch[1], votes: '' });
                            return;
                        }

                        resolve(null);
                    } catch (e) { resolve(null); }
                },
                onerror: () => resolve(null),
                timeout: 10000,
            });
        });
    }

    function getMovieData(title, year) {
        return new Promise((resolve) => {
            const cacheKey = (title + '|' + year).toLowerCase();
            if (ratingCache[cacheKey]) {
                resolve(ratingCache[cacheKey]);
                return;
            }

            searchIMDB(title, year).then((searchResult) => {
                if (!searchResult || !searchResult.id) {
                    ratingCache[cacheKey] = null;
                    saveCache();
                    resolve(null);
                    return;
                }

                const result = { imdbID: searchResult.id };
                ratingCache[cacheKey] = result;
                saveCache();

                // Показываем хотя бы ссылку на IMDB сразу
                resolve(result);

                // Асинхронно подгружаем рейтинг
                fetchIMDBRating(searchResult.id).then((ratingData) => {
                    if (ratingData) {
                        result.rating = ratingData.rating;
                        result.votes = ratingData.votes;
                        saveCache();
                        updateBadges();
                    }
                });
            });
        });
    }

    // Храним активные баджи для обновления
    let activeBadges = [];

    function addIMDBBadge(cell, imdbID, title, year) {
        const badge = document.createElement('span');
        badge.className = 'tpb-imdb-badge';
        badge.style.cssText = `
            display: inline-block; margin-left: 8px; padding: 1px 6px;
            font-size: 11px; font-weight: bold; border-radius: 3px;
            white-space: nowrap; vertical-align: middle;
        `;

        const url = imdbID ? `https://www.imdb.com/title/${imdbID}/` : `https://www.imdb.com/find/?q=${encodeURIComponent(title + ' ' + year)}&s=tt`;
        badge.innerHTML = `<a href="${url}" target="_blank" style="color:#fff;text-decoration:none;" title="Открыть на IMDB">IMDB ⏳</a>`;
        badge.style.background = '#888';
        cell.appendChild(badge);

        activeBadges.push({ badge, imdbID, title, year });
    }

    function updateBadges() {
        activeBadges.forEach(({ badge, imdbID, title, year }) => {
            const cacheKey = (title + '|' + year).toLowerCase();
            const data = ratingCache[cacheKey];
            const url = imdbID ? `https://www.imdb.com/title/${imdbID}/` : `https://www.imdb.com/find/?q=${encodeURIComponent(title + ' ' + year)}&s=tt`;

            if (data && data.rating) {
                badge.style.background = '#f5c518';
                badge.innerHTML = `<a href="${url}" target="_blank" style="color:#000;text-decoration:none;" title="${data.votes ? data.votes + ' голосов' : ''}">IMDB ${data.rating}</a>`;
            } else if (data && data !== true) {
                badge.style.background = '#666';
                badge.innerHTML = `<a href="${url}" target="_blank" style="color:#fff;text-decoration:none;">IMDB</a>`;
            }
        });
    }

    function addTrailerLink(cell, movieTitle, year) {
        const query = encodeURIComponent(movieTitle + ' ' + year + ' official trailer');
        const link = document.createElement('a');
        link.href = `https://www.youtube.com/results?search_query=${query}`;
        link.target = '_blank';
        link.className = 'tpb-trailer-link';
        link.textContent = '▶ Трейлер';
        cell.appendChild(link);
    }

    function processListingPage() {
        const rows = document.querySelectorAll('#searchResult tbody tr');
        if (!rows.length) return;

        rows.forEach((row) => {
            const nameCell = row.querySelector('td a.detLink');
            if (!nameCell) return;

            const rawName = nameCell.textContent.trim();
            const { title, year } = extractMovieName(rawName);
            if (!title) return;

            const cell = nameCell.parentElement;
            addTrailerLink(cell, title, year);

            getMovieData(title, year).then((data) => {
                if (data && data.imdbID) {
                    addIMDBBadge(cell, data.imdbID, title, year);
                }
            });
        });
    }

    function processDetailPage() {
        const titleEl = document.getElementById('title');
        if (!titleEl) return;

        const rawName = titleEl.textContent.trim();
        const { title, year } = extractMovieName(rawName);
        if (!title) return;

        const infoDiv = document.createElement('div');
        infoDiv.style.cssText = 'margin: 8px 0; display: flex; gap: 10px; align-items: center;';

        const query = encodeURIComponent(title + ' ' + year + ' official trailer');
        const ytLink = document.createElement('a');
        ytLink.href = `https://www.youtube.com/results?search_query=${query}`;
        ytLink.target = '_blank';
        ytLink.textContent = '▶ Смотреть трейлер на YouTube';
        ytLink.style.cssText = `
            display: inline-block; padding: 6px 12px; font-size: 13px;
            font-weight: bold; color: #fff; background: #ff0000;
            border-radius: 4px; text-decoration: none;
        `;
        infoDiv.appendChild(ytLink);

        const ratingSpan = document.createElement('span');
        ratingSpan.id = 'tpb-imdb-rating';
        ratingSpan.style.cssText = `
            display: inline-block; padding: 6px 12px; font-size: 13px;
            font-weight: bold; border-radius: 4px;
            background: #888; color: #fff;
        `;
        ratingSpan.textContent = 'IMDB: загрузка...';
        infoDiv.appendChild(ratingSpan);

        titleEl.parentElement.insertBefore(infoDiv, titleEl.nextSibling);

        getMovieData(title, year).then((data) => {
            if (data && data.imdbID) {
                const url = `https://www.imdb.com/title/${data.imdbID}/`;
                const cacheKey = (title + '|' + year).toLowerCase();
                const cached = ratingCache[cacheKey];

                if (cached && cached.rating) {
                    ratingSpan.style.background = '#f5c518';
                    ratingSpan.innerHTML = `<a href="${url}" target="_blank" style="color:#000;text-decoration:none;">IMDB ${cached.rating}</a>`;
                } else {
                    ratingSpan.style.background = '#666';
                    ratingSpan.innerHTML = `<a href="${url}" target="_blank" style="color:#fff;text-decoration:none;">Открыть на IMDB</a>`;
                }
            } else {
                ratingSpan.textContent = 'IMDB: N/A';
            }
        });
    }

    GM_addStyle(`
        .tpb-trailer-link {
            display: inline-block; margin-left: 6px; padding: 1px 6px;
            font-size: 11px; font-weight: bold; color: #fff !important;
            background: #ff0000; border-radius: 3px;
            text-decoration: none !important; white-space: nowrap;
            vertical-align: middle;
        }
        .tpb-trailer-link:hover { background: #cc0000; }
    `);

    if (document.querySelector('#searchResult tbody')) {
        processListingPage();
    }
    if (document.getElementById('detailsframe')) {
        processDetailPage();
    }

})();
