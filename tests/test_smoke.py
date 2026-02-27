from __future__ import annotations

import requests
import os
import pytest


def test_healthz(server_base_url: str) -> None:
    r = requests.get(server_base_url + "/healthz", timeout=5)
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_main_page(server_base_url: str) -> None:
    r = requests.get(server_base_url + "/", timeout=10)
    assert r.status_code == 200
    # Cheap signal that HTML returned
    assert "<html" in r.text.lower()


def test_preview(server_base_url: str) -> None:
    r = requests.get(server_base_url + "/preview", timeout=10)
    assert r.status_code == 200
    assert "<html" in r.text.lower()


def test_watch_status(server_base_url: str) -> None:
    r = requests.get(server_base_url + "/watch/status", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)

@pytest.mark.skipif(os.environ.get("TEST_TRY_CURATE", "0") != "1", reason="External fetch test")
def test_curate0(server_base_url: str) -> None:
    r = requests.get(server_base_url + "/curate/0", timeout=60)
    assert r.status_code == 200    

def test_refresh_redirect(server_base_url: str) -> None:
    r = requests.get(
        server_base_url + "/refresh",
        timeout=30,
        allow_redirects=False,
    )

    assert r.status_code in (301, 302, 303)
    assert r.headers.get("Location", "").startswith("/?status=")    