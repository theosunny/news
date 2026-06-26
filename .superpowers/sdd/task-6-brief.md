# Task 6: RSS + Scrapling 爬虫 + AI 摘要

## Context
乳业情报平台爬虫，位于 E:/claudpro/news/dairy-intel-crawler。
Task 5 已完成：crawler/sources.py、crawler/supabase_writer.py、requirements.txt 已存在。
这是 Task 6：实现 RSS 解析、Scrapling 抓取、Claude AI 摘要、以及主入口协调器。

## Global Constraints
- Python 3.11+
- AI 摘要使用 Claude Haiku（通过中转站），不使用 OpenAI
  - 中转站 base_url 从环境变量 ANTHROPIC_BASE_URL 读取
  - API key 从环境变量 ANTHROPIC_API_KEY 读取
  - 使用 anthropic Python SDK，model="claude-haiku-4-5-20251001"
- 所有密钥从环境变量读取，不硬编码
- 工作目录：E:/claudpro/news/dairy-intel-crawler

## Files to Create
- `crawler/rss_fetcher.py`
- `crawler/scrapling_fetcher.py`
- `crawler/ai_summarizer.py`
- `crawler/main.py`
- `tests/test_rss_fetcher.py`
- `tests/test_ai_summarizer.py`

## Interfaces Consumed from Task 5
- `from crawler.sources import SOURCES, SOCIAL_SOURCES`
- `from crawler.supabase_writer import write_articles, write_social_posts`
  - write_articles(articles: list[dict]) -> int
  - write_social_posts(posts: list[dict]) -> int

## Interfaces Produced (for Task 7 main.py usage)
- `fetch_rss(source: dict) -> list[dict]`
- `fetch_scrapling(source: dict) -> list[dict]`
- `summarize_article(title: str, content: str, language: str) -> dict`
  返回：{"summary": str, "sentiment_score": float, "tags": list[str]}

## Implementation Requirements

### crawler/rss_fetcher.py
```python
import feedparser
from datetime import datetime, timezone

def fetch_rss(source: dict) -> list[dict]:
    """
    解析 RSS 源，返回标准化文章列表。
    - 用 feedparser.parse(source["url"]) 解析
    - 最多取 20 条（feed.entries[:20]）
    - 每篇文章提取：title, content（优先 entry.summary，其次 entry.content[0].value），
      source_url（entry.link），source_name（source["name"]），
      category（source["category"]），language（source.get("language","en")），
      published_at（从 published_parsed 转为 ISO 格式 UTC 字符串），
      is_premium=False，tags=[]
    - content 截断到 2000 字符
    - 过滤掉 title 或 source_url 为空的条目
    - 任何异常打印错误日志并返回 []
    """
```

### crawler/scrapling_fetcher.py
```python
from scrapling import Fetcher
from datetime import datetime, timezone
from urllib.parse import urlparse

def fetch_scrapling(source: dict) -> list[dict]:
    """
    用 Scrapling 抓取无 RSS 的网页。
    - Fetcher(auto_match=True)
    - fetcher.get(source["url"])
    - 用 source.get("selector", "a") 提取元素
    - 每篇：title=el.text.strip()，link=el.attrib.get("href","")
    - 相对链接补全：link.startswith("/") 时补 scheme://netloc
    - 过滤掉 title 或 link 为空的条目
    - 最多 15 条
    - content="" （无正文），published_at=now UTC ISO，is_premium=False，tags=[]
    - 任何异常打印错误日志并返回 []
    """
```

### crawler/ai_summarizer.py
使用 Claude Haiku 通过中转站：

```python
import os
import json
from anthropic import Anthropic

def get_client() -> Anthropic:
    return Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
    )

SUMMARIZE_PROMPT = """你是乳业行业分析师。请对以下文章生成：
1. 中文摘要（2-3句，聚焦关键信息）
2. 情感得分（-1.0到1.0，负面事件接近-1，正面接近1，中性接近0）
3. 标签（从以下选1-3个：政策、价格、质量安全、企业动态、技术、国际）

返回 JSON 格式：{{"summary": "...", "sentiment_score": 0.0, "tags": ["..."]}}

标题：{title}
内容：{content}
"""

def summarize_article(title: str, content: str, language: str = "zh") -> dict:
    """
    调用 Claude Haiku 生成摘要、情感得分、标签。
    - title 为空时直接返回 {"summary": "", "sentiment_score": 0.0, "tags": []}
    - content 截断到 1000 字符（content[:1000] if content else "（无正文）"）
    - model="claude-haiku-4-5-20251001"
    - max_tokens=300
    - 解析返回的 JSON，提取 summary/sentiment_score/tags
    - 任何异常打印错误日志，返回 {"summary": "", "sentiment_score": 0.0, "tags": []}
    """
```

