import os
import sqlite3
from datetime import datetime, timedelta, timezone

from flask import Flask, render_template, request, redirect, url_for
import feedparser


DB_PATH = os.path.join(os.path.dirname(__file__), "news.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
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
    conn = get_connection()
    with conn:
        for source in RSS_SOURCES:
            try:
                feed = feedparser.parse(source["url"])
            except Exception as e:
                # 某些來源可能因為 SSL 或暫時性網路問題失敗，避免整個程式當掉
                print(f"[RSS] 來源抓取失敗：{source['name']} ({source['url']}) - {e}")
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
# 所以在此先確保資料庫已建立，首次請到網頁點「手動更新新聞」抓資料
init_db()


# 首頁選單：五個區塊的 value 與顯示名稱
BLOCK_OPTIONS = [
    ("international", "國際新聞（World / Geopolitics）"),
    ("tech", "科技新聞（Tech）"),
    ("business", "財經新聞（Business / Markets）"),
    ("bigtech", "大型科技公司追蹤（NVIDIA / Google / Amazon / Microsoft / Meta）"),
    ("nvidia", "NVIDIA 專區"),
    ("google", "Google 專區"),
    ("microsoft", "Microsoft 專區"),
    ("zh", "中文新聞（國際／科技／財經）"),
]


@app.route("/")
def index():
    period = request.args.get("period", "day")
    block = request.args.get("block", "international")
    selected_source = request.args.get("source") or ""
    keyword = request.args.get("q", "").strip()

    # 只抓選中的區塊，每區 30～50 篇（此處用 50）
    limit = 50
    articles: list[sqlite3.Row] = []
    block_label = next((label for v, label in BLOCK_OPTIONS if v == block), block)

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
        block_options=BLOCK_OPTIONS,
        sources=sources,
        selected_source=selected_source,
        keyword=keyword,
        articles=articles,
    )


@app.route("/refresh")
def refresh():
    # 手動觸發更新（抓一次 RSS）
    fetch_and_store_news(limit_per_source=5)
    return render_template("refresh_done.html")


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
    article_id = request.form.get("article_id")
    block = request.form.get("block", "international")
    period = request.form.get("period", "day")
    if not article_id:
        return redirect(url_for("index", block=block, period=period))

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

    return redirect(url_for("index", block=block, period=period))


@app.route("/favorites")
def favorites():
    favs = get_favorites()
    return render_template("favorites.html", favorites=favs)


if __name__ == "__main__":
    fetch_and_store_news(limit_per_source=5)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

