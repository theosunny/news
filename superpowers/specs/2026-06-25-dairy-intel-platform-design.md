# 乳业情报平台设计文档

**日期**：2026-06-25  
**产品名**：待定（参考 PrimeScope，建议取乳业相关品牌名）  
**参考站**：ai-news-digest.com（PrimeScope）  
**构建平台**：Lovable.dev

---

## 一、产品定位

面向乳业从业者（牧场、加工厂、经销商）和投资/分析师的一站式行业情报平台。自动聚合国内外乳业资讯、舆情、社交动态、企业行情，AI 生成摘要与深度洞察，免费 + 付费分层。

---

## 二、技术架构

```
┌─────────────────────────────────────────┐
│          Lovable.dev 生成                │
│         React + Vite 前端               │
│  (部署在 Cloudflare CDN)                │
└──────────────┬──────────────────────────┘
               │ REST / Realtime
┌──────────────▼──────────────────────────┐
│              Supabase                   │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │  PostgreSQL │  │  Edge Functions  │  │
│  │  (内容存储) │  │  (AI摘要/支付)   │  │
│  └─────────────┘  └──────────────────┘  │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │  Auth       │  │  RLS 权限控制    │  │
│  │ (手机+微信) │  │  (付费内容隔离)  │  │
│  └─────────────┘  └──────────────────┘  │
└──────────────┬──────────────────────────┘
               │
   ┌───────────┴──────────────┐
   ▼                          ▼
GitHub Actions             OpenAI/Claude API
Scrapling Python 爬虫      (AI摘要 + 洞察生成)
(每小时定时抓取)
               │
   ┌───────────┴──────────────┐
   ▼                          ▼
微信支付 / 支付宝           短信服务
(订阅回调)                 (阿里云/腾讯云)
```

