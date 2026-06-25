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
