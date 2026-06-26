# 乳业情报平台实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Lovable.dev + Supabase + GitHub Actions 构建乳业行业情报平台，支持自动抓取、AI摘要、免费/付费分层、手机号/微信登录。

**Architecture:** Lovable.dev 生成 React+Vite 前端连接 Supabase（数据库+Auth+Edge Functions+RLS），GitHub Actions 每小时运行 Python Scrapling 爬虫抓取乳业内容写入 Supabase，Supabase Edge Functions 处理 AI 摘要生成和支付回调。

**Tech Stack:** React + Vite (Lovable.dev), Supabase (PostgreSQL + Auth + Edge Functions), Python 3.11 + Scrapling + feedparser (爬虫), OpenAI GPT-4o (AI摘要), 微信支付 + 支付宝 (付费), GitHub Actions (定时任务)

## Global Constraints

- Supabase 项目区域选 ap-east-1（香港），降低国内延迟
- Python 爬虫最低版本 3.11
- 所有写入 Supabase 的请求使用 service_role key（绕过 RLS），读取使用 anon key（受 RLS 约束）
- is_premium=true 的内容只有 subscription_tier='pro' 用户可读（RLS 强制）
- 免费用户每日资讯限 20 条，通过前端查询参数 limit 控制
- AI 调用使用 OpenAI GPT-4o-mini（成本低），洞察报告用 GPT-4o
- 所有密钥存储在 GitHub Actions Secrets 和 Supabase Edge Function 环境变量，不硬编码

---

## 文件结构

```
dairy-intel/                          # 爬虫 + 配置仓库（GitHub）
├── .github/
│   └── workflows/
│       └── crawler.yml               # 每小时定时抓取
├── crawler/
│   ├── main.py                       # 入口，协调所有爬虫
│   ├── rss_fetcher.py                # RSS/Atom 解析
│   ├── scrapling_fetcher.py          # Scrapling 复杂页面抓取
│   ├── social_fetcher.py             # 社交媒体抓取
│   ├── company_fetcher.py            # 企业动态 + 行情
│   ├── ai_summarizer.py              # OpenAI 摘要 + 标签 + 情感
│   ├── supabase_writer.py            # 写入 Supabase
│   └── sources.py                    # 数据源配置（URL、方法、分类）
├── requirements.txt
└── tests/
    ├── test_rss_fetcher.py
    ├── test_ai_summarizer.py
    └── test_supabase_writer.py

supabase/                             # Supabase Edge Functions
└── functions/
    ├── daily-digest/
    │   └── index.ts                  # 每日凌晨生成今日速览
    ├── payment-wechat/
    │   └── index.ts                  # 微信支付回调
    └── payment-alipay/
        └── index.ts                  # 支付宝回调

# Lovable.dev 生成的前端代码由平台托管，无需本地文件结构
```

---

## Task 1: Supabase 项目初始化 + 数据库 Schema

**Files:**
- Create: `supabase/migrations/20260625_init.sql`

**Interfaces:**
- Produces: 所有后续任务依赖的 8 张表，RLS 策略，pg_cron 扩展

- [ ] **Step 1: 创建 Supabase 项目**

访问 https://supabase.com/dashboard → New Project
- Name: dairy-intel
- Region: Northeast Asia (Tokyo) 或 Southeast Asia（选延迟最低的）
- Password: 生成强密码并保存

- [ ] **Step 2: 开启必要扩展**

在 Supabase Dashboard → SQL Editor 运行：

```sql
-- 开启 pg_cron（定时任务）和 pg_net（HTTP请求）
create extension if not exists pg_cron;
create extension if not exists pg_net;
create extension if not exists "uuid-ossp";
```

- [ ] **Step 3: 创建用户扩展表**

```sql
-- Supabase Auth 已有 auth.users，这里创建 public.users 存业务字段
create table public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  phone text unique,
  wechat_openid text unique,
  subscription_tier text not null default 'free' check (subscription_tier in ('free', 'pro')),
  subscription_expires_at timestamptz,
  created_at timestamptz not null default now()
);

-- 新用户注册时自动插入 public.users
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.users (id, phone)
  values (new.id, new.phone);
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
```

- [ ] **Step 4: 创建内容表**

```sql
create table public.articles (
  id uuid primary key default uuid_generate_v4(),
  title text not null,
  summary text,
  content text,
  source_url text unique,
  source_name text,
  category text not null check (category in ('news','sentiment','social','company','insight')),
  tags text[] default '{}',
  sentiment_score float check (sentiment_score >= -1.0 and sentiment_score <= 1.0),
  is_premium boolean not null default false,
  published_at timestamptz,
  created_at timestamptz not null default now()
);

create index articles_category_published_idx on public.articles(category, published_at desc);
create index articles_is_premium_idx on public.articles(is_premium);
```

- [ ] **Step 5: 创建企业、社交、速览、数据源、订阅表**

