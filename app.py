import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

from flask import Flask, g, jsonify, render_template, request, redirect, url_for
import feedparser


DB_PATH = os.path.join(os.path.dirname(__file__), "news.db")
REFRESH_INTERVAL_MINUTES = 30
SUPPORTED_LANGS = ("zh-TW", "en")
DEFAULT_LANG = "zh-TW"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "zh-TW": {
        "app_title": "新聞蒐集",
        "app_subtitle": "依類別、來源與關鍵字篩選 — 每類最多 50 篇文章",
        "my_favorites": "我的最愛",
        "section": "類別",
        "source": "來源",
        "all_sources": "全部來源",
        "keyword": "關鍵字",
        "keyword_placeholder": "例如：人工智慧、利率、晶片…",
        "time_range": "時間範圍",
        "period_day": "今日／過去 24 小時",
        "period_week": "過去一週",
        "period_month": "過去一個月",
        "period_quarter": "過去一季（3 個月）",
        "period_halfyear": "過去半年",
        "period_all": "全部（由新到舊）",
        "show_news": "顯示新聞",
        "refresh_news": "重新整理新聞",
        "article_count": "{count} 篇文章",
        "save": "收藏",
        "empty_articles": "沒有符合篩選條件的文章。請試著擴大時間範圍，或稍候自動更新完成。",
        "footer_note": "資料來自公開 RSS 來源（BBC、Reuters 等），僅供學習與個人研究使用。",
        "favorites_title": "我的最愛",
        "favorites_subtitle": "你收藏、稍後閱讀的文章（由新到舊）",
        "back_home": "返回首頁",
        "saved_count": "已收藏 {count} 篇文章",
        "saved_at": "收藏於 {time}",
        "empty_favorites": "尚未收藏任何文章。請到首頁點擊「收藏」按鈕。",
        "refresh_done_title": "新聞更新完成",
        "refresh_done_body": "已從所有 RSS 來源抓取最新標題並存入資料庫。",
        "block_international": "國際（世界／地緣政治）",
        "block_tech": "科技",
        "block_business": "財經／市場",
        "block_bigtech": "大型科技公司（NVIDIA／Google／Amazon／Microsoft／Meta）",
        "block_nvidia": "NVIDIA",
        "block_google": "Google",
        "block_microsoft": "Microsoft",
        "block_zh": "中文（國際／科技／財經）",
        "cat_international": "國際",
        "cat_us": "美國",
        "cat_tech": "科技",
        "cat_business": "財經",
        "cat_zh": "中文",
        "lang_switch": "English",
    },
    "en": {
        "app_title": "News Aggregator",
        "app_subtitle": "Filter by section, source, and keyword — up to 50 articles per section",
        "my_favorites": "My Favorites",
        "section": "Section",
        "source": "Source",
        "all_sources": "All sources",
        "keyword": "Keyword",
        "keyword_placeholder": "e.g. AI, rates, chips…",
        "time_range": "Time range",
        "period_day": "Today / last 24 hours",
        "period_week": "Last week",
        "period_month": "Last month",
        "period_quarter": "Last quarter (3 months)",
        "period_halfyear": "Last 6 months",
        "period_all": "All (newest first)",
        "show_news": "Show news",
        "refresh_news": "Refresh News",
        "article_count": "{count} article(s)",
        "save": "Save",
        "empty_articles": "No articles match your filters. Try a wider time range or wait for auto-refresh.",
        "footer_note": "Data from public RSS feeds (BBC, Reuters, etc.). For learning and personal research only.",
        "favorites_title": "My Favorites",
        "favorites_subtitle": "Articles you saved to read later (newest first)",
        "back_home": "Back to home",
        "saved_count": "{count} saved article(s)",
        "saved_at": "Saved {time}",
        "empty_favorites": "No saved articles yet. Go to the home page and click Save on any headline.",
        "refresh_done_title": "News refresh complete",
        "refresh_done_body": "Fetched the latest headlines from all RSS sources and stored them in the database.",
        "block_international": "International (World / Geopolitics)",
        "block_tech": "Tech",
        "block_business": "Business / Markets",
        "block_bigtech": "Big Tech (NVIDIA / Google / Amazon / Microsoft / Meta)",
        "block_nvidia": "NVIDIA",
        "block_google": "Google",
        "block_microsoft": "Microsoft",
        "block_zh": "Chinese (International / Tech / Business)",
        "cat_international": "International",
        "cat_us": "US",
        "cat_tech": "Tech",
        "cat_business": "Business",
        "cat_zh": "Chinese",
        "lang_switch": "中文",
    },
}

