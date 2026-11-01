# 新聞蒐集（Flask）

**Languages:** [English](README.md) · [中文](README.zh-TW.md)

**線上（GitHub Pages，推薦）：** https://boson316.github.io/news/
**舊版（Render，會冷啟動）：** https://boson-news-app.onrender.com

使用 Python + Flask + SQLite 的新聞蒐集網站，從多個公開 RSS 來源抓取國際、科技、財經、中文新聞。預設**繁體中文介面**，可切換英文。可本機執行或部署到 Render。

> 僅供個人學習與研究使用，請勿用於商業用途。

---

## GitHub Pages 靜態版（推薦：免費、沒有冷啟動）

GitHub Actions 每 15 分鐘抓一次 RSS，產生靜態網站部署到 GitHub Pages。打開網頁不需要等伺服器喚醒，永久免費。

| 項目 | 說明 |
|------|------|
| 抓取 | `scripts/build_site.py`：抓 RSS → 合併線上舊資料 → 輸出 `_site/` |
| 排程 | `.github/workflows/pages.yml`：每 15 分鐘、push 到 `main`、或手動執行 |
| 前端 | `web/`（`index.html`、`favorites.html`、`app.js`、`style.css`），篩選在瀏覽器完成 |
| 歷史 | 保留最近 180 天，每個來源最多 300 篇 |
| 收藏 | 存在瀏覽器 `localStorage`（每台裝置各自獨立） |

### 第一次啟用

1. 把這些檔案合併到 `main`
2. GitHub repo → **Settings → Pages → Build and deployment → Source** 選 **GitHub Actions**
3. **Actions** → **Update news & deploy Pages** → **Run workflow**
4. 約 1 分鐘後打開 https://boson316.github.io/news/

> GitHub 排程常延遲幾分鐘；repo 若 60 天沒有任何活動，GitHub 會自動暫停排程，到 Actions 頁面重新啟用即可。

### 本機預覽

```bash
pip install -r requirements.txt
python scripts/build_site.py
python -m http.server -d _site 8000
```

瀏覽器：`http://127.0.0.1:8000`

---

## 功能

| 功能 | 說明 |
|------|------|
| 預設中文 | 介面預設繁體中文，右上角可切 English |
| 自動抓取 | 首頁開啟時若資料庫為空，自動抓 RSS |
| 背景更新 | 啟動後每 30 分鐘背景更新（若已過期） |
| 定時排程 | cron-job.org 每 **10 分鐘** 呼叫 `/cron/refresh` |
| 篩選 | 類別、來源、關鍵字、時間範圍 |
| 收藏 | 標記稍後閱讀 |

---

## 方式一：線上使用（Render）

**GitHub：** https://github.com/boson316/news

### 部署步驟

1. Push 本資料夾內容到 repo **根目錄**（`app.py`、`requirements.txt`、`templates/`、`static/`、`render.yaml`、`runtime.txt`）
2. [Render](https://render.com) → **New → Web Service** → 選 repo
3. **Build：** `pip install -r requirements.txt`
4. **Start：** `gunicorn app:app --bind 0.0.0.0:$PORT`
5. 或使用 **Blueprint** 匯入 `render.yaml`（服務名稱 `boson-news-app`）

### 驗證部署

| URL | 預期結果 |
|-----|----------|
| https://boson-news-app.onrender.com/ | 首頁「新聞蒐集」 |
| https://boson-news-app.onrender.com/cron/refresh | `{"status":"started"}` |
| https://boson-news-app.onrender.com/health | `{"status":"ok","articles":...}` |

### cron-job.org（建議）

Render 免費方案約 15 分鐘無流量會休眠。設定定時工作：

1. [cron-job.org](https://cron-job.org) → **+ 建立定時工作**
2. **URL：** `https://boson-news-app.onrender.com/cron/refresh`
3. **方法：** GET
4. **排程：** 每 **10 分鐘**（`*/10 * * * *`）
5. Execution history 應見 `{"status":"started"}` 或 `{"status":"already_running"}`

> `/cron/refresh` 立刻回應、背景抓 RSS，避免 cron-job.org 30 秒逾時。

---

## 方式二：本機執行

```bash
pip install -r requirements.txt
python app.py
```

瀏覽器：`http://127.0.0.1:5000`

---

## API 端點

| 方法 | 路徑 | 用途 |
|------|------|------|
| GET | `/` | 首頁（自動抓取若 DB 空） |
| GET | `/refresh` | 手動同步更新，完成後回首頁 |
| GET | `/cron/refresh` | 外部排程用，背景更新 |
| GET | `/health` | 健康檢查 |
| GET | `/favorites` | 我的最愛 |
| POST | `/favorite` | 收藏文章 |

---

## 專案結構

```
.
├── app.py                 # Flask 主程式、RSS 抓取、i18n
├── requirements.txt
├── runtime.txt            # Python 3.11.9（Render）
├── render.yaml            # Render Blueprint
├── templates/
│   ├── index.html         # 首頁
│   ├── favorites.html     # 收藏
│   └── refresh_done.html  # 更新完成（備用）
├── static/style.css
└── news.db                # SQLite（執行時建立，不進 git）
```

---

## RSS 來源

編輯 `app.py` 的 `RSS_SOURCES` 增減來源。目前含 BBC、Reuters、TechCrunch、TechNews、自由時報、ETtoday、聯合新聞網、BBC 中文、DW 中文等。
