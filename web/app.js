// 新聞蒐集 — GitHub Pages 靜態版
// 資料：data/articles.json（由 GitHub Actions 定時抓 RSS 產生）
// 收藏：存在瀏覽器 localStorage（每台裝置／瀏覽器各自獨立）
"use strict";

const SUPPORTED_LANGS = ["zh-TW", "en"];
const DEFAULT_LANG = "zh-TW";
const LIMIT = 50;
const FAV_KEY = "boson-news:favorites";
const LANG_KEY = "boson-news:lang";

const TRANSLATIONS = {
  "zh-TW": {
    app_title: "新聞蒐集",
    app_subtitle: "依類別、來源與關鍵字篩選 — 每類最多 50 篇文章",
    my_favorites: "我的最愛",
    section: "類別",
    source: "來源",
    all_sources: "全部來源",
    keyword: "關鍵字",
    keyword_placeholder: "例如：人工智慧、利率、晶片…",
    time_range: "時間範圍",
    period_day: "今日／過去 24 小時",
    period_week: "過去一週",
    period_month: "過去一個月",
    period_quarter: "過去一季（3 個月）",
    period_halfyear: "過去半年",
    period_all: "全部（由新到舊）",
    show_news: "顯示新聞",
    refresh_news: "重新載入",
    article_count: "{count} 篇文章",
    save: "收藏",
    saved: "已收藏 ✓",
    remove: "移除",
    loading: "載入中…",
    load_error: "無法載入新聞資料，請稍後再試。",
    updated_at: "最後更新：{time}（每 15 分鐘自動更新）",
    empty_articles: "沒有符合篩選條件的文章。請試著擴大時間範圍。",
    footer_note: "資料來自公開 RSS 來源（BBC、TechCrunch 等），僅供學習與個人研究使用。",
    favorites_title: "我的最愛",
    favorites_subtitle: "你收藏、稍後閱讀的文章（由新到舊，儲存在此瀏覽器）",
    back_home: "返回首頁",
    saved_count: "已收藏 {count} 篇文章",
    saved_at: "收藏於 {time}",
    empty_favorites: "尚未收藏任何文章。請到首頁點擊「收藏」按鈕。",
    block_international: "國際（世界／地緣政治）",
    block_tech: "科技",
    block_business: "財經／市場",
    block_bigtech: "大型科技公司（NVIDIA／Google／Amazon／Microsoft／Meta）",
    block_nvidia: "NVIDIA",
    block_google: "Google",
    block_microsoft: "Microsoft",
    block_zh: "中文（國際／科技／財經）",
    cat_international: "國際",
    cat_us: "美國",
    cat_tech: "科技",
    cat_business: "財經",
    cat_zh: "中文",
    lang_switch: "English",
  },
  en: {
    app_title: "News Aggregator",
    app_subtitle: "Filter by section, source, and keyword — up to 50 articles per section",
    my_favorites: "My Favorites",
    section: "Section",
    source: "Source",
    all_sources: "All sources",
    keyword: "Keyword",
    keyword_placeholder: "e.g. AI, rates, chips…",
    time_range: "Time range",
    period_day: "Today / last 24 hours",
    period_week: "Last week",
    period_month: "Last month",
    period_quarter: "Last quarter (3 months)",
    period_halfyear: "Last 6 months",
    period_all: "All (newest first)",
    show_news: "Show news",
    refresh_news: "Reload",
    article_count: "{count} article(s)",
    save: "Save",
    saved: "Saved ✓",
    remove: "Remove",
    loading: "Loading…",
    load_error: "Could not load news data. Please try again later.",
    updated_at: "Last updated: {time} (auto-refreshes every 15 min)",
    empty_articles: "No articles match your filters. Try a wider time range.",
    footer_note: "Data from public RSS feeds (BBC, TechCrunch, etc.). For learning and personal research only.",
    favorites_title: "My Favorites",
    favorites_subtitle: "Articles you saved to read later (newest first, stored in this browser)",
    back_home: "Back to home",
    saved_count: "{count} saved article(s)",
    saved_at: "Saved {time}",
    empty_favorites: "No saved articles yet. Go to the home page and click Save on any headline.",
    block_international: "International (World / Geopolitics)",
    block_tech: "Tech",
    block_business: "Business / Markets",
    block_bigtech: "Big Tech (NVIDIA / Google / Amazon / Microsoft / Meta)",
    block_nvidia: "NVIDIA",
    block_google: "Google",
    block_microsoft: "Microsoft",
    block_zh: "Chinese (International / Tech / Business)",
    cat_international: "International",
    cat_us: "US",
    cat_tech: "Tech",
    cat_business: "Business",
    cat_zh: "Chinese",
    lang_switch: "中文",
  },
};

const BLOCK_KEYS = ["international", "tech", "business", "bigtech", "nvidia", "google", "microsoft", "zh"];
const PERIODS = { day: 1, week: 7, month: 30, quarter: 90, halfyear: 180, all: null };

