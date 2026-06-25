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