```sql
create table public.companies (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  exchange text,
  ticker text,
  country text,
  is_active boolean not null default true
);

-- 插入初始企业数据
insert into public.companies (name, exchange, ticker, country) values
  ('伊利股份', 'SSE', '600887', 'CN'),
  ('蒙牛乳业', 'HKEX', '02319', 'CN'),
  ('光明乳业', 'SSE', '600597', 'CN'),
  ('新乳业', 'SZE', '002946', 'CN'),
  ('澳亚集团', 'HKEX', '06963', 'CN'),
  ('Fonterra', 'NZX', 'FCG', 'NZ'),
  ('Bega Cheese', 'ASX', 'BGA', 'AU');

create table public.company_updates (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid not null references public.companies(id),
  title text not null,
  summary text,
  price_data jsonb,
  is_premium boolean not null default false,
  published_at timestamptz not null default now()
);

create table public.social_posts (
  id uuid primary key default uuid_generate_v4(),
  platform text not null check (platform in ('weibo','wechat','xueqiu','eastmoney','twitter')),
  content text not null,
  author text,
  engagement_count int default 0,
  url text unique,
  created_at timestamptz not null default now()
);

create table public.daily_digest (
  id uuid primary key default uuid_generate_v4(),
  date date not null unique,
  highlights jsonb not null default '[]',
  created_at timestamptz not null default now()
);

create table public.rss_sources (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  url text not null,
  category text not null,
  scraping_method text not null default 'rss' check (scraping_method in ('rss','scrapling')),
  is_active boolean not null default true,
  last_fetched_at timestamptz
);

-- 插入初始数据源
insert into public.rss_sources (name, url, category, scraping_method) values
  ('Dairy Reporter', 'https://www.dairyreporter.com/rss/news', 'news', 'rss'),
  ('USDA Dairy', 'https://www.ams.usda.gov/rss/mncs/dairy.xml', 'news', 'rss'),
  ('Fonterra News', 'https://www.fonterra.com/nz/en/news-and-media/news.rss.xml', 'news', 'rss'),
  ('农业农村部', 'http://www.moa.gov.cn/rssfeed/rss.xml', 'news', 'scrapling'),
  ('国家奶牛技术体系', 'http://www.chinacows.org', 'news', 'scrapling'),
  ('雪球乳业', 'https://xueqiu.com/search?q=乳业', 'social', 'scrapling'),
  ('东方财富乳业', 'https://search.eastmoney.com/快讯?keyword=乳业', 'social', 'scrapling'),
  ('GDT拍卖', 'https://www.globaldairytrade.info/en/product-results/', 'company', 'scrapling');

create table public.subscriptions (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.users(id),
  plan text not null check (plan in ('monthly','yearly')),
  amount int not null,
  payment_method text not null check (payment_method in ('wechat','alipay')),
  status text not null default 'pending' check (status in ('pending','active','expired','cancelled')),
  out_trade_no text unique,
  started_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz not null default now()
);
```

- [ ] **Step 6: 验证表创建成功**

在 Supabase Dashboard → Table Editor，确认以下 8 张表存在：
`users, articles, companies, company_updates, social_posts, daily_digest, rss_sources, subscriptions`

---

## Task 2: RLS 权限策略

**Files:**
- Create: `supabase/migrations/20260625_rls.sql`

**Interfaces:**
- Consumes: Task 1 创建的所有表
- Produces: 数据库级付费内容隔离，anon key 查询自动过滤 is_premium 内容

- [ ] **Step 1: 开启 RLS 并配置 articles 表策略**

```sql
alter table public.users enable row level security;
alter table public.articles enable row level security;
alter table public.company_updates enable row level security;
alter table public.social_posts enable row level security;
alter table public.daily_digest enable row level security;
alter table public.subscriptions enable row level security;

-- articles: 免费内容所有人可读；付费内容仅 pro 用户可读
create policy "free articles are public" on public.articles
  for select using (is_premium = false);

create policy "premium articles for pro users" on public.articles
  for select using (
    is_premium = true
    and exists (
      select 1 from public.users
      where id = auth.uid()
      and subscription_tier = 'pro'
      and (subscription_expires_at is null or subscription_expires_at > now())
    )
  );
```

- [ ] **Step 2: 配置其余表策略**

```sql
-- company_updates: 同 articles 逻辑
create policy "free company updates are public" on public.company_updates
  for select using (is_premium = false);

create policy "premium company updates for pro users" on public.company_updates
  for select using (
    is_premium = true
    and exists (
      select 1 from public.users
      where id = auth.uid()
      and subscription_tier = 'pro'
      and (subscription_expires_at is null or subscription_expires_at > now())
    )
  );

-- social_posts: 全部公开
create policy "social posts are public" on public.social_posts
  for select using (true);

-- daily_digest: 全部公开（前端按 is_premium 字段决定是否模糊显示）
create policy "daily digest is public" on public.daily_digest
  for select using (true);

-- users: 只能读写自己的记录
create policy "users can read own profile" on public.users
  for select using (auth.uid() = id);

create policy "users can update own profile" on public.users
  for update using (auth.uid() = id);

-- subscriptions: 只能读自己的订阅
create policy "users can read own subscriptions" on public.subscriptions
  for select using (auth.uid() = user_id);
```

- [ ] **Step 3: 验证 RLS 生效**

在 SQL Editor 中，用 anon 角色测试（模拟未登录用户）：

```sql
-- 设置为 anon 角色
set role anon;

-- 应该只返回 is_premium=false 的文章
select count(*) from public.articles where is_premium = true;
-- 预期结果: 0 rows（RLS 阻止访问）

reset role;
```

---

## Task 3: Lovable.dev 前端初始化

**Interfaces:**
- Consumes: Supabase 项目 URL 和 anon key（Task 1 完成后获取）
- Produces: 可访问的 React 前端，包含整体布局、六大模块占位、Supabase 连接

- [ ] **Step 1: 获取 Supabase 连接信息**

Supabase Dashboard → Settings → API：
- 复制 `Project URL`（格式：`https://xxxx.supabase.co`）
- 复制 `anon public` key

- [ ] **Step 2: 在 Lovable.dev 创建项目并发送初始 Prompt**

访问 https://lovable.dev → New Project，发送以下 Prompt：

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

