"""Scrapling-based fetcher for sites without RSS feeds."""
from scrapling import Fetcher
from datetime import datetime, timezone
from urllib.parse import urlparse


def fetch_scrapling(source: dict) -> list[dict]:
    """Fetch a web page with Scrapling and extract article links.

    - Uses Fetcher(auto_match=True)
    - Selects elements via source.get("selector", "a")
    - Builds relative links into absolute URLs
    - Filters entries where title or link is empty
    - Returns at most 15 articles
    - On any exception: prints error and returns []
    """
    try:
        fetcher = Fetcher(auto_match=True)
        page = fetcher.get(source["url"])
        selector = source.get("selector", "a")

        parsed_url = urlparse(source["url"])
        base = f"{parsed_url.scheme}://{parsed_url.netloc}"

        now_iso = datetime.now(tz=timezone.utc).isoformat()
        articles = []

        for el in page.css(selector):
            title = (el.text or "").strip()
            link = el.attrib.get("href", "")

            if not title or not link:
                continue

            # Resolve relative URLs
            if link.startswith("/"):
                link = base + link

            articles.append({
                "title": title,
                "content": "",
                "source_url": link,
                "source_name": source.get("name", ""),
                "category": source.get("category", ""),
                "language": source.get("language", "zh"),
                "published_at": now_iso,
                "is_premium": False,
                "tags": [],
            })

            if len(articles) >= 15:
                break

        return articles

    except Exception as e:
        print(f"[scrapling_fetcher] Error fetching {source.get('url', '')}: {e}")
        return []
