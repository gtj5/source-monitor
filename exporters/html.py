"""
exporters/html.py

Export items to a simple static HTML site (site/index.html).
"""

import html as html_lib
from datetime import datetime, timezone
from pathlib import Path

_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Source Monitor</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 920px; margin: 2rem auto; padding: 0 1rem;
      color: #222; background: #fff;
    }}
    h1 {{ font-size: 1.5rem; color: #1F4E79; border-bottom: 2px solid #1F4E79; padding-bottom: .4rem; }}
    .meta {{ font-size: .82rem; color: #666; margin-bottom: 1rem; }}
    .search-wrap {{ margin-bottom: 1.5rem; position: relative; }}
    #search {{
      width: 100%; padding: .55rem .55rem .55rem 2.2rem;
      font-size: .95rem; border: 1.5px solid #c5d3e0; border-radius: 6px;
      outline: none; background: #f7f9fc;
    }}
    #search:focus {{ border-color: #1F4E79; background: #fff; }}
    .search-icon {{
      position: absolute; left: .65rem; top: 50%; transform: translateY(-50%);
      color: #8fa8bf; pointer-events: none; font-size: 1rem;
    }}
    #result-count {{ font-size: .8rem; color: #888; margin-top: .4rem; }}
    .no-results {{ color: #888; font-size: .95rem; padding: 1rem 0; }}
    .item {{
      border-left: 3px solid #1F4E79; padding: .65rem 1rem;
      margin-bottom: .9rem; background: #f7f9fc; border-radius: 0 4px 4px 0;
    }}
    .item h2 {{ font-size: 1rem; margin: 0 0 .2rem; display: flex; align-items: baseline; gap: .45rem; flex-wrap: wrap; }}
    .badge {{
      flex-shrink: 0; font-size: .68rem; background: #1F4E79; color: #fff;
      border-radius: 3px; padding: 1px 6px; text-transform: uppercase; letter-spacing: .04em;
    }}
    .item h2 a {{ color: #1a3d6b; text-decoration: none; }}
    .item h2 a:hover {{ text-decoration: underline; }}
    .date {{ font-size: .78rem; color: #888; }}
    .item p {{ margin: .35rem 0 0; font-size: .88rem; color: #444; line-height: 1.5; }}
  </style>
</head>
<body>
  <h1>Source Monitor</h1>
  <p class="meta">Last updated: {last_updated} &mdash; {count} items</p>
  <div class="search-wrap">
    <span class="search-icon">&#128269;</span>
    <input id="search" type="search" placeholder="Filter by keyword, source, title…" autocomplete="off">
    <div id="result-count"></div>
  </div>
  <div id="items-list">
    {items_html}
  </div>
  <p class="no-results" id="no-results" style="display:none">No items match your search.</p>
  <script>
    const input   = document.getElementById('search');
    const list    = document.getElementById('items-list');
    const counter = document.getElementById('result-count');
    const noRes   = document.getElementById('no-results');
    const items   = Array.from(list.querySelectorAll('.item'));

    function filter() {{
      const q = input.value.trim().toLowerCase();
      let visible = 0;
      items.forEach(el => {{
        const text = el.textContent.toLowerCase();
        const show = !q || text.includes(q);
        el.style.display = show ? '' : 'none';
        if (show) visible++;
      }});
      counter.textContent = q ? `${{visible}} of ${{items.length}} items` : '';
      noRes.style.display = (q && visible === 0) ? '' : 'none';
    }}

    input.addEventListener('input', filter);
  </script>
</body>
</html>
"""

_ITEM = """\
<div class="item">
  <h2>
    <span class="badge">{source}</span>
    <a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>
  </h2>
  <span class="date">{published}</span>
  <p>{summary}</p>
</div>
"""


def export_html(items: list[dict], output_dir: str):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    items_html = "".join(
        _ITEM.format(
            source=html_lib.escape(item.get("source", "")),
            url=html_lib.escape(item.get("url", "#")),
            title=html_lib.escape(item.get("title", "(no title)")),
            published=html_lib.escape(item.get("published", "")),
            summary=html_lib.escape(item.get("summary", "")),
        )
        for item in items
    )

    page = _PAGE.format(
        last_updated=last_updated,
        count=len(items),
        items_html=items_html,
    )

    index = out / "index.html"
    index.write_text(page, encoding="utf-8")
    print(f"  HTML → {index}")
