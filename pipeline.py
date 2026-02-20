"""
pipeline.py

Generalized source monitoring pipeline.
Reads config.yaml, fetches each source, applies keyword filter, and exports.

Run:  python pipeline.py
"""

from pathlib import Path

import yaml

from exporters.html import export_html
from exporters.xlsx import export_xlsx
from fetchers.rss import fetch_rss
from fetchers.scraper import fetch_scrape
from filters import keyword_filter
from storage import Storage

CONFIG_FILE = Path("config.yaml")


def load_config() -> dict:
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def run_pipeline():
    print("\n=== Source Monitor Pipeline ===")
    config = load_config()

    sources  = config.get("sources", [])
    keywords = config.get("keywords", [])
    output   = config.get("output", {})

    storage      = Storage(output.get("data_file", "items.json"))
    existing_urls = storage.existing_urls()

    # Fetch from all sources
    all_items = []
    for source in sources:
        print(f"\nFetching: {source['name']}")
        src_type = source.get("type")
        if src_type == "rss":
            items = fetch_rss(source)
        elif src_type == "scrape":
            items = fetch_scrape(source)
        else:
            print(f"  Unknown type '{src_type}', skipping.")
            continue
        all_items.extend(items)

    print(f"\nTotal fetched: {len(all_items)}")

    # Keyword filter
    if keywords:
        all_items = keyword_filter(all_items, keywords)
        print(f"After keyword filter ({', '.join(keywords)}): {len(all_items)}")

    # Deduplicate and persist
    new_items = [i for i in all_items if i["url"] not in existing_urls]
    storage.save(new_items)
    print(f"New items saved: {len(new_items)}")

    # Export
    all_stored = storage.load()["items"]
    print()
    if output.get("xlsx"):
        export_xlsx(all_stored, output.get("xlsx_file", "report.xlsx"))
    if output.get("html"):
        export_html(all_stored, output.get("html_dir", "site"))

    print("\n=== Done ===\n")


if __name__ == "__main__":
    run_pipeline()