const BIG_TECH_KEYWORDS = ["NVIDIA", "Nvidia", "NVDA", "Google", "Alphabet", "Amazon", "AMZN", "Microsoft", "MSFT", "Meta", "Facebook", "META"];
const COMPANY_KEYWORDS = {
  nvidia: ["NVIDIA", "Nvidia", "NVDA"],
  google: ["Google", "Alphabet"],
  microsoft: ["Microsoft", "MSFT"],
};

// ---------- 語言 ----------
function storageGet(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}
function storageSet(key, value) {
  try { localStorage.setItem(key, value); } catch { /* 無痕模式等情況忽略 */ }
}

const params = new URLSearchParams(location.search);
let lang = params.get("lang");
if (SUPPORTED_LANGS.includes(lang)) {
  storageSet(LANG_KEY, lang);
} else {
  lang = storageGet(LANG_KEY);
  if (!SUPPORTED_LANGS.includes(lang)) lang = DEFAULT_LANG;
}

function t(key, vars) {
  let text = (TRANSLATIONS[lang] || TRANSLATIONS[DEFAULT_LANG])[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) text = text.replace(`{${k}}`, v);
  return text;
}

function otherLang() {
  return lang === "zh-TW" ? "en" : "zh-TW";
}

function applyStaticTexts() {
  document.documentElement.lang = lang === "zh-TW" ? "zh-Hant" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  const sw = document.getElementById("lang-switch");
  sw.textContent = t("lang_switch");
  const next = new URLSearchParams(location.search);
  next.set("lang", otherLang());
  sw.href = `?${next}`;
}

// ---------- 工具 ----------
function formatTime(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  if (Number.isNaN(d.getTime())) return isoStr;
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function el(tag, attrs = {}, text) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text != null) node.textContent = text;
  return node;
}

function safeUrl(url) {
  return /^https?:\/\//i.test(url || "") ? url : "#";
}

