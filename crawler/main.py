"""Main entry point for the dairy intelligence crawler."""
from crawler.sources import SOURCES
from crawler.rss_fetcher import fetch_rss
from crawler.scrapling_fetcher import fetch_scrapling
from crawler.ai_summarizer import summarize_article
from crawler.supabase_writer import write_articles


def run():
    """Fetch articles from all sources, summarize with AI, and write to Supabase."""
    all_articles = []
    for source in SOURCES:
        print(f"[main] Fetching: {source['name']}")
        # sources.py uses "type" field with values "RSS" or "scrapling"
        source_type = source.get("type", "").lower()
        if source_type == "rss":
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
