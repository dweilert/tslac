#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from urllib.parse import quote

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
PY = sys.executable


def wait_for_health(base: str, timeout_s: float = 10.0) -> None:
    t0 = time.time()
    last_err = None
    while time.time() - t0 < timeout_s:
        try:
            r = requests.get(base + "/healthz", timeout=1.5)
            if r.status_code == 200:
                return
        except Exception as e:
            last_err = e
        time.sleep(0.2)
    raise RuntimeError(f"Server did not become healthy at {base}/healthz. Last error: {last_err}")


def get_doc_id_sample() -> str | None:
    # Best-effort: try importing your doc_store and reading one id
    try:
        sys.path.insert(0, REPO)
        from doc_store import load_doc_candidates  # type: ignore

        docs = load_doc_candidates()
        for d in docs or []:
            if isinstance(d, dict) and d.get("id"):
                return str(d["id"])
    except Exception:
        return None
    return None


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

        # Optional doc curate check (only if we can find a doc_id)
        doc_id = get_doc_id_sample()
        if doc_id:
            checks.append(("/curate_doc?doc_id=" + quote(doc_id, safe=""), 200, None))

        # Optional curate index check: only if candidates file exists and idx 0 works in your environment.
        # This can fail if HTTPS is blocked on your network, so we keep it optional.
        if os.environ.get("SMOKE_TRY_CURATE", "0") == "1":
            checks.append(("/curate/0", 200, None))

        for path, want_status, must_contain in checks:
            r = requests.get(base + path, timeout=15)
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
