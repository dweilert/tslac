from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from typing import Generator

import pytest
import requests


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PY = sys.executable


def _wait_for_health(base: str, timeout_s: float = 12.0) -> None:
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
    raise RuntimeError(f"Server not healthy at {base}/healthz. Last error: {last_err}")


@pytest.fixture(scope="session")
def server_base_url() -> Generator[str, None, None]:
    """
    Starts the app server once for the whole test session.
    Uses port 5055 by default (your preference), but can override:
      TEST_PORT=5057 pytest
    """
    port = int(os.environ.get("TEST_PORT", "5055"))
    base = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env["PORT"] = str(port)

    p = subprocess.Popen([PY, os.path.join(REPO, "run.py")], cwd=REPO, env=env)

    try:
        _wait_for_health(base)
        yield base
    finally:
        try:
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
        except Exception:
            pass