from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class Request:
    method: str
    raw_path: str
    path: str
    query: dict[str, list[str]]
    headers: Any  # http.client.HTTPMessage
    body: bytes

    @property
    def query_first(self) -> dict[str, str]:
        """Convenience: first value for each query key."""
        return {k: (v[0] if v else "") for k, v in (self.query or {}).items()}


def build_request(method: str, raw_path: str, headers: Any, body: bytes) -> Request:
    p = urlparse(raw_path)
    q = parse_qs(p.query or "", keep_blank_values=True)
    return Request(
        method=method.upper(),
        raw_path=raw_path,
        path=p.path or "/",
        query=q,
        headers=headers,
        body=body or b"",
    )