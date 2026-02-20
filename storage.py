"""
storage.py

JSON-based item storage with deduplication by URL.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


class Storage:
    def __init__(self, path: str):
        self.path = Path(path)

    def load(self) -> dict:
        if self.path.exists():
            with open(self.path) as f:
                return json.load(f)
        return {"items": [], "last_updated": None}

    def existing_urls(self) -> set:
        return {item["url"] for item in self.load()["items"]}

    def save(self, new_items: list[dict]):
        """Prepend new_items to stored items (newest first) and write to disk."""
        data = self.load()
        for item in reversed(new_items):   # preserve fetch order when inserting at front
            data["items"].insert(0, item)
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)
