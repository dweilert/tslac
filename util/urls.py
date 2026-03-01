from __future__ import annotations

from urllib.parse import urlparse


def norm_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return u
    p = urlparse(u)
    return p._replace(fragment="").geturl()
