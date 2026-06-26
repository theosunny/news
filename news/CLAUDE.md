# 乳业情报平台 - 项目上下文

## 项目概述
面向乳业从业者和投资分析师的一站式行业情报平台（产品名：**乳源**）。
技术栈：Lovable.dev（React+Vite 前端）+ Supabase（数据库+Auth+RLS）+ GitHub Actions + Python Scrapling 爬虫 + Claude Haiku AI 摘要。

## 目录结构
```
E:\claudpro\news\
├── CLAUDE.md                          # 本文件
├── dairy-intel-crawler\               # Python 爬虫仓库（已有 git）
│   ├── crawler\                       # 爬虫模块（rss/scrapling/ai/writer）
│   ├── tests\                         # 单元测试（8 tests passing）
│   ├── .github\workflows\crawler.yml  # GitHub Actions 每小时定时任务
│   └── supabase-functions\README.md   # Edge Function 部署说明
└── supabase\
    ├── migrations\                    # SQL 文件（已在 Supabase 执行 01-05）
    │   ├── 01_extensions.sql          ✅ 已执行
    │   ├── 02_users.sql               ✅ 已执行
    │   ├── 03_tables.sql              ✅ 已执行
    │   ├── 04_seed.sql                ✅ 已执行
    │   ├── 05_rls.sql                 ✅ 已执行
    │   └── 06_pg_cron.sql             ⏳ 待执行（需先部署 Edge Function）
    └── functions\
        └── daily-digest\index.ts      # 每日速览 Edge Function（已写好，待部署）
```

## 关键设计决策
- AI 摘要使用 **Claude Haiku**（用户有中转站），环境变量：`ANTHROPIC_API_KEY` + `ANTHROPIC_BASE_URL`
- sources.py 中数据源用 `"method"` 字段（值：`"rss"` 或 `"scrapling"`），不是 `"type"`
- Supabase 写入用 `service_role key`（绕过 RLS），前端读取用 `anon key`
- 付费内容通过 RLS 隔离（`is_premium=true` 仅 `subscription_tier='pro'` 用户可读）
- 免费用户每日限 20 条资讯（前端 limit 参数控制）

## 参考文档
- 设计文档：`E:\claudpro\docs\superpowers\specs\2026-06-25-dairy-intel-platform-design.md`
- 实现计划：`E:\claudpro\docs\superpowers\plans\2026-06-25-dairy-intel-platform.md`
- SDD 进度台账：`E:\claudpro\news\dairy-intel-crawler\.superpowers\sdd\progress.md`

---

## TODO — 下次启动继续

### 🔴 TODO-1：完成 Lovable.dev 前端初始化（Task 3）

**状态**：用户已有 Supabase Project URL 和 anon key，但还未在 Lovable.dev 创建项目。

**操作步骤**：
1. 打开 https://lovable.dev → New Project
2. 把以下 Prompt 粘贴进去，**先把两个占位符替换成实际值**：
   - `[YOUR_SUPABASE_URL]` → Supabase Dashboard → Project Settings → Data API → Project URL
   - `[YOUR_ANON_KEY]` → 同页面 → Project API keys → anon public 那一行的值

**Lovable.dev 初始 Prompt：**
```
Build a dark-themed dairy industry intelligence dashboard called "乳源" (Ruyuan).

Layout: Full-width dark background (#0a0f1e), sticky top navigation bar with logo "乳源" on left and login button on right.

Main content: Single-page dashboard with 6 sections displayed as a responsive card grid:

1. 今日重点速览 (Daily Highlights) - Top banner, full width, shows 5-8 key news items as numbered list
2. 乳业资讯 (Dairy News) - Card grid, shows article cards with title, source, time, 2-line summary, and colored tags (政策=blue, 价格=green, 质量安全=red, 企业动态=orange, 技术=purple, 国际=gray)
3. 重点舆情 (Sentiment Monitor) - Cards with sentiment indicator bar (-1 to +1), negative items highlighted with red left border
4. 社交动态 (Social Feed) - Feed cards showing platform icon (微博/微信/雪球/东方财富/Twitter), author, content snippet, engagement count
5. 企业追踪 (Company Tracker) - Table with company name, ticker, price, change%, and latest news headline
6. 深度洞察 (Deep Insights) - Report cards with title, date, 3-line preview, "阅读全文" button

Color scheme: Dark navy background, electric blue (#3b82f6) accents, white text, subtle card borders (#1e293b).
Typography: System font stack, Chinese-first.

All sections show skeleton loading states when data is empty. Add a premium paywall blur overlay on sections 5 (international companies) and 6 (full reports) with an upgrade button.

Connect to Supabase:
- URL: [YOUR_SUPABASE_URL]
- Anon Key: [YOUR_ANON_KEY]

Fetch data from these tables: articles, company_updates, social_posts, daily_digest
```

**完成后**：告诉 Claude，继续执行 Task 4（手机号登录 Prompt）。

---

### 🔴 TODO-2：推送爬虫到 GitHub 并配置 Secrets（Task 7）

**状态**：爬虫代码已在本地 `E:\claudpro\news\dairy-intel-crawler\` 完成，需要推送到 GitHub 仓库并配置 Secrets 才能自动运行。

**操作步骤**：
1. 在 GitHub 新建仓库 `dairy-intel-crawler`（Private）
2. 推送本地代码：
   ```powershell
   cd E:\claudpro\news\dairy-intel-crawler
   git remote add origin https://github.com/YOUR_USERNAME/dairy-intel-crawler.git
   git push -u origin master
   ```
3. 在 GitHub 仓库 → Settings → Secrets and variables → Actions，添加以下 4 个 Secret：
   - `SUPABASE_URL` — Supabase Project URL
   - `SUPABASE_SERVICE_KEY` — Supabase service_role key（Settings → Data API → service_role，不是 anon）
   - `ANTHROPIC_API_KEY` — Claude API Key
   - `ANTHROPIC_BASE_URL` — 中转站地址（如有，否则留 https://api.anthropic.com）
4. 推送后在 GitHub → Actions → "Dairy Intel Crawler" → Run workflow 手动触发一次验证

**完成后**：告诉 Claude，继续执行 Task 8 Edge Function 部署（`supabase functions deploy daily-digest`）。

---

## 后续待做（需商户账号）
- Task 9：微信支付 + 支付宝集成（需要微信支付商户号 + 支付宝商户 PID）
- Task 10：Lovable.dev 前端数据对接（需 Task 3 完成后进行）
- 06_pg_cron.sql：需要 Edge Function 部署后再执行