- [ ] **Step 3: 替换 Prompt 中的占位符**

将 `[YOUR_SUPABASE_URL]` 和 `[YOUR_ANON_KEY]` 替换为 Step 1 获取的实际值后再发送。

- [ ] **Step 4: 验证前端基础结构**

Lovable.dev 生成后，点击 Preview：
- 确认 6 个区块都存在
- 确认暗色主题正确
- 确认骨架屏在数据为空时显示
- 确认付费遮罩出现在企业追踪（国际部分）和深度洞察

---

## Task 4: 手机号登录

**Interfaces:**
- Consumes: Supabase Auth（Task 1），Lovable.dev 前端（Task 3）
- Produces: 用户可用手机号+验证码注册/登录，登录状态持久化

- [ ] **Step 1: 配置 Supabase 短信提供商**

Supabase Dashboard → Authentication → Providers → Phone：
- 开启 Phone provider
- SMS provider 选 Twilio（国际）或 Aliyun（国内，需自定义）
- 对于阿里云短信：选 Twilio，填入阿里云短信 Access Key 和模板（格式兼容）

> 如果暂时无短信账号，开启 Phone provider 后在 Dashboard → Authentication → Settings 开启 "Enable phone confirmations" 关闭，改为直接发 OTP（测试阶段 Supabase 提供免费 OTP，勿用于生产）

- [ ] **Step 2: 在 Lovable.dev 添加登录页 Prompt**

在 Lovable.dev 发送：

```
Add a login modal that appears when clicking the login button in the nav.

The modal has two tabs:
Tab 1 "手机登录":
- Phone number input field (Chinese format, prefix +86)
- "获取验证码" button that calls Supabase signInWithOtp({ phone: '+86' + phoneNumber })
- 6-digit OTP input that appears after sending
- "登录" button that calls Supabase verifyOtp({ phone, token, type: 'sms' })
- Show countdown timer 60s on the send button after clicking

Tab 2 "微信登录":
- Large WeChat green button with WeChat logo
- Button text: "微信扫码登录"
- For now show a placeholder "即将开放" toast when clicked

After successful login, close the modal and show user's phone number in the nav bar where login button was, with a logout option in dropdown.

Use Supabase client already configured in the project.
```

- [ ] **Step 3: 验证登录流程**

在 Preview 中：
1. 点击登录 → 模态框出现
2. 输入手机号 → 点击获取验证码（Supabase 发送 OTP）
3. 输入收到的 OTP → 点击登录
4. 确认导航栏显示手机号，模态框关闭

---

## Task 5: 爬虫基础设施

**Files:**
- Create: `crawler/requirements.txt`
- Create: `crawler/sources.py`
- Create: `crawler/supabase_writer.py`
- Create: `tests/test_supabase_writer.py`

**Interfaces:**
- Produces: `write_articles(articles: list[dict]) -> int`，`write_social_posts(posts: list[dict]) -> int`，`write_company_updates(updates: list[dict]) -> int`

- [ ] **Step 1: 创建仓库并初始化**

在 GitHub 创建新仓库 `dairy-intel-crawler`（Private），克隆到本地：

```bash
git clone https://github.com/YOUR_USERNAME/dairy-intel-crawler.git
cd dairy-intel-crawler
mkdir -p crawler tests .github/workflows
```

- [ ] **Step 2: 创建 requirements.txt**

```
scrapling==0.2.9
feedparser==6.0.11
openai==1.35.0
supabase==2.5.0
python-dotenv==1.0.1
pytest==8.2.2
pytest-asyncio==0.23.7
httpx==0.27.0
```

- [ ] **Step 3: 创建 crawler/sources.py**

```python
SOURCES = [
    # RSS 源
    {
        "name": "Dairy Reporter",
        "url": "https://www.dairyreporter.com/rss/news",
        "category": "news",
        "method": "rss",
        "language": "en",
    },
    {
        "name": "USDA Dairy",
        "url": "https://www.ams.usda.gov/rss/mncs/dairy.xml",
        "category": "news",
        "method": "rss",
        "language": "en",
    },
    {
        "name": "Fonterra News",
        "url": "https://www.fonterra.com/nz/en/news-and-media/news.rss.xml",
        "category": "news",
        "method": "rss",
        "language": "en",
    },
    # Scrapling 源
    {
        "name": "农业农村部",
        "url": "http://www.moa.gov.cn/govpublic/",
        "category": "news",
        "method": "scrapling",
        "language": "zh",
        "selector": "div.main-list li a",
    },
    {
        "name": "GDT拍卖",
        "url": "https://www.globaldairytrade.info/en/product-results/",
        "category": "company",
        "method": "scrapling",
        "language": "en",
        "selector": "table.results-table tr",
    },
]

SOCIAL_SOURCES = [
    {
        "platform": "xueqiu",
        "url": "https://xueqiu.com/search?q=乳业&type=status",
        "method": "scrapling",
        "selector": "div.timeline-item",
    },
    {
        "platform": "eastmoney",
        "url": "https://search.eastmoney.com/快讯?keyword=乳业",
        "method": "scrapling",
        "selector": "div.news-item",
    },
]

COMPANY_SOURCES = [
    {"name": "伊利股份", "ticker": "600887", "exchange": "SSE", "is_premium": False},
    {"name": "蒙牛乳业", "ticker": "02319", "exchange": "HKEX", "is_premium": False},
    {"name": "光明乳业", "ticker": "600597", "exchange": "SSE", "is_premium": False},
    {"name": "新乳业",   "ticker": "002946", "exchange": "SZE", "is_premium": False},
    {"name": "Fonterra", "ticker": "FCG",    "exchange": "NZX", "is_premium": True},
    {"name": "Bega Cheese", "ticker": "BGA", "exchange": "ASX", "is_premium": True},
]
```

