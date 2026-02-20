"""
fetchers/rss.py

Fetch items from an RSS or Atom feed.
"""

from datetime import datetime, timezone

import feedparser

_HEADERS = {
    "User-Agent": "source-monitor/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_rss(source: dict) -> list[dict]:
    """Parse an RSS/Atom feed and return normalized items."""
    feed = feedparser.parse(
        source["url"],
        agent=_HEADERS["User-Agent"],
        request_headers={"Accept": _HEADERS["Accept"]},
    )
    now = datetime.now(timezone.utc).isoformat()
    items = []
    for entry in feed.entries:
        items.append({
            "source":     source["name"],
            "title":      entry.get("title", "").strip(),
            "url":        entry.get("link", "").strip(),
            "published":  entry.get("published", ""),
            "summary":    entry.get("summary", entry.get("title", "")).strip(),
            "created_at": now,
        })
    print(f"  → {len(items)} items")
    return items
