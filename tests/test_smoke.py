"""Network-free smoke tests covering the bits most likely to regress."""

import sys
import tempfile
import unittest
from pathlib import Path

# Make the project root importable when running `python -m unittest` from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ImportTests(unittest.TestCase):
    def test_all_modules_import(self):
        import app                # noqa: F401
        import pipeline           # noqa: F401
        import storage            # noqa: F401
        import filters            # noqa: F401
        import scoring            # noqa: F401
        import exporters.html     # noqa: F401
        import exporters.xlsx     # noqa: F401
        import fetchers.rss       # noqa: F401


class ScoringTests(unittest.TestCase):
    """The scorer is AI-based; with no API key it must degrade, not crash."""

    def test_degrades_without_api_key(self):
        import os
        import scoring

        saved = os.environ.pop("ANTHROPIC_API_KEY", None)
        scoring._client = None
        try:
            result = scoring.analyze_item("SEC charges firm with fraud", "")
            self.assertIsNone(result["score"])
            self.assertEqual(result["reason"], "")
            self.assertEqual(result["summary"], "")
            # score_newsworthiness always returns an int for UI callers.
            self.assertEqual(scoring.score_newsworthiness({"title": "x"}), 1)
        finally:
            if saved is not None:
                os.environ["ANTHROPIC_API_KEY"] = saved
            scoring._client = None


class FilterTests(unittest.TestCase):
    def test_keyword_filter(self):
        from filters import keyword_filter
        items = [
            {"title": "Bitcoin rises",  "summary": ""},
            {"title": "Stocks fall",    "summary": "good news"},
        ]
        self.assertEqual(len(keyword_filter(items, ["bitcoin"])), 1)
        self.assertEqual(len(keyword_filter(items, [])),          2)
        self.assertEqual(len(keyword_filter(items, ["nope"])),    0)


class StorageTests(unittest.TestCase):
    def test_roundtrip(self):
        from storage import Storage
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            store = Storage(str(path))
            self.assertEqual(store.load(), {"items": [], "last_updated": None})
            data = {"items": [{"url": "https://x", "title": "t"}], "last_updated": "2026-05-12"}
            store.write(data)
            self.assertEqual(store.load(), data)


if __name__ == "__main__":
    unittest.main()
