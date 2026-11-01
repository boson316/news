// 新聞蒐集 — GitHub Pages 靜態版
// 資料：data/articles.json（由 GitHub Actions 定時抓 RSS 產生）
// 收藏、已讀、語言、主題：存在瀏覽器 localStorage
"use strict";

const SUPPORTED_LANGS = ["zh-TW", "en"];
const DEFAULT_LANG = "zh-TW";
const PAGE_SIZE = 30;
const AUTO_REFRESH_MS = 10 * 60 * 1000; // 回到分頁時，距離上次載入超過 10 分鐘就自動檢查
const KEY = (name) => `boson-news:${name}`;
const FAV_KEY = KEY("favorites");
const READ_KEY = KEY("read");
const LANG_KEY = KEY("lang");
const THEME_KEY = KEY("theme");
const CONTENT_LANG_KEY = KEY("content-lang");
const LAST_SEEN_KEY = KEY("last-seen");
const READ_MAX = 2000;

const TRANSLATIONS = {
  "zh-TW": {
    app_title: "新聞蒐集",
    headline: "今天的重點新聞",
    app_subtitle: "國際、科技、財經與中文新聞，每 15 分鐘自動更新",
    my_favorites: "收藏",
    source: "來源",
    all_sources: "全部來源",
    keyword: "搜尋",
    keyword_placeholder: "搜尋新聞，例如：AI、利率、晶片",
    search_hint: "按 / 搜尋",
    clear: "清除搜尋",
    period_label: "時間範圍",
    period_day: "24 小時",
    period_week: "一週",
    period_month: "一個月",
    period_quarter: "三個月",
    period_halfyear: "半年",
    period_all: "全部",
    content_lang_label: "文章語言",
    content_all: "全部語言",
    content_zh: "中文",
    content_en: "English",
    refresh_news: "重新載入",
    article_count: "{count} 篇",
    new_count: "{count} 篇新文章",
    updated: "更新於 {time}",
    new_banner: "有 {count} 篇新文章，點這裡查看",
    show_more: "顯示更多（還有 {count} 篇）",
    save: "收藏",
    unsave: "取消收藏",
    new_badge: "新",
    loading: "載入中…",
    load_error_title: "無法載入新聞",
    load_error: "請檢查網路連線後再試一次。",
    retry: "重試",
    empty_title: "沒有符合條件的文章",
    empty_articles: "試試看放寬時間範圍、改選其他來源，或換個關鍵字。",
    show_all_time: "改看全部時間",
    footer_note: "資料來自公開 RSS 來源（BBC、Reuters、Bloomberg、中央社等），僅供學習與個人研究使用。",
    favorites_title: "我的收藏",
    favorites_subtitle: "稍後閱讀的文章，儲存在這個瀏覽器中",
    saved_count: "共 {count} 篇",
    saved_at: "收藏於 {time}",
    empty_favorites_title: "還沒有收藏",
    empty_favorites: "在首頁點文章右側的書籤圖示，就能收藏起來稍後閱讀。",
    back_home: "回首頁",
    today: "今天",
    yesterday: "昨天",
    tab_international: "國際",
    tab_tech: "科技",
    tab_business: "財經",
    tab_bigtech: "大型科技",
    tab_nvidia: "NVIDIA",
    tab_google: "Google",
    tab_microsoft: "Microsoft",
    tab_zh: "中文新聞",
    cat_international: "國際",
    cat_us: "美國",
    cat_tech: "科技",
    cat_business: "財經",
    cat_zh: "中文",
    lang_switch: "EN",
    lang_switch_label: "Switch to English",
    theme_auto: "主題：跟隨系統",
    theme_light: "主題：淺色",
    theme_dark: "主題：深色",
    back_to_top: "回到頂端",
  },
  en: {
    app_title: "Boson News",
    headline: "Today's headlines",
    app_subtitle: "World, tech, business and Chinese-language news, refreshed every 15 minutes",
    my_favorites: "Saved",
    source: "Source",
    all_sources: "All sources",
    keyword: "Search",
    keyword_placeholder: "Search news, e.g. AI, rates, chips",
    search_hint: "Press / to search",
    clear: "Clear search",
    period_label: "Time range",
    period_day: "24 hours",
    period_week: "Week",
    period_month: "Month",
    period_quarter: "3 months",
    period_halfyear: "6 months",
    period_all: "All time",
    content_lang_label: "Article language",
    content_all: "All languages",
    content_zh: "中文",
    content_en: "English",
    refresh_news: "Reload",
    article_count: "{count} articles",
    new_count: "{count} new",
    updated: "Updated {time}",
    new_banner: "{count} new articles — tap to show",
    show_more: "Show more ({count} left)",
    save: "Save",
    unsave: "Remove from saved",
    new_badge: "New",
    loading: "Loading…",
    load_error_title: "Couldn't load the news",
    load_error: "Check your connection and try again.",
    retry: "Retry",
    empty_title: "No matching articles",
    empty_articles: "Try a wider time range, another source, or a different keyword.",
    show_all_time: "Show all time",
    footer_note: "Data from public RSS feeds (BBC, Reuters, Bloomberg, CNA, etc.). For learning and personal research only.",
    favorites_title: "Saved articles",
    favorites_subtitle: "Articles to read later, stored in this browser",
    saved_count: "{count} saved",
    saved_at: "Saved {time}",
    empty_favorites_title: "Nothing saved yet",
    empty_favorites: "Tap the bookmark icon next to any headline to save it for later.",
    back_home: "Home",
    today: "Today",
    yesterday: "Yesterday",
    tab_international: "World",
    tab_tech: "Tech",
    tab_business: "Business",
    tab_bigtech: "Big Tech",
    tab_nvidia: "NVIDIA",
    tab_google: "Google",
    tab_microsoft: "Microsoft",
    tab_zh: "Chinese",
    cat_international: "World",
    cat_us: "US",
    cat_tech: "Tech",
    cat_business: "Business",
    cat_zh: "Chinese",
    lang_switch: "中文",
    lang_switch_label: "切換成中文",
    theme_auto: "Theme: system",
    theme_light: "Theme: light",
    theme_dark: "Theme: dark",
    back_to_top: "Back to top",
  },
};