BLOCK_KEYS = [
    "international",
    "tech",
    "business",
    "bigtech",
    "nvidia",
    "google",
    "microsoft",
    "zh",
]

_fetch_lock = threading.Lock()
_refresh_running = False


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row  # 讓模板可以用 a.title 這種點記法
    return conn


def init_db():
    conn = get_connection()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                published_at TEXT,
                summary TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        # 收藏表：儲存使用者標記想回頭看的文章
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                published_at TEXT,
                summary TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
    conn.close()


# 預設 RSS 來源（可依需要再擴充或調整）
RSS_SOURCES = [
    # 英文國際新聞
    {
        "name": "BBC World",
        "category": "international",
        "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
    },
    {
        "name": "BBC US & Canada",
        "category": "us",
        "url": "http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
    },
    {
        "name": "Reuters World News",
        "category": "international",
        "url": "http://feeds.reuters.com/Reuters/worldNews",
    },
    # 英文財經／科技
    {
        "name": "Reuters Business News",
        "category": "business",
        "url": "http://feeds.reuters.com/reuters/businessNews",
    },
    {
        "name": "Reuters Technology News",
        "category": "tech",
        "url": "http://feeds.reuters.com/reuters/technologyNews",
    },
    {
        "name": "TechCrunch",
        "category": "tech",
        "url": "https://techcrunch.com/feed/",
    },
    {
        "name": "USA TODAY Tech",
        "category": "tech",
        "url": "http://rssfeeds.usatoday.com/tech/",
    },
    # 中文科技／財經
    {
        "name": "TechNews 科技新報",
        "category": "tech",
        "url": "https://technews.tw/tn-rss/",
    },
    {
        "name": "TechOrange 科技報橘",
        "category": "tech",
        "url": "https://buzzorange.com/techorange/feed/",
    },
    {
        "name": "自由時報 財經",
        "category": "business",
        "url": "https://news.ltn.com.tw/rss/business.xml",
    },
    {
        "name": "ETtoday 財經",
        "category": "business",
        "url": "http://feeds.feedburner.com/ettoday/finance",
    },
    {
        "name": "聯合新聞網 產經",
        "category": "business",
        "url": "https://fund.udn.com/rss/lists/1002",
    },
    # 中文一般新聞（放在 zh 區塊）
    {
        "name": "BBC 中文網",
        "category": "zh",
        "url": "http://www.bbc.co.uk/zhongwen/trad/index.xml",
    },
    {
        "name": "DW 德國之聲 中文",
        "category": "zh",
        "url": "https://rss.dw.com/rdf/rss-chi",
    },
    {
        "name": "自由時報 國際",
        "category": "zh",
        "url": "https://news.ltn.com.tw/rss/world.xml",
    },
]


