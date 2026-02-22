"""
app.py

Flask web UI for the source-monitor pipeline.
Run: python app.py  →  http://localhost:5001
"""

import csv
import io
import json
import subprocess
import sys
from pathlib import Path

import yaml
from flask import Flask, flash, redirect, render_template, render_template_string, request, url_for, Response

app = Flask(__name__)
app.secret_key = "source-monitor-secret"

CONFIG_FILE  = Path(__file__).parent / "config.yaml"
PIPELINE_LOG = Path(__file__).parent / "pipeline.log"
LOG_TAIL     = 200  # max lines to show in the UI


def read_pipeline_log() -> str | None:
    if not PIPELINE_LOG.exists():
        return None
    lines = PIPELINE_LOG.read_text().splitlines()
    return "\n".join(lines[-LOG_TAIL:])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f) or {}


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def load_items(source_name: str | None = None) -> list[dict]:
    cfg = load_config()
    data_file = Path(__file__).parent / cfg.get("output", {}).get("data_file", "items.json")
    if not data_file.exists():
        return []
    items = json.loads(data_file.read_text()).get("items", [])
    if source_name:
        items = [i for i in items if i.get("source") == source_name]
    return items


def make_csv_response(items: list[dict], filename: str) -> Response:
    fields = ["source", "title", "url", "published", "summary", "created_at"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(items)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    cfg = load_config()
    return render_template(
        "index.html",
        sources=cfg.get("sources", []),
        keywords=cfg.get("keywords", []),
        log=None,
        log_error=None,
        pipeline_log=read_pipeline_log(),
    )


@app.route("/keywords/save", methods=["POST"])
def keywords_save():
    raw = request.form.get("keywords", "")
    keywords = [k.strip() for k in raw.split(",") if k.strip()]
    cfg = load_config()
    cfg["keywords"] = keywords
    save_config(cfg)
    flash("Keywords saved.", "success")
    return redirect(url_for("index"))


@app.route("/source/add", methods=["POST"])
def source_add():
    src_type = request.form.get("type", "rss")
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()

    if not name or not url:
        flash("Name and URL are required.", "error")
        return redirect(url_for("index"))

    source: dict = {"name": name, "type": src_type, "url": url}

    if src_type == "scrape":
        selectors: dict = {}
        for field in ("items", "title", "link", "summary", "date", "date_attr", "link_prefix"):
            val = request.form.get(f"sel_{field}", "").strip()
            if val:
                selectors[field] = val
        if selectors:
            source["selectors"] = selectors

    cfg = load_config()
    cfg.setdefault("sources", []).append(source)
    save_config(cfg)
    flash(f"Source '{name}' added.", "success")
    return redirect(url_for("index"))


@app.route("/source/delete/<int:idx>", methods=["POST"])
def source_delete(idx: int):
    cfg = load_config()
    sources = cfg.get("sources", [])
    if 0 <= idx < len(sources):
        removed = sources.pop(idx)
        cfg["sources"] = sources
        save_config(cfg)
        flash(f"Source '{removed.get('name', idx)}' removed.", "success")
    else:
        flash("Invalid source index.", "error")
    return redirect(url_for("index"))


@app.route("/run", methods=["POST"])
def run_pipeline():
    pipeline = Path(__file__).parent / "pipeline.py"
    result = subprocess.run(
        [sys.executable, str(pipeline)],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent),
    )
    # Append this run's output to pipeline.log (same as cron does)
    with open(PIPELINE_LOG, "a") as f:
        if result.stdout:
            f.write(result.stdout)
        if result.stderr:
            f.write(result.stderr)

    cfg = load_config()
    log_error = None
    if result.returncode != 0:
        log_error = result.stderr or "(no stderr)"
    return render_template(
        "index.html",
        sources=cfg.get("sources", []),
        keywords=cfg.get("keywords", []),
        log=result.stdout or "(no output)",
        log_error=log_error,
        pipeline_log=read_pipeline_log(),
    )


@app.route("/download/csv")
def download_csv():
    items = load_items()
    if not items:
        flash("No data found. Run the pipeline first.", "error")
        return redirect(url_for("index"))
    return make_csv_response(items, "source-monitor.csv")


@app.route("/download/csv/<path:source_name>")
def download_csv_source(source_name: str):
    items = load_items(source_name)
    if not items:
        flash(f"No data found for '{source_name}'. Run the pipeline first.", "error")
        return redirect(url_for("index"))
    filename = source_name.lower().replace(" ", "-") + ".csv"
    return make_csv_response(items, filename)


_PREVIEW_TEMPLATE = """
<table style="width:100%;border-collapse:collapse;font-size:.8rem;">
  <thead>
    <tr>
      <th style="text-align:left;padding:6px 8px;border-bottom:1px solid #d5dde8;color:#607d8b;font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;">Title</th>
      <th style="text-align:left;padding:6px 8px;border-bottom:1px solid #d5dde8;color:#607d8b;font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;">Published</th>
      <th style="text-align:left;padding:6px 8px;border-bottom:1px solid #d5dde8;color:#607d8b;font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;">Summary</th>
    </tr>
  </thead>
  <tbody>
    {% for item in items %}
    <tr>
      <td style="padding:6px 8px;border-bottom:1px solid #f0f4f8;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
        <a href="{{ item.url }}" target="_blank" style="color:#1F4E79;text-decoration:none;">{{ item.title or '—' }}</a>
      </td>
      <td style="padding:6px 8px;border-bottom:1px solid #f0f4f8;white-space:nowrap;color:#607d8b;">{{ item.published or '—' }}</td>
      <td style="padding:6px 8px;border-bottom:1px solid #f0f4f8;color:#37474f;max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ item.summary or '—' }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% if total > 5 %}
<p style="font-size:.75rem;color:#90a4ae;margin-top:6px;">Showing 5 of {{ total }} items. Download CSV for full data.</p>
{% endif %}
{% if not items %}
<p style="color:#90a4ae;font-size:.82rem;">No data yet for this source — run the pipeline first.</p>
{% endif %}
"""

@app.route("/source/preview/<int:idx>")
def source_preview(idx: int):
    cfg = load_config()
    sources = cfg.get("sources", [])
    if not 0 <= idx < len(sources):
        return "<p style='color:#dc3545;font-size:.82rem;'>Invalid source index.</p>", 404
    source_name = sources[idx]["name"]
    all_items = load_items(source_name)
    return render_template_string(
        _PREVIEW_TEMPLATE,
        items=all_items[:5],
        total=len(all_items),
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