const BLOCK_KEYS = ["international", "tech", "business", "bigtech", "nvidia", "google", "microsoft", "zh"];
const PERIODS = { day: 1, week: 7, month: 30, quarter: 90, halfyear: 180, all: null };
const CONTENT_LANGS = ["all", "zh", "en"];

const BIG_TECH_KEYWORDS = ["NVIDIA", "Nvidia", "NVDA", "Google", "Alphabet", "Amazon", "AMZN", "Microsoft", "MSFT", "Meta", "Facebook", "META", "Apple", "輝達", "谷歌", "亞馬遜", "微軟", "蘋果"];
const COMPANY_KEYWORDS = {
  nvidia: ["NVIDIA", "Nvidia", "NVDA", "輝達"],
  google: ["Google", "Alphabet", "谷歌"],
  microsoft: ["Microsoft", "MSFT", "微軟"],
};

const ICONS = {
  bookmark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg>',
  auto: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 0 0 18z" fill="currentColor"/></svg>',
  light: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>',
  dark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>',
  arrowUp: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>',
};

// ---------- 儲存 ----------
function storageGet(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}
function storageSet(key, value) {
  try { localStorage.setItem(key, value); } catch { /* 無痕模式等情況忽略 */ }
}
function storageGetJSON(key, fallback) {
  try {
    const v = JSON.parse(storageGet(key) || "null");
    return v ?? fallback;
  } catch {
    return fallback;
  }
}

// ---------- 介面語言 ----------
const params = new URLSearchParams(location.search);
let lang = params.get("lang");
if (SUPPORTED_LANGS.includes(lang)) {
  storageSet(LANG_KEY, lang);
} else {
  lang = storageGet(LANG_KEY);
  if (!SUPPORTED_LANGS.includes(lang)) lang = DEFAULT_LANG;
}
const LOCALE = lang === "zh-TW" ? "zh-TW" : "en-US";

function t(key, vars) {
  let text = (TRANSLATIONS[lang] || TRANSLATIONS[DEFAULT_LANG])[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) text = text.replace(`{${k}}`, v);
  return text;
}

// ---------- 主題 ----------
const THEMES = ["auto", "light", "dark"];
function currentTheme() {
  const th = storageGet(THEME_KEY);
  return THEMES.includes(th) ? th : "auto";
}
function applyTheme(theme) {
  if (theme === "auto") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = theme;
  const btn = document.getElementById("theme-toggle");
  btn.innerHTML = ICONS[theme];
  btn.title = t(`theme_${theme}`);
  btn.setAttribute("aria-label", t(`theme_${theme}`));
}

// ---------- 共用工具 ----------
function el(tag, attrs = {}, text) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text != null) node.textContent = text;
  return node;
}

function safeUrl(url) {
  return /^https?:\/\//i.test(url || "") ? url : "#";
}

