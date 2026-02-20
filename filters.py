"""
filters.py

Keyword filtering for fetched items.
"""


def keyword_filter(items: list[dict], keywords: list[str]) -> list[dict]:
    """Return items whose title or summary contains at least one keyword (case-insensitive)."""
    if not keywords:
        return items
    lower_kws = [k.lower() for k in keywords]
    return [
        item for item in items
        if any(
            kw in (item.get("title", "") + " " + item.get("summary", "")).lower()
            for kw in lower_kws
        )
    ]
