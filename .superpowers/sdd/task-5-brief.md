# Task 5: 爬虫基础设施

## Context
乳业情报平台爬虫仓库，位于 E:/claudpro/news/dairy-intel-crawler。
这是 Task 5/10，建立爬虫的基础模块：数据源配置、Supabase 写入器、测试。

## Global Constraints
- Python 最低版本 3.11
- AI 摘要使用 Claude Haiku（通过中转站），不使用 OpenAI
- 所有写入 Supabase 使用 service_role key（绕过 RLS）
- 所有密钥从环境变量读取，不硬编码
- 工作目录：E:/claudpro/news/dairy-intel-crawler

## Files to Create
- `requirements.txt` — Python 依赖
- `crawler/sources.py` — 数据源配置
- `crawler/supabase_writer.py` — Supabase 写入器
- `crawler/__init__.py` — 空文件使 crawler 成为 package
- `tests/__init__.py` — 空文件
- `tests/test_supabase_writer.py` — 单元测试

## Requirements

### requirements.txt
```
scrapling==0.2.9
feedparser==6.0.11
anthropic==0.28.0
supabase==2.5.0
python-dotenv==1.0.1
pytest==8.2.2
pytest-asyncio==0.23.7
httpx==0.27.0
```

### crawler/sources.py
数据源配置，包含三个列表：SOURCES、SOCIAL_SOURCES、COMPANY_SOURCES。

SOURCES 包含：
- Dairy Reporter: RSS, https://www.dairyreporter.com/rss/news, category=news, language=en
- USDA Dairy: RSS, https://www.ams.usda.gov/rss/mncs/dairy.xml, category=news, language=en
- Fonterra News: RSS, https://www.fonterra.com/nz/en/news-and-media/news.rss.xml, category=news, language=en
- 农业农村部: scrapling, http://www.moa.gov.cn/govpublic/, category=news, language=zh, selector="div.main-list li a"
- GDT拍卖: scrapling, https://www.globaldairytrade.info/en/product-results/, category=company, language=en, selector="table.results-table tr"

SOCIAL_SOURCES 包含：
- xueqiu: scrapling, https://xueqiu.com/search?q=乳业&type=status, selector="div.timeline-item"
- eastmoney: scrapling, https://search.eastmoney.com/快讯?keyword=乳业, selector="div.news-item"

COMPANY_SOURCES 包含企业列表（name, ticker, exchange, is_premium）：
- 伊利股份, 600887, SSE, False
- 蒙牛乳业, 02319, HKEX, False
- 光明乳业, 600597, SSE, False
- 新乳业, 002946, SZE, False
- Fonterra, FCG, NZX, True
- Bega Cheese, BGA, ASX, True

### crawler/supabase_writer.py
提供三个函数：

```python
def get_client() -> Client:
    # 从环境变量 SUPABASE_URL 和 SUPABASE_SERVICE_KEY 创建客户端

def write_articles(articles: list[dict]) -> int:
    # upsert articles 表，on_conflict="source_url"，ignore_duplicates=True
    # 返回实际插入数量（len(result.data)）
    # articles 为空时直接返回 0，不调用 client

def write_social_posts(posts: list[dict]) -> int:
    # upsert social_posts 表，on_conflict="url"，ignore_duplicates=True
    # posts 为空时直接返回 0

def write_company_updates(updates: list[dict]) -> int:
    # insert company_updates 表
    # updates 为空时直接返回 0
```

### tests/test_supabase_writer.py
三个测试，全部使用 unittest.mock.patch：

1. `test_write_articles_empty` — articles=[] 时返回 0，不调用 client
2. `test_write_articles_returns_count` — mock client 返回 2 条 data，断言返回 2
3. `test_write_social_posts_empty` — posts=[] 时返回 0，不调用 client

## TDD Steps
1. 先写测试文件
2. 运行确认失败（ImportError 或 AssertionError）
3. 实现 supabase_writer.py
4. 运行确认全部通过
5. git commit

## Run Command
```
cd E:/claudpro/news/dairy-intel-crawler
SUPABASE_URL=fake SUPABASE_SERVICE_KEY=fake pytest tests/test_supabase_writer.py -v
```

Expected: 3 passed

## Report File
写报告到：E:/claudpro/news/dairy-intel-crawler/.superpowers/sdd/task-5-report.md
报告内容：实际创建的文件列表、测试运行输出、遇到的问题、git commit hash。
最后一行写状态：DONE / DONE_WITH_CONCERNS / BLOCKED