- [ ] **Step 4: 创建 crawler/supabase_writer.py**

```python
import os
from supabase import create_client, Client

def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]  # service_role key，绕过 RLS
    return create_client(url, key)

def write_articles(articles: list[dict]) -> int:
    """写入文章，source_url 唯一冲突时跳过。返回实际插入数量。"""
    if not articles:
        return 0
    client = get_client()
    result = client.table("articles").upsert(
        articles,
        on_conflict="source_url",
        ignore_duplicates=True,
    ).execute()
    return len(result.data)

def write_social_posts(posts: list[dict]) -> int:
    """写入社交动态，url 唯一冲突时跳过。"""
    if not posts:
        return 0
    client = get_client()
    result = client.table("social_posts").upsert(
        posts,
        on_conflict="url",
        ignore_duplicates=True,
    ).execute()
    return len(result.data)

def write_company_updates(updates: list[dict]) -> int:
    """写入企业动态。"""
    if not updates:
        return 0
    client = get_client()
    result = client.table("company_updates").insert(updates).execute()
    return len(result.data)
```

- [ ] **Step 5: 编写测试 tests/test_supabase_writer.py**

```python
import pytest
from unittest.mock import patch, MagicMock
from crawler.supabase_writer import write_articles, write_social_posts

@patch("crawler.supabase_writer.get_client")
def test_write_articles_empty(mock_client):
    result = write_articles([])
    assert result == 0
    mock_client.assert_not_called()

@patch("crawler.supabase_writer.get_client")
def test_write_articles_returns_count(mock_client):
    mock_table = MagicMock()
    mock_table.table.return_value.upsert.return_value.execute.return_value.data = [
        {"id": "1"}, {"id": "2"}
    ]
    mock_client.return_value = mock_table
    articles = [
        {"title": "Test", "source_url": "https://example.com/1", "category": "news"},
        {"title": "Test2", "source_url": "https://example.com/2", "category": "news"},
    ]
    result = write_articles(articles)
    assert result == 2

@patch("crawler.supabase_writer.get_client")
def test_write_social_posts_empty(mock_client):
    result = write_social_posts([])
    assert result == 0
    mock_client.assert_not_called()
```

- [ ] **Step 6: 运行测试验证**

```bash
cd dairy-intel-crawler
pip install -r requirements.txt
SUPABASE_URL=fake SUPABASE_SERVICE_KEY=fake pytest tests/test_supabase_writer.py -v
```

预期输出：
```
test_supabase_writer.py::test_write_articles_empty PASSED
test_supabase_writer.py::test_write_articles_returns_count PASSED
test_supabase_writer.py::test_write_social_posts_empty PASSED
3 passed
```

- [ ] **Step 7: 提交**

```bash
git add crawler/requirements.txt crawler/sources.py crawler/supabase_writer.py tests/test_supabase_writer.py
git commit -m "feat: crawler infrastructure - sources config and supabase writer"
```

---

## Task 6: RSS + Scrapling 爬虫

**Files:**
- Create: `crawler/rss_fetcher.py`
- Create: `crawler/scrapling_fetcher.py`
- Create: `crawler/ai_summarizer.py`
- Create: `crawler/main.py`
- Create: `tests/test_rss_fetcher.py`
- Create: `tests/test_ai_summarizer.py`

**Interfaces:**
- Consumes: `sources.py` 中的 SOURCES 配置
- Produces: `fetch_rss(source: dict) -> list[dict]`，`fetch_scrapling(source: dict) -> list[dict]`，`summarize_article(title: str, content: str, language: str) -> dict`

- [ ] **Step 1: 创建 crawler/rss_fetcher.py**

```python
import feedparser
from datetime import datetime, timezone

def fetch_rss(source: dict) -> list[dict]:
    """
    解析 RSS 源，返回标准化文章列表。
    每篇文章格式: {title, content, source_url, source_name, category, language, published_at}
    """
    try:
        feed = feedparser.parse(source["url"])
    except Exception as e:
        print(f"[rss_fetcher] Failed to fetch {source['url']}: {e}")
        return []

    articles = []
    for entry in feed.entries[:20]:  # 每次最多取 20 条
        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()

        content = ""
        if hasattr(entry, "summary"):
            content = entry.summary
        elif hasattr(entry, "content"):
            content = entry.content[0].value if entry.content else ""

        articles.append({
            "title": entry.get("title", ""),
            "content": content[:2000],  # 截断避免超长
            "source_url": entry.get("link", ""),
            "source_name": source["name"],
            "category": source["category"],
            "language": source.get("language", "en"),
            "published_at": published_at,
            "is_premium": False,
            "tags": [],
        })

    return [a for a in articles if a["title"] and a["source_url"]]
```

- [ ] **Step 2: 创建 crawler/scrapling_fetcher.py**

