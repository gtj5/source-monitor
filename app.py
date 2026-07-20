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
from collections import deque
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
    # Tail the file without loading the whole thing into memory.
    with open(PIPELINE_LOG) as f:
        return "".join(deque(f, maxlen=LOG_TAIL)).rstrip("\n")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f) or {}


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def load_items(source_name: str | None = None, cfg: dict | None = None) -> list[dict]:
    if cfg is None:
        cfg = load_config()
    data_file = Path(__file__).parent / cfg.get("output", {}).get("data_file", "items.json")
    if not data_file.exists():
        return []
    items = json.loads(data_file.read_text()).get("items", [])
    if source_name:
        items = [i for i in items if i.get("source") == source_name]
    return items


def make_csv_response(items: list[dict], filename: str) -> Response:
    # DictWriter blanks any field an item is missing, so stored scores/summaries
    # flow straight through — no per-request scoring needed.
    fields = ["source", "title", "url", "published", "summary", "ai_summary",
              "newsworthiness_score", "score_reason", "user_rating", "created_at"]
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
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()

    if not name or not url:
        flash("Name and URL are required.", "error")
        return redirect(url_for("index"))

    # RSS/Atom feeds only — the HTML scraper was removed.
    source: dict = {"name": name, "type": "rss", "url": url}

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


PIPELINE_TIMEOUT = 180  # seconds — caps the worst case if a feed hangs


@app.route("/run", methods=["POST"])
def run_pipeline():
    pipeline = Path(__file__).parent / "pipeline.py"
    stdout = ""
    log_error = None
    try:
        result = subprocess.run(
            [sys.executable, str(pipeline)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent),
            timeout=PIPELINE_TIMEOUT,
        )
        stdout = result.stdout
        if result.returncode != 0:
            log_error = result.stderr or "(no stderr)"
    except subprocess.TimeoutExpired as e:
        stdout    = (e.stdout or "") if isinstance(e.stdout, str) else ""
        log_error = f"Pipeline timed out after {PIPELINE_TIMEOUT}s and was killed."

    # Append this run's output to pipeline.log (same as cron does)
    with open(PIPELINE_LOG, "a") as f:
        if stdout:
            f.write(stdout)
        if log_error:
            f.write(log_error)

    cfg = load_config()
    return render_template(
        "index.html",
        sources=cfg.get("sources", []),
        keywords=cfg.get("keywords", []),
        log=stdout or "(no output)",
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


_SCORE_COLORS = {
    5: ("#FEF2F2", "#DC2626", "5 — Break"),
    4: ("#FFF7ED", "#EA580C", "4 — High"),
    3: ("#FEFCE8", "#CA8A04", "3 — Moderate"),
    2: ("#F0FDF4", "#16A34A", "2 — Low"),
    1: ("#F8FAFC", "#94A3B8", "1 — Routine"),
}

_PREVIEW_TEMPLATE = """
{% if items %}
<table style="width:100%;border-collapse:collapse;font-size:.8rem;">
  <thead>
    <tr>
      <th style="text-align:left;padding:4px 10px 8px;border-bottom:1px solid #E2E8F0;color:#94A3B8;font-size:.65rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;">Score</th>
      <th style="text-align:left;padding:4px 10px 8px;border-bottom:1px solid #E2E8F0;color:#94A3B8;font-size:.65rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;">Title</th>
      <th style="text-align:left;padding:4px 10px 8px;border-bottom:1px solid #E2E8F0;color:#94A3B8;font-size:.65rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;">Published</th>
      <th style="text-align:left;padding:4px 10px 8px;border-bottom:1px solid #E2E8F0;color:#94A3B8;font-size:.65rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;">Summary</th>
    </tr>
  </thead>
  <tbody>
    {% for item in items %}
    {% set score = item.get('newsworthiness_score') %}
    <tr>
      <td style="padding:9px 10px;border-bottom:1px solid #F8FAFC;white-space:nowrap;">
        {% if score %}
        {% set colors = score_colors.get(score, score_colors[1]) %}
        <span style="display:inline-block;padding:2px 8px;border-radius:20px;font-size:.7rem;font-weight:700;background:{{ colors[0] }};color:{{ colors[1] }};">{{ colors[2] }}</span>
        {% else %}
        <span style="display:inline-block;padding:2px 8px;border-radius:20px;font-size:.7rem;font-weight:700;background:#F1F5F9;color:#94A3B8;">—</span>
        {% endif %}
      </td>
      <td style="padding:9px 10px;border-bottom:1px solid #F8FAFC;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
        <a href="{{ item.url }}" target="_blank" style="color:#1D4ED8;text-decoration:none;font-weight:600;">{{ item.title or '—' }}</a>
      </td>
      <td style="padding:9px 10px;border-bottom:1px solid #F8FAFC;white-space:nowrap;color:#94A3B8;">{{ item.published or '—' }}</td>
      <td style="padding:9px 10px;border-bottom:1px solid #F8FAFC;color:#475569;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ item.ai_summary or item.summary or '—' }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% if total > 5 %}
<p style="font-size:.72rem;color:#94A3B8;margin-top:8px;">Showing 5 of {{ total }} items &mdash; download the CSV for the full list.</p>
{% endif %}
{% else %}
<p style="color:#94A3B8;font-size:.82rem;">No data for this source yet &mdash; run the pipeline first.</p>
{% endif %}
"""

@app.route("/source/preview/<int:idx>")
def source_preview(idx: int):
    cfg = load_config()
    sources = cfg.get("sources", [])
    if not 0 <= idx < len(sources):
        return "<p style='color:#dc3545;font-size:.82rem;'>Invalid source index.</p>", 404
    source_name = sources[idx]["name"]
    all_items = load_items(source_name, cfg=cfg)
    return render_template_string(
        _PREVIEW_TEMPLATE,
        items=all_items[:5],
        total=len(all_items),
        score_colors=_SCORE_COLORS,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
