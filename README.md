# Source Monitor

A small, self-hosted tool for journalists and analysts who want to keep tabs on
many sources at once. Point it at any mix of RSS feeds and web pages, give it a
list of keywords (or none), and it will fetch, filter, deduplicate, score, and
export everything it finds — on demand or on a cron schedule.

It runs as a single-user Flask app on your laptop. No accounts, no database,
no SaaS dependency.

---

## What it does

```
   config.yaml                       items.json
       │                                  ▲
       ▼                                  │
  ┌──────────┐   fetch   ┌──────────┐    write
  │ sources  │──────────▶│ pipeline │────────▶ report.xlsx
  └──────────┘           │          │
                         │ • filter │────────▶ site/index.html
                         │ • dedupe │
                         │ • score  │────────▶ CSV (on demand,
                         └──────────┘          via the web UI)
```

For every pipeline run:

1. **Fetch** each configured source. Two fetcher types:
   - **RSS** — any RSS or Atom feed (`fetchers/rss.py`, uses `feedparser`).
   - **Scrape** — any HTML page described by CSS selectors
     (`fetchers/scraper.py`, uses `requests` + `beautifulsoup4`).
2. **Filter** by keyword (`filters.py`). An item is kept if at least one
   keyword appears in its title or summary, case-insensitive. Leave keywords
   empty to keep everything.
3. **Deduplicate** against everything already in `items.json` — items are keyed
   by URL, so re-running the pipeline never produces duplicates.
4. **Score** each new item 1–5 for newsworthiness based on a tiered keyword
   list (`scoring.py`). 5 = break / urgent, 1 = routine. Items also carry a
   `user_rating` field that the UI leaves writable for human review.
5. **Persist** the new items to `items.json` (newest-first). On no-op runs
   the file is left untouched — `last_updated` only changes when the data
   actually does.
6. **Export** the full collection to `report.xlsx` (`exporters/xlsx.py`) and
   a static `site/index.html` with a live search box (`exporters/html.py`).
   CSV export is on-demand from the web UI.

---

## Quick start

```bash
git clone https://github.com/gtj5/source-monitor.git
cd source-monitor

python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env          # only needed if your sources use private keys

python launch.py              # opens http://localhost:5001 in your browser
```

`launch.py` is a cross-platform wrapper that starts the Flask app and opens
your browser. Equivalent shortcuts:

| Platform | File |
|---|---|
| macOS    | double-click `launch.command` |
| Windows  | double-click `launch.bat` |
| Linux    | `python launch.py` |

To run the pipeline once from the terminal without the UI:

```bash
python pipeline.py
```

---

## The web UI

Open `http://localhost:5001/` after `launch.py` and you get:

