"""
filters.py

Keyword filtering for fetched items.
"""


def keyword_filter(items: list[dict], keywords: list[str]) -> list[dict]:
    """Return items whose title or summary contains at least one keyword (case-insensitive)."""
    if not keywords:
        return items
    lower_kws = [k.lower() for k in keywords]
    kept = []
    for item in items:
        haystack = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        if any(kw in haystack for kw in lower_kws):
            kept.append(item)
    return kept
