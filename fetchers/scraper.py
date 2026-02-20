"""
fetchers/scraper.py

Fetch items by scraping an HTML page using CSS selectors defined in config.

Selector config keys (all optional except `items`):
  items       - CSS selector for the repeating item container
  title       - CSS selector for the title element (text content used)
  link        - CSS selector for the anchor tag (href used)
  link_prefix - Prepended to relative hrefs (e.g. "https://example.com")
  summary     - CSS selector for the description element
  date        - CSS selector for the date element
  date_attr   - If set, reads this attribute from the date element instead of text
"""

from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": "source-monitor/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_scrape(source: dict) -> list[dict]:
    """Scrape an HTML page and return normalized items."""
    sel = source.get("selectors", {})

    response = requests.get(source["url"], headers=_HEADERS, timeout=15)
    response.raise_for_status()

    soup  = BeautifulSoup(response.text, "html.parser")
    cards = soup.select(sel.get("items", ""))
    now   = datetime.now(timezone.utc).isoformat()

    items = []
    for card in cards:
        title = _text(card, sel.get("title"))
        url   = _link(card, sel.get("link"), sel.get("link_prefix", ""))
        summary   = _text(card, sel.get("summary"))
        published = _date(card, sel.get("date"), sel.get("date_attr"))

        if not title or not url:
            continue

        items.append({
            "source":     source["name"],
            "title":      title,
            "url":        url,
            "published":  published,
            "summary":    summary,
            "created_at": now,
        })

    print(f"  → {len(items)} items")
    return items


# ── helpers ────────────────────────────────────────────────────────────────────

def _text(card, selector: str | None) -> str:
    if not selector:
        return ""
    tag = card.select_one(selector)
    return tag.get_text(strip=True) if tag else ""


def _link(card, selector: str | None, prefix: str) -> str:
    if not selector:
        return ""
    tag = card.select_one(selector)
    if not tag:
        return ""
    href = tag.get("href", "")
    return (prefix + href) if href.startswith("/") else href


def _date(card, selector: str | None, attr: str | None) -> str:
    if not selector:
        return ""
    tag = card.select_one(selector)
    if not tag:
        return ""
    if attr:
        return tag.get(attr, "")
    return tag.get_text(strip=True)