- **Sources** — add, remove, or preview each configured feed/page. Each row
  has a "Preview" button (shows the latest 5 items inline) and a "CSV"
  button (downloads just that source's items).
- **Keywords** — comma-separated list. Saved to `config.yaml` immediately;
  applies to the *next* run only (already-saved items aren't retroactively
  removed).
- **Run Pipeline** — runs `pipeline.py` as a subprocess with a 180-second
  timeout. stdout/stderr are shown on the page *and* appended to
  `pipeline.log` for the in-page log viewer.
- **Download All CSV** — every item ever saved, across all sources.

All UI state lives in `config.yaml` and `items.json` — nothing else. Delete
`items.json` and re-run the pipeline to start fresh.

---

## Configuring sources

Sources live in `config.yaml`. The default config has four:

```yaml
sources:
- name: SEC Press Releases
  type: rss
  url: https://www.sec.gov/news/pressreleases.rss

- name: SEC Open Meetings
  type: scrape
  url: https://www.sec.gov/news/upcoming-events
  selectors:
    items: li.usa-collection__item
    title: h3.usa-collection__heading a
    link:  h3.usa-collection__heading a
    link_prefix: https://www.sec.gov
    summary: div.usa-collection__description
    date: time
    date_attr: datetime
```

### RSS sources

Just `name`, `type: rss`, and `url`. That's it.

### Scrape sources

Add a `selectors:` block describing where each field lives on the page. All
fields except `items` are optional.

| Selector | Purpose |
|---|---|
| `items` | CSS selector for the repeating item container (e.g. `li.story`). **Required.** |
| `title` | Element whose text content is the item title. |
| `link` | Element whose `href` is the item URL. |
| `link_prefix` | Prepended to relative hrefs (`urljoin` semantics). |
| `summary` | Element whose text content is the summary. |
| `date` | Element containing the publication date. |
| `date_attr` | If set, reads this attribute (e.g. `datetime`) instead of the element's text. |

You can add scrape sources from the web UI; the form has fields for each
selector with hints.

### Secrets

URLs in `config.yaml` go through `os.path.expandvars`, so anything of the
form `${VAR_NAME}` is replaced with the corresponding environment variable
at pipeline-run time. Put the actual values in a `.env` file (gitignored).

Example: a private feed key.

```yaml
# config.yaml
url: https://example.com/private?key=${MY_FEED_KEY}
```

```ini
# .env
MY_FEED_KEY=actual-key-value
```

---

## Newsworthiness scoring

`scoring.py` assigns a 1–5 score by checking the item's title and summary
against four keyword tiers, top-down. The first tier that matches wins.

| Score | Tier | Examples |
|---|---|---|
| 5 | Break / urgent | `arrest`, `fraud`, `data breach`, `mass shooting`, `cyberattack` |
| 4 | High interest  | `lawsuit`, `subpoena`, `bankruptcy`, `whistleblower`, `antitrust` |
| 3 | Moderate       | `regulation`, `merger`, `interest rate`, `election`, `ruling` |
| 2 | Lower          | `appointed`, `conference`, `quarterly`, `survey` |
| 1 | Routine        | anything that didn't match the above |

The keyword lists are intentionally short and editable — open `scoring.py`
and tune them for your beat.

The `user_rating` column is a manual override slot: the pipeline never
writes to it after creating an item, so it's safe for you to fill in via the
CSV/XLSX exports.

---

## Outputs

| File | Written by | Format |
|---|---|---|
| `items.json` | Pipeline | Source of truth. Newest-first array; only rewritten when data actually changes. |
| `report.xlsx` | `exporters/xlsx.py` | All items, with `newsworthiness_score` and `user_rating` columns, URL hyperlinked. |
| `site/index.html` | `exporters/html.py` | Static page with live client-side search. RSS HTML is stripped from summaries before rendering. |
| CSV download | `app.py` (`/download/csv`) | Everything, or per-source. Generated on demand — no file on disk. |
| `pipeline.log` | Pipeline output, appended by the web UI on each `/run` | Shown in the in-page log viewer. Gitignored. |

---

## Scheduling

The pipeline is a regular CLI — schedule it however you like. On macOS/Linux,
a typical crontab entry to run every 4 hours and capture output:

```cron
0 */4 * * * cd /path/to/source-monitor && /path/to/venv/bin/python pipeline.py >> pipeline.log 2>&1
```

---

## Project layout

```
source-monitor/
├── pipeline.py           # CLI entrypoint: fetch → filter → score → save → export
├── app.py                # Flask web UI
├── launch.py             # Cross-platform "start the UI + open browser"
├── launch.command        # macOS double-click shortcut
├── launch.bat            # Windows double-click shortcut
├── config.yaml           # Sources, keywords, output paths
├── fetchers/
│   ├── rss.py            # feedparser-based RSS/Atom fetcher
│   └── scraper.py        # requests + bs4 CSS-selector scraper
├── exporters/
│   ├── xlsx.py           # openpyxl spreadsheet export
│   └── html.py           # Static HTML site with live search
├── filters.py            # keyword_filter()
├── scoring.py            # score_newsworthiness() + keyword tiers
├── storage.py            # JSON load/write (caller controls when)
├── templates/index.html  # Flask UI template
├── tests/test_smoke.py   # Network-free unit tests
└── .github/workflows/ci.yml  # Install deps, syntax-check, run tests on push/PR
```

---

## Development

```bash
python -m unittest discover -s tests -v
```

The tests cover module imports, scoring tiers, the keyword filter, the
storage round-trip, and `urljoin` behavior in the scraper. They don't hit
the network, so they run in a couple hundred milliseconds and are safe to
run in CI.

The same checks run on every push and pull request via
`.github/workflows/ci.yml`.

---

## Dependencies

All listed in `requirements.txt`:

- `flask` — web UI
- `feedparser` — RSS/Atom parsing
- `requests`, `beautifulsoup4` — HTML scraping
- `openpyxl` — XLSX export
- `pyyaml` — `config.yaml` parsing
- `python-dotenv` — `${VAR}` expansion in URLs

Python 3.11+ recommended (the type hints use 3.10+ syntax).
