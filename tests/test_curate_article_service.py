from __future__ import annotations

import services.curate_article_service as svc


def test_build_view_by_index_happy_path():
    view = svc.build_view_by_index(
        0,
        load_candidates=lambda: [{"url": "https://x", "title": "T"}],
        fetch_payload=lambda _url: {"title": "T", "html": "<p>x</p>", "images": ["i1"]},
        load_cur=lambda: {
            "https://x": {
                "final_blurb": "B",
                "excerpts": ["E1"],
                "selected_image": "IMG",
                "image_crops": {"img": {"ix": 1}},
            }
        },
    )

    assert view.idx == 0
    assert view.total == 1
    assert isinstance(view.candidate, dict)
    assert view.candidate["url"] == "https://x"
    assert view.cleaned["title"] == "T"
    assert view.final_blurb == "B"
    assert view.excerpts == ["E1"]
    assert view.selected_image == "IMG"
    assert view.crops == {"img": {"ix": 1}}


def test_select_image_rejects_non_http(monkeypatch):
    called = {}

    def fake_upsert(url: str, img_src: str) -> None:
        called["args"] = (url, img_src)

    monkeypatch.setattr(svc.curation_store, "upsert_curated_selected_image", fake_upsert)

    svc.select_image(url="https://x", img_src="file:///etc/passwd")
    assert "args" not in called  # should not write

    svc.select_image(url="https://x", img_src="https://img.example/a.jpg")
    assert called["args"] == ("web:https://x", "https://img.example/a.jpg")