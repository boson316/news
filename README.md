# News Aggregator (Flask)

**Languages:** [English](README.md) · [中文](README.zh-TW.md)

**Live (GitHub Pages, recommended):** https://boson316.github.io/news/
**Legacy (Render, has cold starts):** https://boson-news-app.onrender.com

A lightweight news aggregator built with Python, Flask, and SQLite. Pulls headlines from public RSS feeds (international, tech, business, Chinese). Default UI is **Traditional Chinese** with an English toggle. Run locally or deploy to Render.

> For personal learning and research only. Not for commercial use.

---

## GitHub Pages static version (recommended: free, no cold starts)

GitHub Actions fetches the RSS feeds every 15 minutes and deploys a static site to GitHub Pages, so the page loads instantly with no server to wake up.

| Item | Description |
|------|-------------|
| Fetch | `scripts/build_site.py`: fetch RSS → merge with live data → write `_site/` |
| Schedule | `.github/workflows/pages.yml`: every 15 min, on push to `main`, or manually |
| Frontend | `web/` (`index.html`, `favorites.html`, `app.js`, `style.css`); filtering runs in the browser |
| History | Keeps the last 180 days, up to 300 articles per source |
| Favorites | Stored in the browser's `localStorage` (per device) |

### First-time setup

1. Merge these files into `main`
2. Repo **Settings → Pages → Build and deployment → Source** → **GitHub Actions**
3. **Actions** → **Update news & deploy Pages** → **Run workflow**
4. Open https://boson316.github.io/news/ after about a minute

> GitHub schedules are often delayed a few minutes. If the repo has no activity for 60 days, GitHub pauses scheduled workflows; re-enable it on the Actions page.

### Local preview

```bash
pip install -r requirements.txt
python scripts/build_site.py
python -m http.server -d _site 8000
```

---

## Features

| Feature | Description |
|---------|-------------|
| Chinese default | Traditional Chinese UI; switch to English in the header |
| Auto-fetch | Fetches RSS on first visit when the database is empty |
| Background refresh | Refreshes every 30 minutes after startup if stale |
| Scheduled cron | cron-job.org every **10 minutes** → `/cron/refresh` |
| Filters | Section, source, keyword, time range |
| Favorites | Save articles to read later |

---

## Option 1: Use online (Render)

**GitHub:** https://github.com/boson316/news

### Deploy

1. Push this folder to the **repo root** (`app.py`, `requirements.txt`, `templates/`, `static/`, `render.yaml`, `runtime.txt`)
2. [Render](https://render.com) → **New → Web Service** → select repo
3. **Build:** `pip install -r requirements.txt`
4. **Start:** `gunicorn app:app --bind 0.0.0.0:$PORT`
5. Or use **Blueprint** with `render.yaml` (service name `boson-news-app`)

### Verify deployment

| URL | Expected |
|-----|----------|
| https://boson-news-app.onrender.com/ | Home page (Chinese by default) |
| https://boson-news-app.onrender.com/cron/refresh | `{"status":"started"}` |
| https://boson-news-app.onrender.com/health | `{"status":"ok","articles":...}` |

### cron-job.org (recommended)

On Render's free tier, the service sleeps after ~15 minutes of inactivity:

1. [cron-job.org](https://cron-job.org) → **Create cronjob**
2. **URL:** `https://boson-news-app.onrender.com/cron/refresh`
3. **Method:** GET
4. **Schedule:** every **10 minutes** (`*/10 * * * *`)
5. Check **Execution history** for `{"status":"started"}` or `{"status":"already_running"}`

> `/cron/refresh` responds immediately and fetches RSS in the background (avoids the 30s cron-job.org timeout).

---

## Option 2: Run locally

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`

---

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Home (auto-fetch if DB empty) |
| GET | `/refresh` | Manual sync refresh, then redirect home |
| GET | `/cron/refresh` | External scheduler; background refresh |
| GET | `/health` | Health check |
| GET | `/favorites` | Saved articles |
| POST | `/favorite` | Save an article |

---

## Sections

| Section | Description |
|---------|-------------|
| International | World / geopolitics (BBC, Reuters, …) |
| Tech | Technology headlines |
| Business | Markets and finance |
| Big Tech | NVIDIA, Google, Amazon, Microsoft, Meta |
| NVIDIA / Google / Microsoft | Company keyword filters |
| Chinese | Traditional Chinese sources |

---

## Project layout

```
.
├── app.py                 # Flask app, RSS fetcher, i18n
├── requirements.txt
├── runtime.txt            # Python 3.11.9 for Render
├── render.yaml            # Render Blueprint
├── templates/
│   ├── index.html
│   ├── favorites.html
│   └── refresh_done.html
├── static/style.css
└── news.db                # SQLite (runtime; gitignored)
```

---

## Customize RSS sources

Edit `RSS_SOURCES` in `app.py`. Current feeds include BBC, Reuters, TechCrunch, TechNews, Liberty Times, ETtoday, UDN, BBC Chinese, and DW Chinese.

---

## RSS sources

Sources live in `RSS_SOURCES` in `scripts/build_site.py` (`app.py` for the legacy Flask app). Before adding one, run **Actions → Check RSS feeds → Run workflow** (`scripts/check_feeds.py`) to confirm the URL works.

| Section | Sources |
|---------|---------|
| World | BBC World, BBC US & Canada, Reuters, AP News (Reuters/AP via Google News) |
| Business | Bloomberg, CNBC, MarketWatch, Liberty Times Business, ETtoday Finance, Economic Daily News, CNA Finance, Yahoo TW Finance |
| Tech | TechCrunch, Wired, MIT Technology Review, Hacker News, TechNews, TechOrange, iThome |
| Chinese | BBC Chinese, DW Chinese, Liberty Times World, PTS News, The Reporter, NYT Chinese, RFI Chinese |
