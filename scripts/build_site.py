"""抓取 RSS 並產生 GitHub Pages 靜態網站。

由 GitHub Actions 定時執行：
1. 下載目前線上的 data/articles.json（保留歷史文章，才能篩選「過去一週／一個月…」）
2. 抓取所有 RSS 來源，合併並去除重複
3. 把 web/ 的靜態檔案與新的 articles.json 輸出到 _site/

本機測試：
    pip install -r requirements.txt
    python scripts/build_site.py
    python -m http.server -d _site 8000
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
OUT_DIR = ROOT / "_site"
OUT_DATA = OUT_DIR / "data" / "articles.json"

# 線上既有資料（由 workflow 傳入，例如 https://boson316.github.io/news/data/articles.json）
EXISTING_DATA_URL = os.environ.get("EXISTING_DATA_URL", "")
# 本機可直接指定舊檔路徑
EXISTING_DATA_FILE = os.environ.get("EXISTING_DATA_FILE", "")

KEEP_DAYS = 180  # 保留半年，對應「過去半年」篩選
MAX_PER_SOURCE = 300  # 每個來源最多保留幾篇，控制 JSON 大小
SUMMARY_MAX_CHARS = 220
REQUEST_TIMEOUT = 20
USER_AGENT = "Mozilla/5.0 (compatible; boson-news/1.0; +https://github.com/boson316/news)"

RSS_SOURCES = [
    # 英文國際新聞
    {"name": "BBC World", "category": "international", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "BBC US & Canada", "category": "us", "url": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"},
    {"name": "Reuters World News", "category": "international", "url": "http://feeds.reuters.com/Reuters/worldNews"},
    # 英文財經／科技
    {"name": "Reuters Business News", "category": "business", "url": "http://feeds.reuters.com/reuters/businessNews"},
    {"name": "Reuters Technology News", "category": "tech", "url": "http://feeds.reuters.com/reuters/technologyNews"},
    {"name": "TechCrunch", "category": "tech", "url": "https://techcrunch.com/feed/"},
    {"name": "USA TODAY Tech", "category": "tech", "url": "http://rssfeeds.usatoday.com/tech/"},
    # 中文科技／財經
    {"name": "TechNews 科技新報", "category": "tech", "url": "https://technews.tw/tn-rss/"},
    {"name": "TechOrange 科技報橘", "category": "tech", "url": "https://buzzorange.com/techorange/feed/"},
    {"name": "自由時報 財經", "category": "business", "url": "https://news.ltn.com.tw/rss/business.xml"},
    {"name": "ETtoday 財經", "category": "business", "url": "http://feeds.feedburner.com/ettoday/finance"},
    {"name": "聯合新聞網 產經", "category": "business", "url": "https://fund.udn.com/rss/lists/1002"},
    # 中文一般新聞
    {"name": "BBC 中文網", "category": "zh", "url": "https://www.bbc.co.uk/zhongwen/trad/index.xml"},
    {"name": "DW 德國之聲 中文", "category": "zh", "url": "https://rss.dw.com/rdf/rss-chi"},
    {"name": "自由時報 國際", "category": "zh", "url": "https://news.ltn.com.tw/rss/world.xml"},
]

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean_text(raw: str, max_chars: int | None = None) -> str:
    text = raw or ""
    # 跑兩次：有些來源的摘要是「跳脫過兩次」的 HTML（&lt;p&gt;…）
    for _ in range(2):
        text = html.unescape(TAG_RE.sub(" ", text))
    text = SPACE_RE.sub(" ", text).strip()
    if max_chars and len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


def entry_time(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            try:
                return datetime(*st[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass
    return None


def fetch_source(source: dict) -> tuple[dict, list[dict], str | None]:
    """回傳 (來源, 文章清單, 錯誤訊息)。"""
    try:
        resp = requests.get(
            source["url"], timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}
        )
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as e:  # noqa: BLE001 — 單一來源失敗不影響其他來源
        return source, [], str(e)

    seen_at = iso(now_utc())
    items: list[dict] = []
    for entry in feed.entries:
        title = clean_text(entry.get("title", ""))
        link = (entry.get("link") or "").strip()
        if not title or not link.startswith(("http://", "https://")):
            continue
        published = entry_time(entry)
        items.append(
            {
                "title": title,
                "url": link,
                "source": source["name"],
                "category": source["category"],
                "summary": clean_text(entry.get("summary", ""), SUMMARY_MAX_CHARS),
                # 沒有發布時間就用第一次抓到的時間，避免被時間篩選排除
                "published_at": iso(published) if published else seen_at,
            }
        )
    if not items and getattr(feed, "bozo", False):
        return source, [], f"parse error: {feed.get('bozo_exception')}"
    return source, items, None


def load_existing() -> list[dict]:
    try:
        if EXISTING_DATA_FILE:
            data = json.loads(Path(EXISTING_DATA_FILE).read_text(encoding="utf-8"))
        elif EXISTING_DATA_URL:
            resp = requests.get(EXISTING_DATA_URL, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                print(f"[existing] {EXISTING_DATA_URL} -> HTTP {resp.status_code}，從空資料開始")
                return []
            data = resp.json()
        else:
            return []
    except Exception as e:  # noqa: BLE001
        print(f"[existing] 讀取失敗，從空資料開始：{e}")
        return []
    articles = data.get("articles", []) if isinstance(data, dict) else []
    print(f"[existing] 載入 {len(articles)} 篇舊文章")
    return articles


def merge(existing: list[dict], fresh: list[dict]) -> list[dict]:
    by_url: dict[str, dict] = {a["url"]: a for a in existing if a.get("url")}
    for a in fresh:
        old = by_url.get(a["url"])
        # 保留第一次抓到的發布時間，其餘欄位用最新資料
        if old:
            a = {**a, "published_at": old.get("published_at") or a["published_at"]}
        by_url[a["url"]] = a

    cutoff = iso(now_utc() - timedelta(days=KEEP_DAYS))
    kept = [a for a in by_url.values() if (a.get("published_at") or "") >= cutoff]
    kept.sort(key=lambda a: a.get("published_at") or "", reverse=True)

    per_source: dict[str, int] = {}
    result: list[dict] = []
    for a in kept:
        n = per_source.get(a["source"], 0)
        if n >= MAX_PER_SOURCE:
            continue
        per_source[a["source"]] = n + 1
        result.append(a)
    return result


def main() -> int:
    existing = load_existing()

    fresh: list[dict] = []
    status: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for source, items, err in pool.map(fetch_source, RSS_SOURCES):
            if err:
                print(f"[RSS] ✗ {source['name']}: {err}")
            else:
                print(f"[RSS] ✓ {source['name']}: {len(items)} 篇")
            fresh.extend(items)
            status.append({"name": source["name"], "ok": err is None, "count": len(items)})

    articles = merge(existing, fresh)

    if not articles:
        print("沒有任何文章（全部來源失敗且沒有舊資料），中止以免覆蓋線上網站")
        return 1

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    shutil.copytree(WEB_DIR, OUT_DIR)
    OUT_DATA.parent.mkdir(parents=True, exist_ok=True)
    payload = {"updated_at": iso(now_utc()), "sources": status, "articles": articles}
    OUT_DATA.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (OUT_DIR / ".nojekyll").write_text("")
    size_kb = OUT_DATA.stat().st_size / 1024
    print(f"輸出 {len(articles)} 篇文章（新抓 {len(fresh)} 篇）→ {OUT_DATA} ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
