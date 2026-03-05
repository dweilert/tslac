#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
PY = sys.executable


def wait_for_health(base: str, timeout_s: float = 10.0) -> None:
    t0 = time.time()
    last_err: Exception | None = None
    while time.time() - t0 < timeout_s:
        try:
            r = requests.get(base + "/healthz", timeout=1.5)
            if r.status_code == 200:
                return
        except Exception as e:
            last_err = e
        time.sleep(0.2)
    raise RuntimeError(f"Server did not become healthy at {base}/healthz. Last error: {last_err}")


def find_first_curate_id(base: str) -> str | None:
    """
    Fetch / and scrape the first /curate?id=... link.
    This keeps smoke tests aligned with the unified curate route.
    """
    r = requests.get(base + "/", timeout=20)
    if r.status_code != 200:
        return None
    m = re.search(r'href="/curate\?id=([^"&]+)', r.text)
    if not m:
        return None
    return m.group(1)


def main() -> int:
    port = int(os.environ.get("SMOKE_PORT", "5057"))
    base = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env["PORT"] = str(port)

    # Start server
    p = subprocess.Popen([PY, os.path.join(REPO, "run.py")], cwd=REPO, env=env)

    try:
        wait_for_health(base, timeout_s=12.0)

        # --- Smoke checks ---
        checks: list[tuple[str, int, str | None]] = [
            ("/", 200, None),
            ("/preview", 200, None),
            ("/watch", 200, None),
            ("/watch/status", 200, None),
        ]

        # Trigger refresh so candidates exist.
        r = requests.get(base + "/refresh", timeout=60, allow_redirects=False)
        if r.status_code not in (301, 302, 303):
            raise AssertionError(f"/refresh: expected redirect, got {r.status_code}")

        cid = find_first_curate_id(base)
        if cid:
            checks.append((f"/curate?id={cid}", 200, None))
        else:
            print("SMOKE: NOTE: no /curate?id=... link found on /; skipping curate check")

        for path, want_status, must_contain in checks:
            r = requests.get(base + path, timeout=30)
            if r.status_code != want_status:
                raise AssertionError(
                    f"{path}: expected {want_status}, got {r.status_code}\nBody: {r.text[:300]}"
                )
            if must_contain and must_contain not in r.text:
                raise AssertionError(f"{path}: response missing expected text: {must_contain}")

        print("SMOKE TESTS: OK")
        return 0

    except Exception as e:
        print(f"SMOKE TESTS: FAIL: {e}")
        return 2

    finally:
        # Stop server
        try:
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