### crawler/main.py
```python
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

## Tests

### tests/test_rss_fetcher.py
两个测试：

```python
from unittest.mock import patch, MagicMock
from crawler.rss_fetcher import fetch_rss

@patch("crawler.rss_fetcher.feedparser.parse")
def test_fetch_rss_returns_articles(mock_parse):
    mock_entry = MagicMock()
    mock_entry.title = "奶价上涨3%"
    mock_entry.link = "https://dairyreporter.com/news/1"
    mock_entry.summary = "全球原奶价格本周上涨3%..."
    mock_entry.published_parsed = (2026, 6, 25, 0, 0, 0, 0, 0, 0)
    # 让 hasattr 检查 summary 返回 True
    del mock_entry.content  # 确保没有 content 属性（或通过 spec 控制）
    mock_parse.return_value = MagicMock(entries=[mock_entry])

    source = {"name": "Test", "url": "https://fake.com/rss", "category": "news", "language": "en"}
    articles = fetch_rss(source)

    assert len(articles) == 1
    assert articles[0]["title"] == "奶价上涨3%"
    assert articles[0]["category"] == "news"
    assert articles[0]["source_url"] == "https://dairyreporter.com/news/1"
    assert articles[0]["is_premium"] == False

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

### tests/test_ai_summarizer.py
两个测试：

```python
from unittest.mock import patch, MagicMock
from crawler.ai_summarizer import summarize_article

@patch("crawler.ai_summarizer.get_client")
def test_summarize_article_returns_dict(mock_get_client):
    import json
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_message = MagicMock()
    mock_message.content[0].text = json.dumps({
        "summary": "蒙牛发布新品",
        "sentiment_score": 0.5,
        "tags": ["企业动态"]
    })
    mock_client.messages.create.return_value = mock_message

    result = summarize_article("蒙牛发布新产品", "蒙牛乳业今日发布...")
    assert result["summary"] == "蒙牛发布新品"
    assert result["sentiment_score"] == 0.5
    assert "企业动态" in result["tags"]

def test_summarize_empty_title():
    result = summarize_article("", "")
    assert result == {"summary": "", "sentiment_score": 0.0, "tags": []}
```

## TDD Steps
1. 先写所有测试文件
2. 运行 pytest，确认失败（ImportError 或 AttributeError）
3. 实现 rss_fetcher.py、scrapling_fetcher.py、ai_summarizer.py、main.py
4. 运行 pytest，确认全部通过（4 tests）
5. git commit

## Run Command
```powershell
cd E:/claudpro/news/dairy-intel-crawler
$env:SUPABASE_URL="fake"; $env:SUPABASE_SERVICE_KEY="fake"; $env:ANTHROPIC_API_KEY="fake"; $env:ANTHROPIC_BASE_URL="https://api.anthropic.com"
pytest tests/test_rss_fetcher.py tests/test_ai_summarizer.py -v
```

Expected: 4 passed

## Notes
- MagicMock 的 hasattr 行为：MagicMock 默认对任何属性 hasattr 都返回 True。
  如果 fetch_rss 用 `hasattr(entry, "summary")` 判断，test 中的 mock_entry 默认就有 summary。
  如果需要控制，可以用 `spec` 或显式 `del mock_entry.content`。
  实现时建议直接 `getattr(entry, "summary", "")` 避免 hasattr 复杂性。
- scrapling_fetcher 的测试不强制要求（Scrapling 难以在无网络环境下 mock），可以跳过。

## Report File
写报告到：E:/claudpro/news/dairy-intel-crawler/.superpowers/sdd/task-6-report.md
报告内容：创建的文件、测试输出、commit hash。
最后一行：DONE / DONE_WITH_CONCERNS / BLOCKED
