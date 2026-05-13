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
        import fetchers.scraper   # noqa: F401


class ScoringTests(unittest.TestCase):
    def test_tiers(self):
        from scoring import score_newsworthiness
        self.assertEqual(score_newsworthiness({"title": "SEC charges firm with fraud"}), 5)
        self.assertEqual(score_newsworthiness({"title": "Class action lawsuit filed"}),  4)
        self.assertEqual(score_newsworthiness({"title": "Treasury announces new policy"}), 3)
        self.assertEqual(score_newsworthiness({"title": "CEO named to advisory board"}),  2)
        self.assertEqual(score_newsworthiness({"title": "Quiet day at the office"}),      1)

    def test_uses_summary_too(self):
        from scoring import score_newsworthiness
        item = {"title": "Update", "summary": "FBI announced an arrest today"}
        self.assertEqual(score_newsworthiness(item), 5)


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


class ScraperLinkTests(unittest.TestCase):
    def test_urljoin_handles_relative_and_absolute(self):
        from bs4 import BeautifulSoup
        from fetchers.scraper import _link

        for href, prefix, expected in [
            ("/news/1",            "https://example.com", "https://example.com/news/1"),
            ("https://abs/x",      "https://example.com", "https://abs/x"),
            ("relative/x",         "https://example.com", "https://example.com/relative/x"),
            ("",                   "https://example.com", ""),
        ]:
            soup = BeautifulSoup(f'<a href="{href}">x</a>', "html.parser")
            self.assertEqual(_link(soup, "a", prefix), expected, msg=f"{href=}")


if __name__ == "__main__":
    unittest.main()
