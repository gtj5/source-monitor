"""
pipeline.py

Generalized source monitoring pipeline.
Reads config.yaml, fetches each source, applies keyword filter, and exports.

Run:  python pipeline.py
"""

import os
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

from exporters.html import export_html
from exporters.xlsx import export_xlsx
from fetchers.rss import fetch_rss
from filters import keyword_filter
from scoring import analyze_item
from storage import Storage

CONFIG_FILE = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    """Load config.yaml and expand ${VAR} references against the environment."""
    load_dotenv(Path(__file__).parent / ".env")
    with open(CONFIG_FILE) as f:
        cfg = yaml.safe_load(f) or {}

    # Expand ${VAR} in source URLs so secrets stay in .env, not in the repo.
    for source in cfg.get("sources", []):
        if isinstance(source.get("url"), str):
            source["url"] = os.path.expandvars(source["url"])
    return cfg


def run_pipeline():
    print("\n=== Source Monitor Pipeline ===")
    config = load_config()

    sources  = config.get("sources", [])
    keywords = config.get("keywords", [])
    output   = config.get("output", {})

    storage = Storage(output.get("data_file", "items.json"))
    data    = storage.load()
    existing_urls = {item["url"] for item in data["items"]}

    # Backfill AI score/summary on items saved before AI analysis was introduced.
    backfilled = 0
    for item in data["items"]:
        if "newsworthiness_score" not in item:
            result = analyze_item(item.get("title", ""), item.get("summary", ""))
            item["newsworthiness_score"] = result["score"]
            item["score_reason"]         = result["reason"]
            item["ai_summary"]           = result["summary"]
            backfilled += 1
        item.setdefault("user_rating", "")
        item.setdefault("score_reason", "")
        item.setdefault("ai_summary", "")
    if backfilled:
        print(f"Backfilled AI score + summary on {backfilled} existing items.")

    # Fetch from all sources
    all_items = []
    for source in sources:
        print(f"\nFetching: {source['name']}")
        src_type = source.get("type")
        if src_type == "rss":
            items = fetch_rss(source)
        else:
            print(f"  Unsupported type '{src_type}' (RSS only), skipping.")
            continue
        all_items.extend(items)

    print(f"\nTotal fetched: {len(all_items)}")

    # Keyword filter
    if keywords:
        all_items = keyword_filter(all_items, keywords)
        print(f"After keyword filter ({', '.join(keywords)}): {len(all_items)}")

    # Deduplicate, then score + summarize each new item with the AI analyzer.
    new_items = [i for i in all_items if i["url"] not in existing_urls]
    for item in new_items:
        result = analyze_item(item.get("title", ""), item.get("summary", ""))
        item["newsworthiness_score"] = result["score"]
        item["score_reason"]         = result["reason"]
        item["ai_summary"]           = result["summary"]
        item["user_rating"]          = ""

    # Persist only if the stored data actually changed.
    if new_items or backfilled:
        data["items"] = new_items + data["items"]
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        storage.write(data)
    print(f"New items saved: {len(new_items)}")

    # Export from the in-memory snapshot — no extra disk read.
    print()
    if output.get("xlsx"):
        export_xlsx(data["items"], output.get("xlsx_file", "report.xlsx"))
    if output.get("html"):
        export_html(data["items"], output.get("html_dir", "site"))

    print("\n=== Done ===\n")


if __name__ == "__main__":
    run_pipeline()