```python
from scrapling import Fetcher
from datetime import datetime, timezone

def fetch_scrapling(source: dict) -> list[dict]:
    """
    用 Scrapling 抓取无 RSS 的网页，返回标准化文章列表。
    """
    try:
        fetcher = Fetcher(auto_match=True)
        page = fetcher.get(source["url"])
    except Exception as e:
        print(f"[scrapling_fetcher] Failed to fetch {source['url']}: {e}")
        return []

    articles = []
    selector = source.get("selector", "a")

    try:
        elements = page.css(selector)
    except Exception:
        return []

    for el in elements[:15]:
        title = el.text.strip() if el.text else ""
        link = el.attrib.get("href", "")

        if not title or not link:
            continue

        if link.startswith("/"):
            from urllib.parse import urlparse
            base = urlparse(source["url"])
            link = f"{base.scheme}://{base.netloc}{link}"

        articles.append({
            "title": title,
            "content": "",  # Scrapling 需要二次请求获取正文，AI 摘要阶段补充
            "source_url": link,
            "source_name": source["name"],
            "category": source["category"],
            "language": source.get("language", "zh"),
            "published_at": datetime.now(timezone.utc).isoformat(),
            "is_premium": False,
            "tags": [],
        })

    return articles
```

- [ ] **Step 3: 创建 crawler/ai_summarizer.py**

```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SUMMARIZE_PROMPT = """你是乳业行业分析师。请对以下文章生成：
1. 中文摘要（2-3句，聚焦关键信息）
2. 情感得分（-1.0到1.0，负面事件接近-1，正面接近1，中性接近0）
3. 标签（从以下选1-3个：政策、价格、质量安全、企业动态、技术、国际）

返回 JSON 格式：{"summary": "...", "sentiment_score": 0.0, "tags": ["..."]}

标题：{title}
内容：{content}
"""

def summarize_article(title: str, content: str, language: str = "zh") -> dict:
    """
    调用 GPT-4o-mini 生成摘要、情感得分、标签。
    返回 {"summary": str, "sentiment_score": float, "tags": list[str]}
    """
    if not title:
        return {"summary": "", "sentiment_score": 0.0, "tags": []}

    input_content = content[:1000] if content else "（无正文）"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": SUMMARIZE_PROMPT.format(title=title, content=input_content)
            }],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=300,
        )
        import json
        result = json.loads(response.choices[0].message.content)
        return {
            "summary": result.get("summary", ""),
            "sentiment_score": float(result.get("sentiment_score", 0.0)),
            "tags": result.get("tags", []),
        }
    except Exception as e:
        print(f"[ai_summarizer] Failed to summarize '{title}': {e}")
        return {"summary": "", "sentiment_score": 0.0, "tags": []}
```

- [ ] **Step 4: 创建 crawler/main.py**

```python
import sys
from crawler.sources import SOURCES
from crawler.rss_fetcher import fetch_rss
from crawler.scrapling_fetcher import fetch_scrapling
from crawler.ai_summarizer import summarize_article
from crawler.supabase_writer import write_articles

def run():
    all_articles = []

    for source in SOURCES:
        print(f"[main] Fetching: {source['name']}")
        if source["method"] == "rss":
            raw = fetch_rss(source)
        else:
            raw = fetch_scrapling(source)

        for article in raw:
            ai_result = summarize_article(
                article["title"],
                article["content"],
                article.get("language", "zh")
            )
            article.update(ai_result)
            all_articles.append(article)
        
        print(f"[main] Got {len(raw)} articles from {source['name']}")

    inserted = write_articles(all_articles)
    print(f"[main] Done. Inserted {inserted} new articles.")

if __name__ == "__main__":
    run()
```

- [ ] **Step 5: 编写测试**

```python
# tests/test_rss_fetcher.py
from unittest.mock import patch, MagicMock
from crawler.rss_fetcher import fetch_rss

@patch("crawler.rss_fetcher.feedparser.parse")
def test_fetch_rss_returns_articles(mock_parse):
    mock_entry = MagicMock()
    mock_entry.title = "奶价上涨3%"
    mock_entry.link = "https://dairyreporter.com/news/1"
    mock_entry.summary = "全球原奶价格本周上涨3%..."
    mock_entry.published_parsed = (2026, 6, 25, 0, 0, 0, 0, 0, 0)
    mock_parse.return_value = MagicMock(entries=[mock_entry])

    source = {"name": "Test", "url": "https://fake.com/rss", "category": "news", "language": "en"}
    articles = fetch_rss(source)

    assert len(articles) == 1
    assert articles[0]["title"] == "奶价上涨3%"
    assert articles[0]["category"] == "news"
    assert articles[0]["source_url"] == "https://dairyreporter.com/news/1"

@patch("crawler.rss_fetcher.feedparser.parse")
def test_fetch_rss_skips_empty_entries(mock_parse):
    mock_entry = MagicMock()
    mock_entry.title = ""
    mock_entry.link = ""
    mock_parse.return_value = MagicMock(entries=[mock_entry])

    source = {"name": "Test", "url": "https://fake.com/rss", "category": "news", "language": "en"}
    articles = fetch_rss(source)
    assert len(articles) == 0
```

```python
# tests/test_ai_summarizer.py
from unittest.mock import patch, MagicMock
from crawler.ai_summarizer import summarize_article

@patch("crawler.ai_summarizer.client")
def test_summarize_article_returns_dict(mock_openai):
    import json
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "summary": "蒙牛发布新品",
        "sentiment_score": 0.5,
        "tags": ["企业动态"]
    })
    mock_openai.chat.completions.create.return_value = mock_response

    result = summarize_article("蒙牛发布新产品", "蒙牛乳业今日发布...")
    assert result["summary"] == "蒙牛发布新品"
    assert result["sentiment_score"] == 0.5
    assert "企业动态" in result["tags"]

def test_summarize_empty_title():
    result = summarize_article("", "")
    assert result == {"summary": "", "sentiment_score": 0.0, "tags": []}
```

- [ ] **Step 6: 运行测试**

