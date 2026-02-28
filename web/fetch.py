from __future__ import annotations

from dataclasses import dataclass

import requests

DEFAULT_HEADERS = {
    "User-Agent": "tslac-newsletter-helper/1.0 (+local)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


@dataclass(frozen=True)
class FetchResult:
    url: str  # final URL after redirects
    text: str  # decoded response text
    status_code: int


class FetchError(RuntimeError):
    pass


def fetch_html(
    url: str,
    *,
    timeout_s: float = 15.0,
    headers: dict[str, str] | None = None,
) -> FetchResult:
    h = dict(DEFAULT_HEADERS)
    if headers:
        h.update(headers)

    try:
        resp = requests.get(url, headers=h, timeout=timeout_s)
        resp.raise_for_status()
        # requests chooses encoding; keep resp.text (decoded)
        return FetchResult(url=resp.url, text=resp.text, status_code=resp.status_code)
    except requests.RequestException as e:
        raise FetchError(f"Failed to fetch {url}: {e}") from e
