from __future__ import annotations

from dataclasses import dataclass

import pytest

import services.api_service as svc
from web.errors import BadRequestError


@dataclass
class _Res:
    url: str = "https://x"
    title: str = "T"
    published_date: str = "2026-01-01"
    date_confidence: str = "high"
    clean_html: str = "<p>x</p>"
    text_plain: str = "plain"
    images: list[str] = None  # type: ignore[assignment]
    extraction_quality: str = "ok"


def test_clean_article_payload_calls_cleaner(monkeypatch):
    monkeypatch.setattr(svc.cleaner, "clean_article", lambda _url: _Res(images=["i1"]))

    payload = svc.clean_article_payload(url="https://example.com/a")

    assert payload["url"] == "https://x"
    assert payload["title"] == "T"
    assert payload["images"] == ["i1"]


def test_clean_article_payload_requires_url():
    with pytest.raises(BadRequestError):
        svc.clean_article_payload(url="")