```bash
pytest tests/test_rss_fetcher.py tests/test_ai_summarizer.py -v
```

预期：5 tests passed

- [ ] **Step 7: 提交**

```bash
git add crawler/ tests/
git commit -m "feat: rss/scrapling fetcher and ai summarizer"
```

---

## Task 7: GitHub Actions 定时任务

**Files:**
- Create: `.github/workflows/crawler.yml`

**Interfaces:**
- Consumes: Task 5-6 的爬虫代码
- Produces: 每小时自动运行，结果写入 Supabase

- [ ] **Step 1: 配置 GitHub Secrets**

在 GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret：
- `SUPABASE_URL`：你的 Supabase Project URL
- `SUPABASE_SERVICE_KEY`：Supabase service_role key（Dashboard → Settings → API → service_role）
- `OPENAI_API_KEY`：你的 OpenAI API Key

- [ ] **Step 2: 创建 .github/workflows/crawler.yml**

```yaml
name: Dairy Intel Crawler

on:
  schedule:
    - cron: '0 * * * *'  # 每小时整点运行
  workflow_dispatch:      # 允许手动触发

jobs:
  crawl:
    runs-on: ubuntu-latest
    timeout-minutes: 20

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install Playwright (Scrapling dependency)
        run: playwright install chromium --with-deps

      - name: Run crawler
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: python -m crawler.main

      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: crawler-logs
          path: '*.log'
          retention-days: 3
```

- [ ] **Step 3: 手动触发验证**

推送代码后，在 GitHub → Actions → "Dairy Intel Crawler" → Run workflow，手动触发。
等待运行完成（约 3-5 分钟），查看 Logs 确认无报错，且输出包含：
```
[main] Done. Inserted N new articles.
```

- [ ] **Step 4: 在 Supabase 确认数据写入**

Dashboard → Table Editor → articles，确认有新行插入，`summary` 和 `tags` 字段有 AI 生成的内容。

- [ ] **Step 5: 提交**

```bash
git add .github/workflows/crawler.yml
git commit -m "feat: github actions hourly crawler workflow"
```

---

## Task 8: Supabase Edge Function - 每日速览生成

**Files:**
- Create: `supabase/functions/daily-digest/index.ts`

**Interfaces:**
- Consumes: `articles` 表中当天数据
- Produces: `daily_digest` 表写入当天 highlights

- [ ] **Step 1: 安装 Supabase CLI**

```bash
npm install -g supabase
supabase login
supabase link --project-ref YOUR_PROJECT_REF  # 从 Dashboard URL 获取
```

- [ ] **Step 2: 创建 supabase/functions/daily-digest/index.ts**

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
);

