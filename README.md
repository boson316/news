# News Aggregator (Flask)

**Languages:** [English](README.md) · [中文](README.zh-TW.md)

A lightweight news aggregator built with Python, Flask, and SQLite. It pulls headlines from public international, US, tech, business, and Chinese RSS feeds. Run it locally or deploy to the cloud and open the URL in a browser—no need to keep `python app.py` running on your machine.

> For personal learning and research only. Not for commercial use.

---

## Option 1: Use it online (deploy to the cloud)

After deploying, you get a URL like `https://your-app.onrender.com`. Open it in any browser—no local terminal required.

### Recommended: Render (free tier)

1. **Push to GitHub**
   - Create a new repo (e.g. `news-aggregator`)
   - Upload the contents of this folder to the **repo root** (`app.py`, `requirements.txt`, `templates/`, `static/`, `render.yaml`, `runtime.txt`, `.gitignore`). Do **not** nest them inside an extra folder, or Render will not find `app.py`.

2. **Deploy on Render**
   - Go to [render.com](https://render.com) and sign in with GitHub
   - **New → Web Service** → select your repo
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
   - Click **Create Web Service** and wait for the build

   **Or** use the included Blueprint: **New → Blueprint** → connect the repo; `render.yaml` applies the settings automatically.

3. **Open your site**
   - Render gives you a URL, e.g. `https://news-aggregator-xxxx.onrender.com`
   - On first visit, click **Refresh News**, wait a few seconds, then return to the home page.

**Note:** On Render's free tier, the service sleeps after inactivity. The first request after sleep may take 30–60 seconds.

---

## Option 2: Run locally

### Requirements

- Python 3.10+
- pip

### Setup

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. The app binds to `0.0.0.0`, so you can also reach it from other devices on your LAN via `http://<your-ip>:5000`.

---

## Features

| Section | Description |
|---------|-------------|
| International | World / geopolitics (BBC, Reuters, …) |
| Tech | Technology headlines |
| Business | Markets and finance |
| Big Tech | NVIDIA, Google, Amazon, Microsoft, Meta |
| NVIDIA / Google / Microsoft | Company-specific keyword filters |
| Chinese | Traditional Chinese sources (BBC 中文, DW, LTN, …) |

**Filters:** time range (24h / week / month / quarter / half-year / all), source dropdown, keyword search, favorites.

---

## Customize RSS sources

Edit `RSS_SOURCES` in `app.py` to add or remove feeds. Current sources include BBC, Reuters, TechCrunch, TechNews, Liberty Times, ETtoday, UDN, BBC Chinese, and DW Chinese.

---

## Project layout

```
.
├── app.py              # Flask app + RSS fetcher
├── requirements.txt
├── runtime.txt         # Python version for Render
├── render.yaml         # Render Blueprint
├── templates/          # HTML pages
├── static/style.css
└── news.db             # SQLite (created at runtime; gitignored)
```
