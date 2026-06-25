"""Supabase writer for the dairy intelligence crawler.

All keys are read from environment variables — never hardcoded.
Uses service_role key to bypass RLS.
"""
import os
from supabase import create_client, Client


def get_client() -> Client:
    """Create a Supabase client from environment variables."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def write_articles(articles: list[dict]) -> int:
    """Upsert articles into the articles table.

    Deduplication is based on source_url.
    Returns the number of rows actually inserted.
    """
    if not articles:
        return 0

    client = get_client()
    result = (
        client.table("articles")
        .upsert(articles, on_conflict="source_url", ignore_duplicates=True)
        .execute()
    )
    return len(result.data)


def write_social_posts(posts: list[dict]) -> int:
    """Upsert social posts into the social_posts table.

    Deduplication is based on url.
    Returns the number of rows actually inserted.
    """
    if not posts:
        return 0

    client = get_client()
    result = (
        client.table("social_posts")
        .upsert(posts, on_conflict="url", ignore_duplicates=True)
        .execute()
    )
    return len(result.data)


def write_company_updates(updates: list[dict]) -> int:
    """Insert company updates into the company_updates table.

    Returns the number of rows inserted.
    """
    if not updates:
        return 0

    client = get_client()
    result = client.table("company_updates").insert(updates).execute()
    return len(result.data)
