# Git SSH 備忘（本專案）

請改看工作區通用文件：**[`SSH_GIT.md`](../../../SSH_GIT.md)**（`Documents\code\SSH_GIT.md`）。

## 本 repo

| 項目 | 值 |
|------|-----|
| 帳號 | **boson316** |
| Remote | `git@github-boson316:boson316/news.git` |
| GitHub | https://github.com/boson316/news |
| Render 線上 | https://boson-news-app.onrender.com |
| Cron 端點 | https://boson-news-app.onrender.com/cron/refresh |

## 部署流程（Push 後 Render 自動建置）

```powershell
cd "c:\Users\User\Documents\code\cursor\3_Web與API\新聞蒐集"
git add app.py templates/ static/ render.yaml README.md README.zh-TW.md
git commit -m "更新：中文介面、自動抓取、cron 端點"
git push origin main
```

建置完成後確認：

- https://boson-news-app.onrender.com/ → 首頁「新聞蒐集」
- https://boson-news-app.onrender.com/cron/refresh → `{"status":"started"}`
- https://boson-news-app.onrender.com/health → `{"status":"ok", ...}`

## cron-job.org

1. **+ 建立定時工作**
2. URL：`https://boson-news-app.onrender.com/cron/refresh`
3. 方法：GET
4. 排程：每 14 分鐘
