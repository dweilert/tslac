from __future__ import annotations

import re

import pytest
import requests


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


@pytest.mark.integration
def test_curate_by_id(server_base_url: str) -> None:
    """
    Integration test: may depend on external fetching / candidate availability.
    Excluded by default (see pytest.ini).

    Strategy:
      - trigger /refresh (redirect expected)
      - load /
      - extract first /curate?id=... link
      - fetch that curate page
    """
    # Refresh so candidates are likely present.
    r = requests.get(server_base_url + "/refresh", timeout=60, allow_redirects=False)
    assert r.status_code in (301, 302, 303)

    main = requests.get(server_base_url + "/", timeout=30)
    assert main.status_code == 200
    html = main.text

    m = re.search(r'href="/curate\?id=([^"&]+)', html)
    assert m, "Did not find any /curate?id=... link on main page after refresh"

    cid = m.group(1)
    curate = requests.get(server_base_url + f"/curate?id={cid}", timeout=60)
    assert curate.status_code == 200
    assert "<html" in curate.text.lower()


def test_refresh_redirect(server_base_url: str) -> None:
    r = requests.get(
        server_base_url + "/refresh",
        timeout=30,
        allow_redirects=False,
    )
    assert r.status_code in (301, 302, 303)
    assert r.headers.get("Location", "").startswith("/?status=")
