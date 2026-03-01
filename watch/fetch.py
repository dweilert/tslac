# watch/fetch.py
from __future__ import annotations

import re
from urllib.request import Request, urlopen

from config import HEADERS


def fetch(url: str, timeout_s: int) -> tuple[str, str]:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=timeout_s) as r:
        ct = (r.headers.get("Content-Type") or "").lower()
        raw = r.read()

    enc = "utf-8"
    m = re.search(r"charset=([a-z0-9_\-]+)", ct)
    if m:
        enc = m.group(1)

    try:
        return raw.decode(enc, errors="replace"), ct
    except Exception:
        return raw.decode("utf-8", errors="replace"), ct