### 爬虫层说明
- **简单 RSS 源**：GitHub Actions 中用 Python `feedparser` 解析
- **复杂网页**（无 RSS、JS 渲染、有反爬）：使用 [Scrapling](https://github.com/D4Vinci/Scrapling) 处理
- 抓取结果通过 Supabase REST API 写入 PostgreSQL
- 触发频率：每小时一次（GitHub Actions `schedule: cron`）

---

## 三、六大模块

### 1. 今日重点速览
- 每日凌晨 6:00 由 AI 从前 24 小时内容中提炼 5-8 条最重要动态
- 免费用户：标题 + 一句话摘要
- 付费用户：完整分析段落

### 2. 乳业资讯
全量资讯流，AI 自动摘要 + 标签。

**国内来源**：
- 中国乳业杂志（RSS）
- 中国食品报
- 农业农村部公告
- 奶牛杂志
- 国家奶牛产业技术体系（Scrapling）

**国际来源**：
- Dairy Reporter RSS
- USDA Dairy RSS
- Fonterra 新闻室
- Rabobank 乳业报告

**标签体系**：政策 / 价格 / 质量安全 / 企业动态 / 技术 / 国际

### 3. 重点舆情监测
- AI 情感分析，自动识别负面事件（质量问题、召回、政策收紧）
- 风险信号高亮展示
- 付费用户可看全部历史 + 趋势图

### 4. 社交媒体动态

| 平台 | 数据获取方式 | 内容 |
|------|-------------|------|
| 微博 | 关键词搜索 API / Scrapling | 伊利、蒙牛、原奶价格等话题 |
| 微信公众号 | 搜狗微信 RSS | 行业公众号文章 |
| 雪球 | Scrapling | 乳业股票讨论热度 |
| 东方财富 | Scrapling | 相关板块舆情 |
| Twitter/X | 官方 API（Basic） | Fonterra、Arla、Lactalis 官号 |

### 5. 企业动态追踪

**国内企业**：伊利、蒙牛、光明、新乳业、澳亚集团  
**国际企业**：Fonterra（NZX）、Bega Cheese（ASX）、Murray Goulburn  
**价格行情**：
- GDT 全球乳制品拍卖（每两周，Scrapling 抓取）
- 国内原奶收购均价（每周，农业农村部数据）

免费用户：仅看国内企业动态  
付费用户：国内 + 国际 + GDT 行情

### 6. 乳业深度洞察（付费专属）
- AI 基于 2-4 周聚合数据生成行业分析报告
- 覆盖：价格趋势预判、政策影响解读、企业动向分析
- 每周发布一篇，免费用户只见标题

---

## 四、用户系统 + 付费

### 登录方式
| 方式 | 实现 |
|------|------|
| 手机号 + 验证码 | Supabase Auth + 阿里云/腾讯云短信 |
| 微信登录 | Supabase Auth 自定义 OAuth，需微信开放平台 AppID |

### 订阅方案
| 方案 | 价格 | 说明 |
|------|------|------|
| 免费版 | ¥0 | 基础资讯，每日限 20 条 |
| 月付 | ¥39/月 | 全部内容 |
| 年付 | ¥299/年 | 约 7.5 折 |

支付通道：微信支付 + 支付宝，Supabase Edge Function 处理异步回调，更新 `subscription_tier`。

### 权限控制
Supabase RLS（Row Level Security）策略：
- `is_premium = true` 的行仅 `subscription_tier = 'pro'` 用户可读
- 前端无需判断，数据库层直接隔离

---

## 五、数据库设计

```sql
-- 用户
users (
  id uuid PK,
  phone text UNIQUE,
  wechat_openid text UNIQUE,
  subscription_tier text DEFAULT 'free',  -- free | pro
  subscription_expires_at timestamptz,
  created_at timestamptz
)

-- 内容文章
articles (
  id uuid PK,
  title text,
  summary text,           -- AI 生成摘要（2-3句）
  content text,           -- 原文或详细分析
  source_url text,
  source_name text,
  category text,          -- news|sentiment|social|company|insight
  tags text[],
  sentiment_score float,  -- -1.0 到 1.0
  is_premium boolean DEFAULT false,
  published_at timestamptz,
  created_at timestamptz
)

-- 企业信息
companies (
  id uuid PK,
  name text,
  exchange text,          -- SSE|SZE|NZX|ASX
  ticker text,
  country text,
  is_active boolean DEFAULT true
)

-- 企业动态
company_updates (
  id uuid PK,
  company_id uuid FK,
  title text,
  summary text,
  price_data jsonb,       -- { price, change, change_pct, date }
  published_at timestamptz
)

-- 社交动态
social_posts (
  id uuid PK,
  platform text,          -- weibo|wechat|xueqiu|eastmoney|twitter
  content text,
  author text,
  engagement_count int,
  url text,
  created_at timestamptz
)

-- 今日速览
daily_digest (
  id uuid PK,
  date date UNIQUE,
  highlights jsonb,       -- [{title, summary, is_premium}]
  created_at timestamptz
)

-- RSS 数据源配置
rss_sources (
  id uuid PK,
  name text,
  url text,
  category text,
  scraping_method text,   -- rss|scrapling
  is_active boolean DEFAULT true,
  last_fetched_at timestamptz
)

-- 订阅记录
subscriptions (
  id uuid PK,
  user_id uuid FK,
  plan text,              -- monthly|yearly
  amount int,             -- 分（人民币）
  payment_method text,    -- wechat|alipay
  status text,            -- pending|active|expired|cancelled
  started_at timestamptz,
  expires_at timestamptz
)
```

---

## 六、Lovable.dev Prompt 策略

Lovable.dev 通过自然语言生成代码，需要分阶段给 Prompt：

1. **初始化**：描述整体布局、六大模块、暗色科技风 UI
2. **认证页**：手机号验证码登录 + 微信登录按钮
3. **付费墙**：模糊遮罩 + 升级提示组件
4. **Supabase 集成**：连接数据库，配置 RLS
5. **各模块卡片**：逐模块细化 UI

---

## 七、待确认事项

- [ ] 产品品牌名
- [ ] 微信开放平台 AppID（微信登录必须）
- [ ] 微信支付 / 支付宝商户号
- [ ] 短信服务商选择（阿里云 vs 腾讯云）
- [ ] AI 调用：OpenAI GPT-4o vs Claude（成本差异）
