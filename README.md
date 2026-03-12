# 國際・美國新聞蒐集網站（Flask）

這是一個使用 Python + Flask + SQLite 打造的簡單新聞蒐集網站，會從多個公開的國際／美國／中文新聞 RSS 來源抓取新聞。可**在本機執行**，也可**部署到雲端**，用瀏覽器開網址就能看，不必再打 `python app.py`。

> 僅供個人學習與研究使用，請勿用於商業用途。

---

## 方式一：直接在網路上看（部署到雲端，不用開 CMD）

把網站放到免費雲端後，你會得到一個網址（例如 `https://xxx.onrender.com`），用瀏覽器打開即可，**不需要在本機執行任何指令**。

### 推薦：Render（免費）

1. **把專案放上 GitHub**
   - 在 GitHub 開一個新 repo（例如 `news-aggregator`）
   - 只把「新聞蒐集」**資料夾裡的內容**（`app.py`、`requirements.txt`、`templates/`、`static/`、`render.yaml`、`runtime.txt`）上傳到該 repo 的**根目錄**（不要多一層「新聞蒐集」資料夾，否則 Render 會找不到 `app.py`）

2. **到 Render 部署**
   - 打開 [render.com](https://render.com)，用 GitHub 登入
   - 點 **New → Web Service**，選你剛建立的 repo
   - **Build command**：`pip install -r requirements.txt`
   - **Start command**：`gunicorn app:app --bind 0.0.0.0:$PORT`
   - 按 **Create Web Service**，等幾分鐘建置完成

3. **取得網址**
   - 完成後會給你一個網址，例如 `https://news-aggregator-xxxx.onrender.com`
   - 用瀏覽器打開即可。**第一次請點「手動更新新聞」**，等幾秒再回首頁，就會有新聞。

**注意**：Render 免費方案在沒人使用一段時間會休眠，第一次打開可能較慢；重新載入或再點一次連結即可。

---

## 方式二：在本機執行（需要 CMD）

### 環境需求

- Python 3.10 以上
- pip

### 安裝與啟動

在「新聞蒐集」資料夾開啟終端機：

```bash
pip install -r requirements.txt
python app.py
```

瀏覽器打開 `http://127.0.0.1:5000`。若想從別台電腦連，可改用 `http://你的IP:5000`（已設定 `host="0.0.0.0"`）。

---

## 使用方式（首頁）

- **選擇區塊**：國際新聞、科技新聞、財經新聞、大型科技公司追蹤、中文新聞
- **時間範圍**：今天／一週／一個月／一季／半年／全部
- **手動更新新聞**：從各 RSS 來源重新抓取最新新聞（建議首次開啟或久久沒更新時點一次）

---

## RSS 來源（可自行調整）

編輯 `app.py` 裡的 `RSS_SOURCES` 即可增減來源。目前包含 BBC、Reuters、TechCrunch、自由時報、ETtoday、聯合新聞網、BBC 中文、DW 中文等。

