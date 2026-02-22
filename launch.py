"""
launch.py

Cross-platform launcher for Source Monitor.
Starts the Flask server and opens the UI in your default browser.

Usage:
    python launch.py
"""

import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

PORT    = 5001
PROJECT = Path(__file__).parent


def wait_for_server(port: int, timeout: int = 15) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://localhost:{port}", timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def kill_existing(port: int) -> None:
    """Best-effort kill of any process already on the port."""
    try:
        import socket
        s = socket.socket()
        s.settimeout(0.5)
        if s.connect_ex(("localhost", port)) == 0:
            s.close()
            # Port is occupied — try platform-specific kill
            if sys.platform == "win32":
                subprocess.call(
                    f"for /f \"tokens=5\" %a in ('netstat -aon ^| find \":{port}\"') do taskkill /F /PID %a",
                    shell=True,
                )
            else:
                subprocess.call(
                    f"lsof -ti :{port} | xargs kill -9 2>/dev/null",
                    shell=True,
                )
            time.sleep(0.5)
        else:
            s.close()
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n  Source Monitor")
    print(f"  Starting on http://localhost:{PORT} ...\n")

    kill_existing(PORT)

    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(PROJECT),
    )

    if wait_for_server(PORT):
        webbrowser.open(f"http://localhost:{PORT}")
        print(f"  Opened in browser.")
        print(f"  Press Ctrl+C to stop the server.\n")
    else:
        print("  Server did not start in time. Check app.py for errors.")
        proc.terminate()
        sys.exit(1)

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        print("\n  Server stopped.\n")
