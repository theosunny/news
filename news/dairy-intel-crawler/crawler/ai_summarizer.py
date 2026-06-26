"""Claude AI summarizer for the dairy intelligence crawler."""
import os
import json
from anthropic import Anthropic


def get_client() -> Anthropic:
    """Create an Anthropic client from environment variables."""
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

_EMPTY_RESULT = {"summary": "", "sentiment_score": 0.0, "tags": []}


def summarize_article(title: str, content: str, language: str = "zh") -> dict:
    """Call Claude Haiku to generate a summary, sentiment score, and tags.

    - Returns empty result immediately when title is empty
    - Truncates content to 1000 chars
    - model="claude-haiku-4-5-20251001", max_tokens=300
    - Parses returned JSON for summary/sentiment_score/tags
    - On any exception: prints error and returns empty result
    """
    if not title:
        return dict(_EMPTY_RESULT)

    truncated_content = (content[:1000] if content else "（无正文）")

    try:
        client = get_client()
        prompt = SUMMARIZE_PROMPT.format(title=title, content=truncated_content)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text
        data = json.loads(raw_text)
        return {
            "summary": data.get("summary", ""),
            "sentiment_score": float(data.get("sentiment_score", 0.0)),
            "tags": data.get("tags", []),
        }
    except Exception as e:
        print(f"[ai_summarizer] Error summarizing '{title}': {e}")
        return dict(_EMPTY_RESULT)
