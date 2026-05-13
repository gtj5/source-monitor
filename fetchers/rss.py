"""
fetchers/rss.py

Fetch items from an RSS or Atom feed.
"""

from datetime import datetime, timezone

import feedparser

_USER_AGENT = "source-monitor/1.0"
_ACCEPT     = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"


def fetch_rss(source: dict) -> list[dict]:
    """Parse an RSS/Atom feed and return normalized items."""
    feed = feedparser.parse(
        source["url"],
        agent=_USER_AGENT,
        request_headers={"Accept": _ACCEPT},
    )

    # feedparser swallows HTTP errors silently — surface them so empty
    # results aren't mistaken for "feed had nothing new".
    status = getattr(feed, "status", None)
    if status and status >= 400:
        print(f"  ! HTTP {status} from feed")
    if feed.bozo and not feed.entries:
        reason = getattr(feed, "bozo_exception", "unknown error")
        print(f"  ! Feed parse error: {reason}")

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