function formatAbsolute(isoStr) {
  const d = new Date(isoStr);
  if (Number.isNaN(d.getTime())) return isoStr || "";
  return d.toLocaleString(LOCALE, {
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false,
  });
}

function formatRelative(isoStr) {
  const d = new Date(isoStr);
  if (Number.isNaN(d.getTime())) return "";
  const diffMin = Math.round((d.getTime() - Date.now()) / 60000);
  const rtf = new Intl.RelativeTimeFormat(LOCALE, { numeric: "auto" });
  const abs = Math.abs(diffMin);
  if (abs < 1) return rtf.format(0, "minute");
  if (abs < 60) return rtf.format(diffMin, "minute");
  if (abs < 60 * 24) return rtf.format(Math.round(diffMin / 60), "hour");
  if (abs < 60 * 24 * 7) return rtf.format(Math.round(diffMin / 1440), "day");
  return d.toLocaleDateString(LOCALE, { month: "short", day: "numeric" });
}

function formatTimeOfDay(isoStr) {
  const d = new Date(isoStr);
  return d.toLocaleTimeString(LOCALE, { hour: "2-digit", minute: "2-digit", hour12: false });
}

function dayKey(isoStr) {
  const d = new Date(isoStr);
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

function dayLabel(isoStr) {
  const d = new Date(isoStr);
  const today = new Date();
  const yesterday = new Date(Date.now() - 86400000);
  if (dayKey(d) === dayKey(today)) return t("today");
  if (dayKey(d) === dayKey(yesterday)) return t("yesterday");
  const opts = { month: "long", day: "numeric", weekday: "short" };
  if (d.getFullYear() !== today.getFullYear()) opts.year = "numeric";
  return d.toLocaleDateString(LOCALE, opts);
}

const CJK_RE = /[㐀-鿿]/;
function articleLang(a) {
  return CJK_RE.test(a.title || "") ? "zh" : "en";
}

// ---------- 頁首、主題、回到頂端 ----------
function setupChrome() {
  document.documentElement.lang = lang === "zh-TW" ? "zh-Hant" : "en";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });

  updateLangLink();
  const sw = document.getElementById("lang-switch");
  sw.textContent = t("lang_switch");
  sw.setAttribute("aria-label", t("lang_switch_label"));
  sw.title = t("lang_switch_label");

  document.getElementById("brand").href = `./?lang=${lang}`;
  const favLink = document.getElementById("favorites-link");
  favLink.href = `favorites.html?lang=${lang}`;
  favLink.title = t("my_favorites");

  applyTheme(currentTheme());
  document.getElementById("theme-toggle").addEventListener("click", () => {
    const next = THEMES[(THEMES.indexOf(currentTheme()) + 1) % THEMES.length];
    storageSet(THEME_KEY, next);
    applyTheme(next);
  });

  const top = document.getElementById("back-to-top");
  top.innerHTML = ICONS.arrowUp;
  top.setAttribute("aria-label", t("back_to_top"));
  top.title = t("back_to_top");
  top.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  window.addEventListener("scroll", () => top.classList.toggle("show", window.scrollY > 600), { passive: true });

  updateFavCount();
}

function updateLangLink() {
  const next = new URLSearchParams(location.search);
  next.set("lang", lang === "zh-TW" ? "en" : "zh-TW");
  document.getElementById("lang-switch").href = `?${next}`;
}

// ---------- 收藏 ----------
function loadFavorites() {
  const list = storageGetJSON(FAV_KEY, []);
  return Array.isArray(list) ? list : [];
}
function saveFavorites(list) {
  storageSet(FAV_KEY, JSON.stringify(list));
  updateFavCount();
}
function isFavorite(url) {
  return loadFavorites().some((f) => f.url === url);
}
function toggleFavorite(article) {
  const list = loadFavorites();
  const idx = list.findIndex((f) => f.url === article.url);
  if (idx >= 0) list.splice(idx, 1);
  else list.unshift({ ...article, saved_at: new Date().toISOString() });
  saveFavorites(list);
}
function updateFavCount() {
  const n = loadFavorites().length;
  document.getElementById("fav-count").textContent = n ? String(n) : "";
}

// ---------- 已讀 ----------
let readSet = new Set(storageGetJSON(READ_KEY, []));
function markRead(url) {
  if (readSet.has(url)) return;
  readSet.add(url);
  const list = [...readSet].slice(-READ_MAX);
  readSet = new Set(list);
  storageSet(READ_KEY, JSON.stringify(list));
}

