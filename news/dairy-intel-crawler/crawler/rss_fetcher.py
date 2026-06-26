"""RSS feed fetcher for the dairy intelligence crawler."""
import feedparser
from datetime import datetime, timezone


def fetch_rss(source: dict) -> list[dict]:
    """Parse an RSS feed and return a normalized list of articles.

    - Uses feedparser.parse(source["url"])
    - Takes at most 20 entries
    - Extracts: title, content (summary preferred, falls back to content[0].value),
      source_url, source_name, category, language, published_at, is_premium, tags
    - Truncates content to 2000 chars
    - Filters entries where title or source_url is empty
    - On any exception: prints error and returns []
    """
    try:
        feed = feedparser.parse(source["url"])
        articles = []

        for entry in feed.entries[:20]:
            title = getattr(entry, "title", "") or ""
            source_url = getattr(entry, "link", "") or ""

            # Skip entries missing required fields
            if not title or not source_url:
                continue

            # Prefer summary, fall back to content[0].value
            content = getattr(entry, "summary", "")
            if not content:
                content_list = getattr(entry, "content", None)
                if content_list:
                    content = content_list[0].value if content_list else ""
            content = (content or "")[:2000]

            # Convert published_parsed to ISO UTC string
            published_at = None
            parsed_time = getattr(entry, "published_parsed", None)
            if parsed_time:
                try:
                    published_at = datetime(
                        *parsed_time[:6], tzinfo=timezone.utc
                    ).isoformat()
                except Exception:
                    published_at = None

            articles.append({
                "title": title,
                "content": content,
                "source_url": source_url,
                "source_name": source.get("name", ""),
                "category": source.get("category", ""),
                "language": source.get("language", "en"),
                "published_at": published_at,
                "is_premium": False,
                "tags": [],
            })

        return articles

    except Exception as e:
        print(f"[rss_fetcher] Error fetching {source.get('url', '')}: {e}")
        return []