serve(async (_req) => {
  const today = new Date().toISOString().split("T")[0];

  // 检查今天是否已生成
  const { data: existing } = await supabase
    .from("daily_digest")
    .select("id")
    .eq("date", today)
    .single();

  if (existing) {
    return new Response(JSON.stringify({ message: "Already generated today" }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // 获取今日所有文章
  const since = new Date();
  since.setHours(0, 0, 0, 0);

  const { data: articles } = await supabase
    .from("articles")
    .select("title, summary, category, tags, sentiment_score, is_premium")
    .gte("created_at", since.toISOString())
    .order("created_at", { ascending: false })
    .limit(50);

  if (!articles || articles.length === 0) {
    return new Response(JSON.stringify({ message: "No articles today" }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // 调用 OpenAI 生成今日速览
  const articlesText = articles
    .map((a, i) => `${i + 1}. [${a.category}] ${a.title}: ${a.summary}`)
    .join("\n");

  const openaiRes = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${Deno.env.get("OPENAI_API_KEY")}`,
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: [{
        role: "user",
        content: `你是乳业分析师。从以下今日文章中选出5-8条最重要的动态，生成今日速览。
每条格式：{"title": "一句话标题", "summary": "一句话摘要", "is_premium": false}
重大行情、政策、安全事件标 is_premium: false，深度分析标 is_premium: true。
返回 JSON 数组。

今日文章：
${articlesText}`,
      }],
      response_format: { type: "json_object" },
      max_tokens: 1000,
    }),
  });

  const openaiData = await openaiRes.json();
  const content = JSON.parse(openaiData.choices[0].message.content);
  const highlights = Array.isArray(content) ? content : content.highlights || [];

  // 写入 daily_digest
  await supabase.from("daily_digest").insert({
    date: today,
    highlights,
  });

  return new Response(JSON.stringify({ message: "Generated", count: highlights.length }), {
    headers: { "Content-Type": "application/json" },
  });
});
```

- [ ] **Step 3: 部署 Edge Function**

```bash
supabase functions deploy daily-digest --no-verify-jwt
```

设置环境变量：
```bash
supabase secrets set OPENAI_API_KEY=your_openai_key
```

- [ ] **Step 4: 配置 pg_cron 每日凌晨 6 点触发**

在 Supabase SQL Editor 运行：

```sql
select cron.schedule(
  'daily-digest-job',
  '0 22 * * *',  -- UTC 22:00 = 北京时间 06:00
  $$
  select net.http_post(
    url := 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-digest',
    headers := '{"Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb
  )
  $$
);
```

将 `YOUR_PROJECT_REF` 和 `YOUR_ANON_KEY` 替换为实际值。

- [ ] **Step 5: 手动调用验证**

```bash
curl -X POST https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-digest \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

预期响应：`{"message":"Generated","count":6}`

然后在 Dashboard → Table Editor → daily_digest 确认今日记录已写入。

---

## Task 9: 微信支付 + 支付宝付费墙

**Files:**
- Create: `supabase/functions/payment-wechat/index.ts`
- Create: `supabase/functions/payment-alipay/index.ts`

**Interfaces:**
- Produces: POST `/functions/v1/payment-wechat` 创建支付订单，POST `/functions/v1/payment-wechat/notify` 处理回调更新订阅状态

> **前置条件**：需要微信支付商户号（mchid）、API v3 密钥、支付宝商户 PID 和 RSA 私钥。以下代码提供完整框架，密钥填入 Supabase Secrets。

- [ ] **Step 1: 在 Lovable.dev 添加付费页面 Prompt**

```
Add a subscription/upgrade page accessible via clicking any premium blur overlay or nav "升级" button.

Show two pricing cards side by side:
- Monthly: ¥39/月, features list: 全部乳业资讯, 国际企业追踪, GDT行情, 深度洞察报告
- Yearly: ¥299/年 (省¥169), same features, "最受欢迎" badge

Below cards show two payment buttons:
- "微信支付" (green, WeChat logo)
- "支付宝" (blue, Alipay logo)

When payment button clicked, call POST /functions/v1/payment-wechat or payment-alipay with body:
{ plan: 'monthly'|'yearly', user_id: currentUser.id }

Show a QR code modal with the returned qr_code_url for WeChat Pay.
For Alipay, redirect to returned payment_url.

After payment, poll GET /functions/v1/check-payment?out_trade_no=xxx every 3s for 5 minutes.
When status becomes 'active', refresh user session and show "升级成功！" toast.
```

- [ ] **Step 2: 创建 supabase/functions/payment-wechat/index.ts**

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
);

const WECHAT_MCHID = Deno.env.get("WECHAT_MCHID")!;
const WECHAT_APP_ID = Deno.env.get("WECHAT_APP_ID")!;
const WECHAT_API_V3_KEY = Deno.env.get("WECHAT_API_V3_KEY")!;

const PLANS = {
  monthly: { amount: 3900, name: "乳源月度订阅", days: 30 },
  yearly:  { amount: 29900, name: "乳源年度订阅", days: 365 },
};

serve(async (req) => {
  const url = new URL(req.url);

  // 处理支付回调通知
  if (url.pathname.endsWith("/notify") && req.method === "POST") {
    const body = await req.json();
    const outTradeNo = body.out_trade_no;
    const tradeState = body.trade_state;

    if (tradeState === "SUCCESS") {
      const { data: sub } = await supabase
        .from("subscriptions")
        .select("user_id, plan")
        .eq("out_trade_no", outTradeNo)
        .single();

      if (sub) {
        const plan = PLANS[sub.plan as keyof typeof PLANS];
        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + plan.days);

        await supabase.from("subscriptions")
          .update({ status: "active", started_at: new Date().toISOString(), expires_at: expiresAt.toISOString() })
          .eq("out_trade_no", outTradeNo);

        await supabase.from("users")
          .update({ subscription_tier: "pro", subscription_expires_at: expiresAt.toISOString() })
          .eq("id", sub.user_id);
      }
    }

    return new Response(JSON.stringify({ code: "SUCCESS" }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // 创建支付订单
  if (req.method === "POST") {
    const { plan, user_id } = await req.json();
    const planConfig = PLANS[plan as keyof typeof PLANS];
    if (!planConfig) return new Response("Invalid plan", { status: 400 });

    const outTradeNo = `DAIRY_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

    await supabase.from("subscriptions").insert({
      user_id,
      plan,
      amount: planConfig.amount,
      payment_method: "wechat",
      status: "pending",
      out_trade_no: outTradeNo,
    });

    // 调用微信支付 Native API 获取二维码链接
    // 实际实现需要微信支付 v3 签名，以下为示意结构
    const wechatPayload = {
      appid: WECHAT_APP_ID,
      mchid: WECHAT_MCHID,
      description: planConfig.name,
      out_trade_no: outTradeNo,
      amount: { total: planConfig.amount, currency: "CNY" },
      notify_url: `${Deno.env.get("SUPABASE_URL")}/functions/v1/payment-wechat/notify`,
    };

    // TODO: 添加微信支付 v3 签名（需要商户私钥）
    // 参考：https://pay.weixin.qq.com/wiki/doc/apiv3/apis/chapter3_4_1.shtml
    const wechatRes = await fetch("https://api.mch.weixin.qq.com/v3/pay/transactions/native", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `WECHATPAY2-SHA256-RSA2048 ${WECHAT_API_V3_KEY}`,
      },
      body: JSON.stringify(wechatPayload),
    });

    const wechatData = await wechatRes.json();

    return new Response(JSON.stringify({
      out_trade_no: outTradeNo,
      qr_code_url: wechatData.code_url,
    }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response("Method not allowed", { status: 405 });
});
```

- [ ] **Step 3: 创建 check-payment Edge Function**

```typescript
// supabase/functions/check-payment/index.ts
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
);

serve(async (req) => {
  const url = new URL(req.url);
  const outTradeNo = url.searchParams.get("out_trade_no");

  if (!outTradeNo) return new Response("Missing out_trade_no", { status: 400 });

  const { data } = await supabase
    .from("subscriptions")
    .select("status, expires_at")
    .eq("out_trade_no", outTradeNo)
    .single();

  return new Response(JSON.stringify(data), {
    headers: { "Content-Type": "application/json" },
  });
});
```

- [ ] **Step 4: 部署**

```bash
supabase functions deploy payment-wechat --no-verify-jwt
supabase functions deploy check-payment --no-verify-jwt
supabase secrets set WECHAT_MCHID=your_mchid WECHAT_APP_ID=your_appid WECHAT_API_V3_KEY=your_key
```

- [ ] **Step 5: 验证订单创建（沙盒模式）**

```bash
curl -X POST https://YOUR_PROJECT_REF.supabase.co/functions/v1/payment-wechat \
  -H "Content-Type: application/json" \
  -d '{"plan": "monthly", "user_id": "test-user-id"}'
```

预期：返回包含 `out_trade_no` 的 JSON，且 `subscriptions` 表有 `status=pending` 的新记录。

---

## Task 10: 前端模块数据对接（Lovable.dev）

**Interfaces:**
- Consumes: Supabase 表数据（articles, daily_digest, social_posts, company_updates）
- Produces: 六大模块展示真实数据，付费墙正确隔离

- [ ] **Step 1: 对接今日速览**

在 Lovable.dev 发送：

```
Update the 今日速览 section to fetch real data from Supabase.

Query: SELECT * FROM daily_digest WHERE date = TODAY ORDER BY created_at DESC LIMIT 1

Render highlights array as numbered list items:
- Free items (is_premium: false): show title + summary normally
- Premium items (is_premium: true): show title normally but blur the summary text with CSS filter:blur(4px), overlay a lock icon and "升级解锁" text

Show "今日速览生成中..." skeleton if no data for today yet.
```

- [ ] **Step 2: 对接乳业资讯**

```
Update the 乳业资讯 section to fetch from Supabase articles table.

Query: SELECT * FROM articles WHERE category = 'news' ORDER BY published_at DESC LIMIT 20

For free users (not logged in or subscription_tier='free'): limit to 20 articles total
For pro users: no limit, add "加载更多" button that fetches next 20

Each card shows:
- Title (clickable, opens source_url in new tab)
- Source name + published_at (formatted as "2小时前" relative time)
- Summary text (2 lines, ellipsis)
- Tags as colored chips: 政策=blue, 价格=green, 质量安全=red, 企业动态=orange, 技术=purple, 国际=gray
```

- [ ] **Step 3: 对接舆情监测**

```
Update the 重点舆情 section to fetch articles with sentiment_score.

Query: SELECT * FROM articles WHERE category = 'sentiment' OR sentiment_score < -0.3 ORDER BY published_at DESC LIMIT 10

For each article:
- Show a horizontal sentiment bar: red for negative (<-0.3), yellow for neutral (-0.3 to 0.3), green for positive (>0.3)
- Articles with sentiment_score < -0.5 get a red left border (3px solid #ef4444) as risk signal
- Show sentiment_score as percentage label

For free users: show only 3 items, rest blurred with "升级查看全部舆情" button
```

- [ ] **Step 4: 对接社交动态**

```
Update the 社交动态 section to fetch from social_posts table.

Query: SELECT * FROM social_posts ORDER BY created_at DESC LIMIT 20

Each card shows:
- Platform icon: 微博=red weibo icon, 微信=green wechat icon, 雪球=orange snowball icon, 东方财富=red, Twitter=black X icon
- Author name in bold
- Content (3 lines, ellipsis)  
- Engagement count with 👍 icon
- "查看原文" link to url

Add platform filter tabs at top: 全部 | 微博 | 微信 | 雪球 | Twitter
Clicking a tab filters the feed by platform.
```

- [ ] **Step 5: 对接企业追踪**

```
Update the 企业追踪 section to fetch from company_updates joined with companies.

For FREE users:
Query: SELECT cu.*, c.name, c.exchange, c.ticker FROM company_updates cu JOIN companies c ON cu.company_id = c.id WHERE cu.is_premium = false ORDER BY cu.published_at DESC LIMIT 10

For PRO users: same query without the is_premium filter

Show as a table with columns: 企业, 交易所, 代码, 最新动态(title), 时间
For free users, add a blurred row after the 5th domestic company row showing "国际企业数据" with lock icon and upgrade prompt.

Below the table, show price_data if available: price, change amount, change percentage (green if positive, red if negative).
```

- [ ] **Step 6: 对接深度洞察**

```
Update the 深度洞察 section to fetch premium insight articles.

Query: SELECT * FROM articles WHERE category = 'insight' ORDER BY published_at DESC LIMIT 6

Each report card shows:
- Title
- Published date
- First 3 lines of summary (always visible)
- "阅读全文" button

For FREE users: clicking "阅读全文" shows upgrade modal instead of content
For PRO users: clicking opens a modal with full content text
```

- [ ] **Step 7: 全流程验证**

在 Lovable.dev Preview 中验证：
1. 有爬虫数据后，乳业资讯显示真实文章
2. 未登录用户超过 20 条后看到"登录查看更多"
3. 登录免费用户：舆情只见 3 条，企业追踪看不到国际数据，洞察点击触发升级弹窗
4. 升级后（手动在 Supabase 将 subscription_tier 改为 'pro' 测试）：所有内容可见，付费墙消失

---

## 待确认（启动前必须准备）

| 项目 | 说明 |
|------|------|
| 微信开放平台 AppID | 微信登录必须，申请地址：open.weixin.qq.com |
| 微信支付商户号 | 申请地址：pay.weixin.qq.com |
| 支付宝商户 PID | 蚂蚁开放平台申请 |
| 短信服务 | 阿里云短信 or 腾讯云短信，申请模板："您的验证码为${code}，5分钟内有效" |
| OpenAI API Key | platform.openai.com，建议设置 $50 月限额 |
| 产品品牌名 | 当前占位"乳源"，确认后替换所有 Prompt |
