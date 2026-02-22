#!/bin/bash
# macOS double-click launcher for Source Monitor.
# Place this file anywhere — it always finds the project directory.

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

VENV_PYTHON="${DIR}/venv/bin/python"

if [ -f "$VENV_PYTHON" ]; then
    "$VENV_PYTHON" launch.py
else
    python3 launch.py
fi
