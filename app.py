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
from flask import Flask, flash, redirect, render_template, request, url_for, Response

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
    cfg = load_config()
    data_file = Path(__file__).parent / cfg.get("output", {}).get("data_file", "items.json")
    if not data_file.exists():
        flash("No data file found. Run the pipeline first.", "error")
        return redirect(url_for("index"))

    with open(data_file) as f:
        items = json.load(f).get("items", [])

    fields = ["source", "title", "url", "published", "summary", "created_at"]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(items)

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=source-monitor.csv"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
