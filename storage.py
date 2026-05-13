"""
storage.py

JSON-based item storage. Callers load once, mutate the in-memory dict,
and write only when something actually changed.
"""

import json
from pathlib import Path


class Storage:
    def __init__(self, path: str):
        self.path = Path(path)

    def load(self) -> dict:
        if self.path.exists():
            with open(self.path) as f:
                return json.load(f)
        return {"items": [], "last_updated": None}

    def write(self, data: dict) -> None:
        """Dump the full data dict to disk. Caller decides when to write."""
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)