// ---------- 收藏（localStorage） ----------
function loadFavorites() {
  try {
    const list = JSON.parse(storageGet(FAV_KEY) || "[]");
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}
function saveFavorites(list) {
  storageSet(FAV_KEY, JSON.stringify(list));
}
function isFavorite(url) {
  return loadFavorites().some((f) => f.url === url);
}
function addFavorite(article) {
  const list = loadFavorites();
  if (list.some((f) => f.url === article.url)) return;
  list.unshift({ ...article, saved_at: new Date().toISOString() });
  saveFavorites(list);
}
function removeFavorite(url) {
  saveFavorites(loadFavorites().filter((f) => f.url !== url));
}

// ---------- 文章渲染 ----------
function renderArticle(a, { favoritesPage = false, onRemove } = {}) {
  const li = el("li", { class: "article-item" });

  const h3 = el("h3", { class: "article-title" });
  h3.append(el("a", { href: safeUrl(a.url), target: "_blank", rel: "noopener noreferrer" }, a.title));
  li.append(h3);

  const meta = el("div", { class: "meta" });
  meta.append(el("span", { class: "badge" }, t(`cat_${a.category}`)));
  meta.append(el("span", { class: "source" }, a.source));
  if (a.published_at) meta.append(el("span", { class: "time" }, formatTime(a.published_at)));
  if (favoritesPage && a.saved_at) meta.append(el("span", { class: "time" }, t("saved_at", { time: formatTime(a.saved_at) })));
  li.append(meta);

  if (a.summary) li.append(el("p", { class: "summary" }, a.summary));

  const actions = el("div", { class: "favorite-form" });
  if (favoritesPage) {
    const btn = el("button", { type: "button", class: "button secondary small" }, t("remove"));
    btn.addEventListener("click", () => {
      removeFavorite(a.url);
      onRemove?.();
    });
    actions.append(btn);
  } else {
    const btn = el("button", { type: "button", class: "button secondary small" });
    const sync = () => {
      const saved = isFavorite(a.url);
      btn.textContent = saved ? t("saved") : t("save");
      btn.classList.toggle("saved", saved);
    };
    btn.addEventListener("click", () => {
      if (isFavorite(a.url)) removeFavorite(a.url);
      else addFavorite(a);
      sync();
    });
    sync();
    actions.append(btn);
  }
  li.append(actions);
  return li;
}

// ---------- 首頁 ----------
function sinceIso(period) {
  const days = PERIODS[period];
  if (days == null) return null;
  return new Date(Date.now() - days * 86400 * 1000).toISOString().slice(0, 19) + "Z";
}

function matchesKeywords(a, keywords) {
  return keywords.some((kw) => (a.title || "").includes(kw) || (a.summary || "").includes(kw));
}

function selectArticles(all, block, period) {
  const since = sinceIso(period);
  const inPeriod = since ? all.filter((a) => (a.published_at || "") >= since) : all.slice();
  const byCategory = (cats) => inPeriod.filter((a) => cats.includes(a.category));

  let rows;
  if (block === "bigtech" || COMPANY_KEYWORDS[block]) {
    const kws = block === "bigtech" ? BIG_TECH_KEYWORDS : COMPANY_KEYWORDS[block];
    rows = inPeriod.filter((a) => matchesKeywords(a, kws));
    // 沒有相關文章時退回科技＋財經最新文章，避免整塊空白
    if (!rows.length) rows = byCategory(["tech", "business"]);
  } else if (["international", "tech", "business", "zh"].includes(block)) {
    rows = byCategory([block]);
  } else {
    rows = byCategory(["international"]);
  }
  return rows.slice(0, LIMIT);
}

async function fetchData() {
  const resp = await fetch(`data/articles.json?t=${Date.now()}`, { cache: "no-store" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

async function initIndex() {
  const form = document.getElementById("filter-form");
  const blockSel = document.getElementById("block");
  const sourceSel = document.getElementById("source");
  const periodSel = document.getElementById("period");
  const qInput = document.getElementById("q");
  const list = document.getElementById("article-list");
  const metaEl = document.getElementById("block-meta");
  const emptyEl = document.getElementById("empty");
  const labelEl = document.getElementById("block-label");
  const updatedEl = document.getElementById("updated-at");

  const state = {
    block: BLOCK_KEYS.includes(params.get("block")) ? params.get("block") : "international",
    period: params.get("period") in PERIODS ? params.get("period") : "day",
    source: params.get("source") || "",
    q: (params.get("q") || "").trim(),
  };

  for (const key of BLOCK_KEYS) blockSel.append(el("option", { value: key }, t(`block_${key}`)));
  for (const key of Object.keys(PERIODS)) periodSel.append(el("option", { value: key }, t(`period_${key}`)));
  qInput.placeholder = t("keyword_placeholder");
  document.getElementById("favorites-link").href = `favorites.html?lang=${lang}`;

  let data = { articles: [] };

  function render() {
    blockSel.value = state.block;
    periodSel.value = state.period;
    qInput.value = state.q;
    labelEl.textContent = t(`block_${state.block}`);

    let rows = selectArticles(data.articles, state.block, state.period);
    if (state.source) rows = rows.filter((a) => a.source === state.source);
    if (state.q) {
      const kw = state.q.toLowerCase();
      rows = rows.filter((a) => (a.title || "").toLowerCase().includes(kw) || (a.summary || "").toLowerCase().includes(kw));
    }

    list.replaceChildren(...rows.map((a) => renderArticle(a)));
    metaEl.textContent = rows.length ? t("article_count", { count: rows.length }) : "";
    emptyEl.hidden = rows.length > 0;
    emptyEl.textContent = t("empty_articles");
  }

  function populateSources() {
    const names = [...new Set(data.articles.map((a) => a.source))].sort((a, b) =>
      a.localeCompare(b, undefined, { sensitivity: "base" })
    );
    sourceSel.replaceChildren(el("option", { value: "" }, t("all_sources")), ...names.map((n) => el("option", { value: n }, n)));
    sourceSel.value = names.includes(state.source) ? state.source : "";
  }

  async function load() {
    metaEl.textContent = t("loading");
    try {
      data = await fetchData();
      updatedEl.textContent = data.updated_at ? t("updated_at", { time: formatTime(data.updated_at) }) : "";
      populateSources();
      render();
    } catch (err) {
      console.error(err);
      metaEl.textContent = "";
      emptyEl.hidden = false;
      emptyEl.textContent = t("load_error");
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    state.block = blockSel.value;
    state.period = periodSel.value;
    state.source = sourceSel.value;
    state.q = qInput.value.trim();
    const next = new URLSearchParams({ lang, block: state.block, period: state.period });
    if (state.source) next.set("source", state.source);
    if (state.q) next.set("q", state.q);
    history.replaceState(null, "", `?${next}`);
    applyStaticTexts(); // 更新語言切換連結，保留篩選條件
    render();
  });
  document.getElementById("reload").addEventListener("click", load);

  // 從別的分頁回來時，同步收藏按鈕狀態
  window.addEventListener("pageshow", (e) => { if (e.persisted) render(); });

  await load();
}

// ---------- 我的最愛 ----------
function initFavorites() {
  const list = document.getElementById("article-list");
  const metaEl = document.getElementById("block-meta");
  const emptyEl = document.getElementById("empty");
  document.getElementById("home-link").href = `./?lang=${lang}`;

  function render() {
    const favs = loadFavorites();
    list.replaceChildren(...favs.map((a) => renderArticle(a, { favoritesPage: true, onRemove: render })));
    metaEl.textContent = favs.length ? t("saved_count", { count: favs.length }) : "";
    emptyEl.hidden = favs.length > 0;
    emptyEl.textContent = t("empty_favorites");
  }
  render();
}

applyStaticTexts();
if (document.body.dataset.page === "favorites") initFavorites();
else initIndex();