// ---------- 文章卡片 ----------
function renderArticle(a, { favoritesPage = false, onChange, isNew = false } = {}) {
  const li = el("li", { class: `article cat-${a.category}` });
  if (readSet.has(a.url)) li.classList.add("is-read");

  const meta = el("div", { class: "article-meta" });
  if (isNew) meta.append(el("span", { class: "new-dot", title: t("new_badge") }));
  meta.append(el("span", { class: "cat" }, t(`cat_${a.category}`)));
  meta.append(el("span", { class: "dot" }));
  meta.append(el("span", { class: "src" }, a.source));
  if (a.published_at) {
    meta.append(el("span", { class: "dot" }));
    const label = favoritesPage ? formatRelative(a.published_at) : formatTimeOfDay(a.published_at);
    meta.append(el("time", { datetime: a.published_at, title: formatAbsolute(a.published_at) }, label));
  }
  if (favoritesPage && a.saved_at) {
    meta.append(el("span", { class: "dot" }));
    meta.append(el("span", {}, t("saved_at", { time: formatRelative(a.saved_at) })));
  }
  li.append(meta);

  const h3 = el("h3");
  const link = el("a", { href: safeUrl(a.url), target: "_blank", rel: "noopener noreferrer" }, a.title);
  const onOpen = () => {
    markRead(a.url);
    li.classList.add("is-read");
  };
  link.addEventListener("click", onOpen);
  link.addEventListener("auxclick", onOpen);
  h3.append(link);
  li.append(h3);

  if (a.summary && a.summary !== a.title) li.append(el("p", { class: "summary" }, a.summary));

  const btn = el("button", { type: "button", class: "icon-btn bookmark" });
  btn.innerHTML = ICONS.bookmark;
  const sync = () => {
    const saved = isFavorite(a.url);
    btn.setAttribute("aria-pressed", String(saved));
    btn.setAttribute("aria-label", saved ? t("unsave") : t("save"));
    btn.title = saved ? t("unsave") : t("save");
  };
  btn.addEventListener("click", () => {
    toggleFavorite(a);
    sync();
    onChange?.();
  });
  sync();
  li.append(btn);
  return li;
}

function renderSkeleton(list, n = 6) {
  const items = [];
  for (let i = 0; i < n; i++) {
    const li = el("li", { class: "skeleton", "aria-hidden": "true" });
    for (const w of ["30%", "85%", "65%"]) {
      const s = el("span");
      s.style.width = w;
      li.append(s);
    }
    items.push(li);
  }
  list.replaceChildren(...items);
}

function showEmpty(box, title, body, action) {
  box.replaceChildren(el("strong", {}, title), el("span", {}, body));
  if (action) {
    const b = el("button", { type: "button", class: "btn" }, action.label);
    b.addEventListener("click", action.onClick);
    box.append(el("br"), b);
  }
  box.hidden = false;
}

// ---------- 篩選 ----------
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
  if (block === "bigtech" || COMPANY_KEYWORDS[block]) {
    const kws = block === "bigtech" ? BIG_TECH_KEYWORDS : COMPANY_KEYWORDS[block];
    return inPeriod.filter((a) => matchesKeywords(a, kws));
  }
  const cats = block === "international" ? ["international", "us"] : [block];
  return inPeriod.filter((a) => cats.includes(a.category));
}

async function fetchData() {
  const resp = await fetch(`data/articles.json?t=${Date.now()}`, { cache: "no-store" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

function makeChips(container, keys, labelKey, onPick) {
  const buttons = keys.map((key) => {
    const b = el("button", { type: "button", class: "chip", "data-key": key }, t(labelKey(key)));
    b.addEventListener("click", () => onPick(key));
    return b;
  });
  container.replaceChildren(...buttons);
  return (current) => buttons.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.key === current)));
}

