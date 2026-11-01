"""檢測 RSS 來源是否可用（在 GitHub Actions 上執行，印出每個來源的狀態）。

用法：python scripts/check_feeds.py
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

import feedparser
import requests

UA_BOT = "Mozilla/5.0 (compatible; boson-news/1.0; +https://github.com/boson316/news)"
UA_BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
BAD_XML_CHARS = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]")

CANDIDATES = [
    # --- 目前壞掉的來源與替代網址 ---
    ("broken", "自由時報 國際", "https://news.ltn.com.tw/rss/world.xml"),
    ("broken", "自由時報 全部", "https://news.ltn.com.tw/rss/all.xml"),
    ("broken", "聯合新聞網 產經 (fund)", "https://fund.udn.com/rss/lists/1002"),
    ("broken", "聯合新聞網 產經", "https://udn.com/rssfeed/news/2/6644?ch=news"),
    ("broken", "聯合新聞網 國際", "https://udn.com/rssfeed/news/2/7225?ch=news"),
    ("broken", "聯合新聞網 即時", "https://udn.com/rssfeed/news/2/6638?ch=news"),
    ("broken", "DW 中文 (rdf)", "https://rss.dw.com/rdf/rss-chi"),
    ("broken", "DW 中文 全部 xml", "https://rss.dw.com/xml/rss-chi-all"),
    ("broken", "DW 中文 全部 rdf", "https://rss.dw.com/rdf/rss-chi-all"),
    ("broken", "USA TODAY Tech", "http://rssfeeds.usatoday.com/tech/"),
    # --- 國際（英文）---
    ("intl", "Reuters (Google News)", "https://news.google.com/rss/search?q=site:reuters.com+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ("intl", "AP News", "https://apnews.com/index.rss"),
    ("intl", "AP News (Google News)", "https://news.google.com/rss/search?q=site:apnews.com+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ("intl", "The Guardian World", "https://www.theguardian.com/world/rss"),
    ("intl", "NYT World", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
    ("intl", "Washington Post World", "https://feeds.washingtonpost.com/rss/world"),
    ("intl", "Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("intl", "NPR World", "https://feeds.npr.org/1004/rss.xml"),
    ("intl", "CNN World", "http://rss.cnn.com/rss/edition_world.rss"),
    ("intl", "DW English", "https://rss.dw.com/rdf/rss-en-world"),
    ("intl", "France 24", "https://www.france24.com/en/rss"),
    ("intl", "CNA Asia", "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511"),
    ("intl", "Nikkei Asia", "https://asia.nikkei.com/rss/feed/nar"),
    ("intl", "The Japan Times", "https://www.japantimes.co.jp/feed/"),
    # --- 財經（英文）---
    ("biz", "CNBC Top News", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("biz", "CNBC Business", "https://www.cnbc.com/id/10001147/device/rss/rss.html"),
    ("biz", "Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ("biz", "WSJ World", "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),
    ("biz", "WSJ Markets", "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ("biz", "MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("biz", "Financial Times", "https://www.ft.com/rss/home"),
    ("biz", "Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ("biz", "The Economist", "https://www.economist.com/finance-and-economics/rss.xml"),
    # --- 科技（英文）---
    ("tech", "The Verge", "https://www.theverge.com/rss/index.xml"),
    ("tech", "Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("tech", "Wired", "https://www.wired.com/feed/rss"),
    ("tech", "Engadget", "https://www.engadget.com/rss.xml"),
    ("tech", "MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ("tech", "Hacker News", "https://hnrss.org/frontpage"),
    ("tech", "Tom's Hardware", "https://www.tomshardware.com/feeds/all"),
    # --- 台灣中文 ---
    ("tw", "中央社 國際", "https://feeds.feedburner.com/rsscna/intworld"),
    ("tw", "中央社 財經", "https://feeds.feedburner.com/rsscna/finance"),
    ("tw", "中央社 科技", "https://feeds.feedburner.com/rsscna/technology"),
    ("tw", "中央社 政治", "https://feeds.feedburner.com/rsscna/politics"),
    ("tw", "公視新聞", "https://news.pts.org.tw/xml/newsfeed.xml"),
    ("tw", "經濟日報", "https://money.udn.com/rssfeed/news/1001/5591?ch=money"),
    ("tw", "天下雜誌", "https://www.cw.com.tw/RSS/cw_content.xml"),
    ("tw", "iThome", "https://www.ithome.com.tw/rss"),
    ("tw", "數位時代", "https://www.bnext.com.tw/rss"),
    ("tw", "報導者", "https://www.twreporter.org/a/rss2.xml"),
    ("tw", "風傳媒", "https://www.storm.mg/feeds"),
    ("tw", "Yahoo 奇摩 國際", "https://tw.news.yahoo.com/rss/world"),
    ("tw", "Yahoo 奇摩 財經", "https://tw.news.yahoo.com/rss/finance"),
    ("tw", "中央廣播電台", "https://www.rti.org.tw/rss"),
    ("tw", "鉅亨網 台股", "https://news.cnyes.com/rss/cat/tw_stock"),
    # --- 中文國際媒體 ---
    ("zh", "紐約時報中文網", "https://cn.nytimes.com/rss/zh-hant/"),
    ("zh", "法廣 RFI 中文", "https://www.rfi.fr/tw/rss"),
    ("zh", "聯合早報 國際", "https://www.zaobao.com.sg/rss/realtime/world"),
    ("zh", "日經中文網", "https://zh.cn.nikkei.com/rss.html"),
]


def try_fetch(url: str, ua: str):
    headers = {
        "User-Agent": ua,
        "Accept": "application/rss+xml, application/rdf+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }
    return requests.get(url, headers=headers, timeout=20)


def check(item):
    group, name, url = item
    out = []
    for label, ua in (("bot", UA_BOT), ("browser", UA_BROWSER)):
        try:
            r = try_fetch(url, ua)
        except Exception as e:  # noqa: BLE001
            out.append(f"{label}: EXC {type(e).__name__}: {str(e)[:120]}")
            continue
        ctype = r.headers.get("content-type", "")
        feed = feedparser.parse(r.content)
        n = len(feed.entries)
        info = f"{label}: HTTP {r.status_code} type={ctype[:40]!r} final={r.url[:80]} entries={n}"
        if n == 0:
            cleaned = BAD_XML_CHARS.sub(b"", r.content)
            n2 = len(feedparser.parse(cleaned).entries)
            info += f" bozo={feed.get('bozo_exception')!s:.100} cleaned_entries={n2} head={r.content[:120]!r}"
        else:
            e0 = feed.entries[0]
            info += (
                f" newest={e0.get('published', e0.get('updated', '?'))!s:.40}"
                f" title={e0.get('title', '')[:50]!r} summary_len={len(e0.get('summary', ''))}"
            )
        out.append(info)
    return group, name, url, out


def main():
    with ThreadPoolExecutor(max_workers=10) as pool:
        for group, name, url, out in pool.map(check, CANDIDATES):
            ok = any("HTTP 200" in o and "entries=0" not in o for o in out)
            print(f"{'OK ' if ok else 'BAD'} [{group}] {name} <{url}>")
            for o in out:
                print(f"      {o}")


if __name__ == "__main__":
    main()
