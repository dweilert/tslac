from __future__ import annotations

from dataclasses import dataclass

import services.curate_article_service as svc


@dataclass
class _Cand:
    url: str


@dataclass
class _CleanResult:
    title: str = "T"
    published_date: str = "2026-01-01"
    date_confidence: str = "high"
    clean_html: str = "<p>x</p>"
    text_plain: str = "hello"
    images: list[str] = None  # type: ignore[assignment]
    extraction_quality: str = "ok"


def test_build_view_by_index_happy_path(monkeypatch):
    monkeypatch.setattr(svc, "load_candidates_file", lambda: [_Cand("https://x")])
    monkeypatch.setattr(svc.cleaner, "clean_article", lambda _url: _CleanResult(images=["i1"]))

    monkeypatch.setattr(svc, "load_curation", lambda: {})
    monkeypatch.setattr(svc, "get_curated_blurb", lambda cur, url: "B")
    monkeypatch.setattr(svc, "get_curated_excerpts", lambda cur, url: ["E1"])
    monkeypatch.setattr(svc, "get_curated_selected_image", lambda cur, url: "IMG")
    monkeypatch.setattr(svc, "get_curated_image_crops", lambda cur, url: {"img": {"ix": 1}})

    view = svc.build_view_by_index(0)

    assert view.idx == 0
    assert view.total == 1
    assert view.candidate.url == "https://x"
    assert view.cleaned["title"] == "T"
    assert view.final_blurb == "B"
    assert view.excerpts == ["E1"]
    assert view.selected_image == "IMG"
    assert view.crops == {"img": {"ix": 1}}


def test_select_image_rejects_non_http(monkeypatch):
    called = {}

    def fake_upsert(url, img_src):
        called["args"] = (url, img_src)

    monkeypatch.setattr(svc, "upsert_curated_selected_image", fake_upsert)

    svc.select_image(url="https://x", img_src="file:///etc/passwd")
    assert "args" not in called  # should not write

    svc.select_image(url="https://x", img_src="https://img.example/a.jpg")
    assert called["args"] == ("https://x", "https://img.example/a.jpg")
