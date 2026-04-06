"""Fetch news articles from RSS feeds and NewsAPI."""

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests
import yaml

logger = logging.getLogger(__name__)

SOURCES_PATH = Path(__file__).parent / "sources.yaml"
NEWSAPI_BASE = "https://newsapi.org/v2/everything"
MAX_AGE_HOURS = 28  # Include articles from last 28 hours to avoid gaps


def load_sources() -> dict:
    with open(SOURCES_PATH) as f:
        return yaml.safe_load(f)


def article_id(title: str, url: str) -> str:
    """Generate a dedup key from title + url."""
    raw = f"{title.strip().lower()}|{url.strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()


def fetch_rss_feeds(feeds: list[dict], cutoff: datetime) -> list[dict]:
    """Fetch articles from all RSS feeds, filtering by cutoff time."""
    articles = []
    for feed_cfg in feeds:
        name = feed_cfg["name"]
        url = feed_cfg["url"]
        try:
            parsed = feedparser.parse(url)
            if parsed.bozo and not parsed.entries:
                logger.warning(f"Failed to parse RSS feed: {name} ({url})")
                continue

            for entry in parsed.entries:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

                if published and published < cutoff:
                    continue

                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()
                if not title or not link:
                    continue

                # Strip HTML tags from summary
                if "<" in summary:
                    import re
                    summary = re.sub(r"<[^>]+>", "", summary).strip()

                articles.append({
                    "id": article_id(title, link),
                    "title": title,
                    "url": link,
                    "summary": summary[:500] if summary else "",
                    "source": name,
                    "published": published.isoformat() if published else None,
                    "category": feed_cfg["category"],
                    "subsection": feed_cfg["subsection"],
                })

            logger.info(f"Fetched {name}: {len(parsed.entries)} entries")
        except Exception as e:
            logger.error(f"Error fetching {name}: {e}")
            continue

    return articles


def fetch_newsapi(queries: list[dict], cutoff: datetime) -> list[dict]:
    """Fetch articles from NewsAPI for each configured query."""
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        logger.warning("NEWS_API_KEY not set, skipping NewsAPI queries")
        return []

    articles = []
    from_date = cutoff.strftime("%Y-%m-%dT%H:%M:%S")

    for query_cfg in queries:
        query = query_cfg["query"]
        try:
            resp = requests.get(
                NEWSAPI_BASE,
                params={
                    "q": query,
                    "from": from_date,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 10,
                    "apiKey": api_key,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("articles", []):
                title = (item.get("title") or "").strip()
                url = (item.get("url") or "").strip()
                if not title or not url or title == "[Removed]":
                    continue

                articles.append({
                    "id": article_id(title, url),
                    "title": title,
                    "url": url,
                    "summary": (item.get("description") or "")[:500],
                    "source": item.get("source", {}).get("name", "NewsAPI"),
                    "published": item.get("publishedAt"),
                    "category": query_cfg["category"],
                    "subsection": query_cfg["subsection"],
                })

            logger.info(f"NewsAPI '{query[:40]}...': {len(data.get('articles', []))} results")
        except Exception as e:
            logger.error(f"NewsAPI error for '{query[:40]}': {e}")
            continue

    return articles


def deduplicate(articles: list[dict]) -> list[dict]:
    """Remove duplicate articles by id."""
    seen = set()
    unique = []
    for article in articles:
        if article["id"] not in seen:
            seen.add(article["id"])
            unique.append(article)
    return unique


def fetch_all() -> dict:
    """Main entry point: fetch from all sources, deduplicate, return structured data."""
    sources = load_sources()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)

    logger.info(f"Fetching articles since {cutoff.isoformat()}")

    rss_articles = fetch_rss_feeds(sources.get("rss_feeds", []), cutoff)
    newsapi_articles = fetch_newsapi(sources.get("newsapi_queries", []), cutoff)

    all_articles = deduplicate(rss_articles + newsapi_articles)
    logger.info(f"Total articles after dedup: {len(all_articles)}")

    # Group by category and subsection
    grouped = {}
    for cat_key, cat_cfg in sources.get("categories", {}).items():
        grouped[cat_key] = {
            "display_name": cat_cfg["display_name"],
            "weight": cat_cfg["weight"],
            "subsections": {},
        }
        for subsection in cat_cfg.get("subsections", []):
            grouped[cat_key]["subsections"][subsection] = []

    for article in all_articles:
        cat = article["category"]
        sub = article["subsection"]
        if cat in grouped and sub in grouped[cat]["subsections"]:
            grouped[cat]["subsections"][sub].append(article)

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_articles": len(all_articles),
        "categories": grouped,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import json
    result = fetch_all()
    print(json.dumps(result, indent=2, default=str))