def fetch_and_store_news(limit_per_source: int = 5) -> None:
    """從多個 RSS 來源抓取新聞並存入 SQLite。"""
    with _fetch_lock:
        conn = get_connection()
        with conn:
            for source in RSS_SOURCES:
                try:
                    feed = feedparser.parse(source["url"])
                except Exception as e:
                    # 某些來源可能因為 SSL 或暫時性網路問題失敗，避免整個程式當掉
                    print(
                        f"[RSS] 來源抓取失敗：{source['name']} ({source['url']}) - {e}"
                    )
                    continue

                count = 0
                for entry in feed.entries:
                    if count >= limit_per_source:
                        break

                    title = entry.get("title", "").strip()
                    link = entry.get("link", "").strip()
                    summary = entry.get("summary", "").strip()

                    if not title or not link:
                        continue

                    # 避免重複（以 URL 為基準）
                    cur = conn.execute(
                        "SELECT 1 FROM articles WHERE url = ?",
                        (link,),
                    )
                    if cur.fetchone():
                        continue

                    published_at_str = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published_at = datetime(
                            entry.published_parsed.tm_year,
                            entry.published_parsed.tm_mon,
                            entry.published_parsed.tm_mday,
                            entry.published_parsed.tm_hour,
                            entry.published_parsed.tm_min,
                            entry.published_parsed.tm_sec,
                            tzinfo=timezone.utc,
                        )
                        # 存成 ISO 字串，顯示時直接印
                        published_at_str = published_at.astimezone(
                            timezone.utc
                        ).strftime("%Y-%m-%d %H:%M")

                    created_at_str = datetime.now(timezone.utc).strftime(
                        "%Y-%m-%d %H:%M"
                    )

                    conn.execute(
                        """
                        INSERT INTO articles
                            (title, source, category, url, summary, published_at, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            title,
                            source["name"],
                            source["category"],
                            link,
                            summary,
                            published_at_str,
                            created_at_str,
                        ),
                    )
                    count += 1

        set_last_refresh()


def get_article_count() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) AS c FROM articles").fetchone()
    conn.close()
    return int(row["c"])


def get_last_refresh() -> datetime | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM meta WHERE key = 'last_refresh'"
    ).fetchone()
    conn.close()
    if not row:
        return None
    try:
        return datetime.fromisoformat(row["value"])
    except ValueError:
        return None


def set_last_refresh() -> None:
    now_str = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO meta (key, value) VALUES ('last_refresh', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (now_str,),
        )
    conn.close()


def should_refresh() -> bool:
    last = get_last_refresh()
    if last is None:
        return True
    return datetime.now(timezone.utc) - last > timedelta(
        minutes=REFRESH_INTERVAL_MINUTES
    )


def ensure_news_loaded() -> None:
    """資料庫為空時同步抓取，避免冷啟動後首頁空白。"""
    if get_article_count() == 0:
        fetch_and_store_news(limit_per_source=5)


def background_refresh_if_needed() -> None:
    """背景執行：資料庫空或超過更新間隔時自動抓取。"""
    import time

    time.sleep(3)
    if get_article_count() == 0 or should_refresh():
        fetch_and_store_news(limit_per_source=5)


def start_background_refresh() -> None:
    thread = threading.Thread(target=background_refresh_if_needed, daemon=True)
    thread.start()


def trigger_background_refresh() -> bool:
    """非阻塞啟動背景更新，供 cron-job.org 等外部排程使用。"""
    global _refresh_running
    if _refresh_running:
        return False

    def _run() -> None:
        global _refresh_running
        _refresh_running = True
        try:
            fetch_and_store_news(limit_per_source=5)
        finally:
            _refresh_running = False

    threading.Thread(target=_run, daemon=True).start()
    return True


def get_block_options(lang: str) -> list[tuple[str, str]]:
    labels = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG])
    return [
        (key, labels[f"block_{key}"])
        for key in BLOCK_KEYS
    ]


def get_category_labels(lang: str) -> dict[str, str]:
    labels = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG])
    return {
        "international": labels["cat_international"],
        "us": labels["cat_us"],
        "tech": labels["cat_tech"],
        "business": labels["cat_business"],
        "zh": labels["cat_zh"],
    }


def t(key: str, **kwargs: str | int) -> str:
    lang = getattr(g, "lang", DEFAULT_LANG)
    text = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def redirect_with_filters(endpoint: str, **kwargs: str):
    """保留篩選參數與語言設定。"""
    lang = getattr(g, "lang", DEFAULT_LANG)
    return redirect(url_for(endpoint, lang=lang, **kwargs))


def get_articles(period: str = "day", category: str | None = None, limit: int = 20):
    """取得特定時間範圍內的新聞。period: day / week / month / quarter / halfyear / all"""
    now = datetime.now(timezone.utc)
    if period == "day":
        since = now - timedelta(days=1)
    elif period == "week":
        since = now - timedelta(days=7)
    elif period == "month":
        since = now - timedelta(days=30)
    elif period == "quarter":
        since = now - timedelta(days=90)
    elif period == "halfyear":
        since = now - timedelta(days=180)
    else:
        since = None

    conn = get_connection()
    params: list[str] = []
    conditions: list[str] = []

    if since is not None:
        since_str = since.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
        conditions.append("published_at >= ?")
        params.append(since_str)

    if category:
        conditions.append("category = ?")
        params.append(category)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT id, title, source, category, url, summary, published_at
        FROM articles
        {where_clause}
        ORDER BY
            CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
            published_at DESC
        LIMIT ?
    """
    params.append(str(limit))

    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_sources():
    """取得目前資料庫中所有來源（用於下拉選單）。"""
    conn = get_connection()
    cur = conn.execute(
        "SELECT DISTINCT source FROM articles ORDER BY source COLLATE NOCASE"
    )
    rows = [r["source"] for r in cur.fetchall()]
    conn.close()
    return rows


def get_articles_multi_categories(
    period: str, categories: list[str], limit: int = 20
):
    """依多個分類抓新聞，用在 fallback 等情境。"""
    now = datetime.now(timezone.utc)
    if period == "day":
        since = now - timedelta(days=1)
    elif period == "week":
        since = now - timedelta(days=7)
    elif period == "month":
        since = now - timedelta(days=30)
    elif period == "quarter":
        since = now - timedelta(days=90)
    elif period == "halfyear":
        since = now - timedelta(days=180)
    else:
        since = None

    conn = get_connection()
    params: list[str] = []
    conditions: list[str] = []

    if since is not None:
        since_str = since.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
        conditions.append("published_at >= ?")
        params.append(since_str)

    if categories:
        placeholders = ",".join("?" for _ in categories)
        conditions.append(f"category IN ({placeholders})")
        params.extend(categories)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT id, title, source, category, url, summary, published_at
        FROM articles
        {where_clause}
        ORDER BY
            CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
            published_at DESC
        LIMIT ?
    """
    params.append(str(limit))

    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows

BIG_TECH_KEYWORDS = [
    "NVIDIA",
    "Nvidia",
    "NVDA",
    "Google",
    "Alphabet",
    "Amazon",
    "AMZN",
    "Microsoft",
    "MSFT",
    "Meta",
    "Facebook",
    "META",
]


COMPANY_KEYWORDS = {
    "nvidia": ["NVIDIA", "Nvidia", "NVDA"],
    "google": ["Google", "Alphabet"],
    "microsoft": ["Microsoft", "MSFT"],
}


def get_big_tech_articles(period: str = "day", limit: int = 20):
    """取得與大型科技公司相關的新聞（依標題與摘要關鍵字）。"""
    now = datetime.now(timezone.utc)
    if period == "day":
        since = now - timedelta(days=1)
    elif period == "week":
        since = now - timedelta(days=7)
    elif period == "month":
        since = now - timedelta(days=30)
    elif period == "quarter":
        since = now - timedelta(days=90)
    elif period == "halfyear":
        since = now - timedelta(days=180)
    else:
        since = None

    conn = get_connection()
    params: list[str] = []
    conditions: list[str] = []

    if since is not None:
        since_str = since.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
        conditions.append("published_at >= ?")
        params.append(since_str)

    keyword_conditions: list[str] = []
    for kw in BIG_TECH_KEYWORDS:
        keyword_conditions.append("(title LIKE ? OR summary LIKE ?)")
        like_kw = f"%{kw}%"
        params.extend([like_kw, like_kw])

    if keyword_conditions:
        conditions.append("(" + " OR ".join(keyword_conditions) + ")")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT id, title, source, category, url, summary, published_at
        FROM articles
        {where_clause}
        ORDER BY
            CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
            published_at DESC
        LIMIT ?
    """
    params.append(str(limit))

    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    # 如果沒有明確包含關鍵字，就退而求其次：
    # 直接從科技＋財經新聞中抓最新的幾篇，避免整塊是空的。
    if not rows:
        rows = get_articles_multi_categories(
            period=period, categories=["tech", "business"], limit=limit
        )

    return rows


def get_company_articles(company_key: str, period: str = "day", limit: int = 20):
    """針對單一公司（如 NVIDIA / Google / Microsoft）抓新聞。"""
    keywords = COMPANY_KEYWORDS.get(company_key)
    if not keywords:
        return []

    now = datetime.now(timezone.utc)
    if period == "day":
        since = now - timedelta(days=1)
    elif period == "week":
        since = now - timedelta(days=7)
    elif period == "month":
        since = now - timedelta(days=30)
    elif period == "quarter":
        since = now - timedelta(days=90)
    elif period == "halfyear":
        since = now - timedelta(days=180)
    else:
        since = None

    conn = get_connection()
    params: list[str] = []
    conditions: list[str] = []

    if since is not None:
        since_str = since.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
        conditions.append("published_at >= ?")
        params.append(since_str)

    keyword_conditions: list[str] = []
    for kw in keywords:
        keyword_conditions.append("(title LIKE ? OR summary LIKE ?)")
        like_kw = f"%{kw}%"
        params.extend([like_kw, like_kw])

    if keyword_conditions:
        conditions.append("(" + " OR ".join(keyword_conditions) + ")")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT id, title, source, category, url, summary, published_at
        FROM articles
        {where_clause}
        ORDER BY
            CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
            published_at DESC
        LIMIT ?
    """
    params.append(str(limit))

    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    # 若抓不到，就退到科技＋財經的最新文章
    if not rows:
        rows = get_articles_multi_categories(
            period=period, categories=["tech", "business"], limit=limit
        )

    return rows

app = Flask(__name__)

# 部署到雲端時（如 Render）會用 gunicorn 啟動，不會跑下面 if __name__，
# 因此在模組載入時初始化資料庫並啟動背景更新
init_db()
start_background_refresh()


@app.before_request
def set_language() -> None:
    lang = request.args.get("lang")
    if lang in SUPPORTED_LANGS:
        g.lang = lang
        g.set_lang_cookie = True
    else:
        cookie_lang = request.cookies.get("lang", DEFAULT_LANG)
        g.lang = cookie_lang if cookie_lang in SUPPORTED_LANGS else DEFAULT_LANG
        g.set_lang_cookie = False


@app.after_request
def save_language_cookie(response):
    if getattr(g, "set_lang_cookie", False):
        response.set_cookie("lang", g.lang, max_age=365 * 24 * 3600)
    return response


def other_lang() -> str:
    return "en" if g.lang == "zh-TW" else "zh-TW"


@app.context_processor
def inject_ui_labels():
    return {
        "t": t,
        "lang": lambda: g.lang,
        "other_lang": other_lang,
        "category_labels": get_category_labels(getattr(g, "lang", DEFAULT_LANG)),
        "html_lang": lambda: "zh-Hant" if g.lang == "zh-TW" else "en",
    }


@app.route("/")
def index():
    ensure_news_loaded()

    period = request.args.get("period", "day")
    block = request.args.get("block", "international")
    selected_source = request.args.get("source") or ""
    keyword = request.args.get("q", "").strip()
    block_options = get_block_options(g.lang)

    # 只抓選中的區塊，每區 30～50 篇（此處用 50）
    limit = 50
    articles: list[sqlite3.Row] = []
    block_label = next((label for v, label in block_options if v == block), block)

    if block == "international":
        articles = get_articles(
            period=period, category="international", limit=limit
        )
    elif block == "tech":
        articles = get_articles(period=period, category="tech", limit=limit)
    elif block == "business":
        articles = get_articles(period=period, category="business", limit=limit)
    elif block == "bigtech":
        articles = get_big_tech_articles(period=period, limit=limit)
    elif block == "nvidia":
        articles = get_company_articles("nvidia", period=period, limit=limit)
    elif block == "google":
        articles = get_company_articles("google", period=period, limit=limit)
    elif block == "microsoft":
        articles = get_company_articles("microsoft", period=period, limit=limit)
    elif block == "zh":
        articles = get_articles(period=period, category="zh", limit=limit)
    else:
        articles = get_articles(period=period, category="international", limit=limit)

    # 來源過濾
    if selected_source:
        articles = [a for a in articles if a["source"] == selected_source]

    # 關鍵字過濾（標題＋摘要）
    if keyword:
        kw_lower = keyword.lower()
        filtered: list[sqlite3.Row] = []
        for a in articles:
            title = (a["title"] or "").lower()
            summary = (a["summary"] or "").lower() if a["summary"] else ""
            if kw_lower in title or kw_lower in summary:
                filtered.append(a)
        articles = filtered

    # 所有來源（給下拉選單用）
    sources = get_all_sources()

    return render_template(
        "index.html",
        period=period,
        block=block,
        block_label=block_label,
        block_options=block_options,
        sources=sources,
        selected_source=selected_source,
        keyword=keyword,
        articles=articles,
    )


@app.route("/refresh")
def refresh():
    fetch_and_store_news(limit_per_source=5)
    block = request.args.get("block", "international")
    period = request.args.get("period", "day")
    return redirect_with_filters("index", block=block, period=period)


@app.route("/cron/refresh")
def cron_refresh():
    """供 cron-job.org 等外部排程呼叫：立即回應，背景抓 RSS（避免 30 秒逾時）。"""
    started = trigger_background_refresh()
    if started:
        return jsonify({"status": "started"}), 202
    return jsonify({"status": "already_running"}), 200


@app.route("/health")
def health():
    """健康檢查：確認服務已啟動且資料庫可讀。"""
    return jsonify(
        {
            "status": "ok",
            "articles": get_article_count(),
            "last_refresh": (
                get_last_refresh().isoformat() if get_last_refresh() else None
            ),
        }
    ), 200


def get_favorites(limit: int = 200):
    conn = get_connection()
    cur = conn.execute(
        """
        SELECT id, article_id, title, source, category, url, summary, published_at, created_at
        FROM favorites
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


@app.post("/favorite")
def favorite():
    lang = request.form.get("lang")
    if lang in SUPPORTED_LANGS:
        g.lang = lang
        g.set_lang_cookie = True

    article_id = request.form.get("article_id")
    block = request.form.get("block", "international")
    period = request.form.get("period", "day")
    if not article_id:
        return redirect_with_filters("index", block=block, period=period)

    conn = get_connection()
    with conn:
        cur = conn.execute(
            """
            SELECT id, title, source, category, url, summary, published_at
            FROM articles
            WHERE id = ?
            """,
            (article_id,),
        )
        row = cur.fetchone()
        if row:
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            conn.execute(
                """
                INSERT OR IGNORE INTO favorites
                    (article_id, title, source, category, url, summary, published_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["title"],
                    row["source"],
                    row["category"],
                    row["url"],
                    row["summary"],
                    row["published_at"],
                    now_str,
                ),
            )

    return redirect_with_filters("index", block=block, period=period)


@app.route("/favorites")
def favorites():
    favs = get_favorites()
    return render_template("favorites.html", favorites=favs)


if __name__ == "__main__":
    ensure_news_loaded()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