// ---------- 首頁 ----------
async function initIndex() {
  const $ = (id) => document.getElementById(id);
  const tabsEl = $("tabs");
  const sourceSel = $("source");
  const qInput = $("q");
  const clearBtn = $("clear-q");
  const list = $("article-list");
  const emptyEl = $("empty");
  const statusEl = $("status-text");
  const reloadBtn = $("reload");
  const moreBtn = $("show-more");
  const banner = $("new-banner");

  const savedContentLang = storageGet(CONTENT_LANG_KEY);
  const state = {
    block: BLOCK_KEYS.includes(params.get("block")) ? params.get("block") : "international",
    period: params.get("period") in PERIODS ? params.get("period") : "day",
    source: params.get("source") || "",
    q: (params.get("q") || "").trim(),
    contentLang: CONTENT_LANGS.includes(savedContentLang) ? savedContentLang : "all",
    shown: PAGE_SIZE,
  };
  let data = null;
  let pending = null; // 背景抓到、尚未顯示的新資料
  let lastLoaded = 0;

  // 上次造訪時看到的最新資料時間，比它新的文章標成「新」
  const prevSeen = storageGet(LAST_SEEN_KEY) || "";

  qInput.placeholder = t("keyword_placeholder");
  qInput.value = state.q;
  qInput.title = t("search_hint");
  clearBtn.setAttribute("aria-label", t("clear"));
  clearBtn.title = t("clear");

  const tabButtons = BLOCK_KEYS.map((key) => {
    const b = el("button", { type: "button", class: "tab", role: "tab", "data-key": key }, t(`tab_${key}`));
    b.addEventListener("click", () => {
      state.block = key;
      b.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
      update({ scroll: true });
    });
    return b;
  });
  tabsEl.replaceChildren(...tabButtons);

  const syncPeriods = makeChips($("periods"), Object.keys(PERIODS), (k) => `period_${k}`, (k) => {
    state.period = k;
    update();
  });
  $("periods").setAttribute("aria-label", t("period_label"));

  const syncContentLang = makeChips($("content-langs"), CONTENT_LANGS, (k) => `content_${k}`, (k) => {
    state.contentLang = k;
    storageSet(CONTENT_LANG_KEY, k);
    update();
  });
  $("content-langs").setAttribute("aria-label", t("content_lang_label"));

  sourceSel.addEventListener("change", () => {
    state.source = sourceSel.value;
    update();
  });

  let timer;
  qInput.addEventListener("input", () => {
    clearBtn.hidden = !qInput.value;
    clearTimeout(timer);
    timer = setTimeout(() => {
      state.q = qInput.value.trim();
      update();
    }, 200);
  });
  const clearSearch = () => {
    qInput.value = "";
    clearBtn.hidden = true;
    state.q = "";
    update();
  };
  clearBtn.addEventListener("click", () => {
    clearSearch();
    qInput.focus();
  });
  clearBtn.hidden = !state.q;

  // 鍵盤：/ 搜尋，Esc 清除
  document.addEventListener("keydown", (e) => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "");
    if (e.key === "/" && !typing && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      qInput.focus();
      qInput.select();
    } else if (e.key === "Escape" && document.activeElement === qInput) {
      if (qInput.value) clearSearch();
      else qInput.blur();
    }
  });

  moreBtn.addEventListener("click", () => {
    state.shown += PAGE_SIZE;
    render();
  });

  banner.addEventListener("click", () => {
    applyPending();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  function syncUrl() {
    const next = new URLSearchParams({ lang, block: state.block, period: state.period });
    if (state.source) next.set("source", state.source);
    if (state.q) next.set("q", state.q);
    history.replaceState(null, "", `?${next}`);
    updateLangLink();
  }

  function update({ scroll = false } = {}) {
    state.shown = PAGE_SIZE;
    syncUrl();
    render();
    if (scroll) {
      const anchor = $("tabs").getBoundingClientRect().top + window.scrollY - 70;
      if (window.scrollY > anchor) window.scrollTo({ top: anchor });
    }
  }

  function filtered() {
    let rows = selectArticles(data.articles, state.block, state.period);
    if (state.contentLang !== "all") rows = rows.filter((a) => articleLang(a) === state.contentLang);

    // 來源下拉：只列出目前條件下有文章的來源，附篇數
    const counts = new Map();
    for (const a of rows) counts.set(a.source, (counts.get(a.source) || 0) + 1);
    const names = [...counts.keys()].sort((x, y) => x.localeCompare(y, undefined, { sensitivity: "base" }));
    if (state.source && !counts.has(state.source)) names.unshift(state.source);
    sourceSel.replaceChildren(
      el("option", { value: "" }, `${t("all_sources")}（${rows.length}）`),
      ...names.map((n) => el("option", { value: n }, `${n}（${counts.get(n) || 0}）`))
    );
    sourceSel.value = state.source;

    if (state.source) rows = rows.filter((a) => a.source === state.source);
    if (state.q) {
      const kw = state.q.toLowerCase();
      rows = rows.filter((a) => (a.title || "").toLowerCase().includes(kw) || (a.summary || "").toLowerCase().includes(kw));
    }
    return rows;
  }

  function render() {
    tabButtons.forEach((b) => b.setAttribute("aria-selected", String(b.dataset.key === state.block)));
    syncPeriods(state.period);
    syncContentLang(state.contentLang);
    if (!data) return;

    const rows = filtered();
    const visible = rows.slice(0, state.shown);
    const isNew = (a) => prevSeen && (a.published_at || "") > prevSeen;

    // 依日期分組
    const items = [];
    let lastDay = null;
    for (const a of visible) {
      const k = a.published_at ? dayKey(a.published_at) : "";
      if (k !== lastDay) {
        lastDay = k;
        if (a.published_at) items.push(el("li", { class: "day-header", role: "presentation" }, dayLabel(a.published_at)));
      }
      items.push(renderArticle(a, { isNew: isNew(a) }));
    }
    list.replaceChildren(...items);

    const remaining = rows.length - visible.length;
    moreBtn.hidden = remaining <= 0;
    moreBtn.textContent = t("show_more", { count: remaining });

    const newCount = rows.filter(isNew).length;
    const parts = [t("article_count", { count: rows.length })];
    if (newCount) parts.push(t("new_count", { count: newCount }));
    if (data.updated_at) parts.push(t("updated", { time: formatRelative(data.updated_at) }));
    statusEl.textContent = parts.join(" · ");
    statusEl.title = data.updated_at ? formatAbsolute(data.updated_at) : "";

    if (rows.length) {
      emptyEl.hidden = true;
    } else {
      showEmpty(
        emptyEl,
        t("empty_title"),
        t("empty_articles"),
        state.period !== "all" ? { label: t("show_all_time"), onClick: () => { state.period = "all"; update(); } } : null
      );
    }
  }

  function rememberSeen() {
    // 停留幾秒後才記錄，避免剛打開就把「新」標記消掉
    if (data?.updated_at) setTimeout(() => storageSet(LAST_SEEN_KEY, data.updated_at), 5000);
  }

  function applyPending() {
    if (!pending) return;
    data = pending;
    pending = null;
    banner.hidden = true;
    render();
    rememberSeen();
  }

  async function load({ silent = false } = {}) {
    reloadBtn.classList.add("spinning");
    reloadBtn.disabled = true;
    if (!data) {
      renderSkeleton(list);
      statusEl.textContent = t("loading");
    }
    try {
      const fresh = await fetchData();
      lastLoaded = Date.now();
      if (silent && data) {
        // 背景更新：有新文章就顯示提示條，不打斷閱讀
        const known = new Set(data.articles.map((a) => a.url));
        const added = fresh.articles.filter((a) => !known.has(a.url)).length;
        if (added > 0) {
          pending = fresh;
          banner.textContent = t("new_banner", { count: added });
          banner.hidden = false;
        }
      } else {
        data = fresh;
        pending = null;
        banner.hidden = true;
        render();
        rememberSeen();
      }
    } catch (err) {
      console.error(err);
      if (!data) {
        list.replaceChildren();
        statusEl.textContent = "";
        showEmpty(emptyEl, t("load_error_title"), t("load_error"), { label: t("retry"), onClick: () => load() });
      }
    } finally {
      reloadBtn.classList.remove("spinning");
      reloadBtn.disabled = false;
    }
  }
  reloadBtn.addEventListener("click", () => load());

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && data && Date.now() - lastLoaded > AUTO_REFRESH_MS) {
      load({ silent: true });
    }
  });

  // 從其他頁面返回時，同步收藏與已讀狀態
  window.addEventListener("pageshow", (e) => {
    if (e.persisted) {
      readSet = new Set(storageGetJSON(READ_KEY, []));
      updateFavCount();
      render();
    }
  });

  render();
  await load();
}

// ---------- 收藏頁 ----------
function initFavorites() {
  const list = document.getElementById("article-list");
  const emptyEl = document.getElementById("empty");
  const statusEl = document.getElementById("status-text");

  function render() {
    const favs = loadFavorites();
    list.replaceChildren(...favs.map((a) => renderArticle(a, { favoritesPage: true, onChange: render })));
    statusEl.textContent = favs.length ? t("saved_count", { count: favs.length }) : "";
    if (favs.length) emptyEl.hidden = true;
    else showEmpty(emptyEl, t("empty_favorites_title"), t("empty_favorites"), {
      label: t("back_home"),
      onClick: () => { location.href = `./?lang=${lang}`; },
    });
  }
  render();
}

setupChrome();
if (document.body.dataset.page === "favorites") initFavorites();
else initIndex();
