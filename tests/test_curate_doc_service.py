from __future__ import annotations

import services.curate_doc_service as svc


def test_build_view_by_index(monkeypatch):
    monkeypatch.setattr(svc, "load_doc_candidates", lambda: [{"id": "doc1", "title": "X"}])

    monkeypatch.setattr(svc, "load_curation", lambda: {})
    monkeypatch.setattr(svc, "get_curated_blurb", lambda cur, doc_id: "B")
    monkeypatch.setattr(svc, "get_curated_excerpts", lambda cur, doc_id: ["E1"])
    monkeypatch.setattr(svc, "get_curated_selected_image", lambda cur, doc_id: "IMG")
    monkeypatch.setattr(svc, "get_curated_image_crops", lambda cur, doc_id: {"img": {"ix": 1}})

    view = svc.build_view_by_index(0)

    assert view.idx == 0
    assert view.total == 1
    assert view.doc["id"] == "doc1"
    assert view.final_blurb == "B"
    assert view.excerpts == ["E1"]
    assert view.selected_image == "IMG"
    assert view.crops == {"img": {"ix": 1}}


def test_select_image_rejects_non_http(monkeypatch):
    called = {}

    def fake_upsert(doc_id, img_src):
        called["args"] = (doc_id, img_src)

    monkeypatch.setattr(svc, "upsert_curated_selected_image", fake_upsert)

    svc.select_image(doc_id="doc1", img_src="file:///etc/passwd")
    assert "args" not in called

    svc.select_image(doc_id="doc1", img_src="https://img.example/a.jpg")
    assert called["args"] == ("doc1", "https://img.example/a.jpg")


def test_load_doc_for_curate_overrides_summary_with_saved_blurb(monkeypatch):
    monkeypatch.setattr(svc, "load_doc_candidates", lambda: [{"id": "doc1", "summary": "orig"}])
    monkeypatch.setattr(svc, "load_curation", lambda: {})
    monkeypatch.setattr(svc, "get_curated_blurb", lambda cur, doc_id: "edited")

    model = svc.load_doc_for_curate(doc_id="doc1", status="X")

    assert model.doc["id"] == "doc1"
    assert model.doc["summary"] == "edited"
    assert model.status == "X"


def test_save_doc_blurb_calls_upsert(monkeypatch):
    called = {}

    def fake_upsert(doc_id, final_blurb):
        called["args"] = (doc_id, final_blurb)

    monkeypatch.setattr(svc, "upsert_curated_blurb", fake_upsert)

    svc.save_doc_blurb(doc_id="doc1", final_blurb=" hello ")
    assert called["args"] == ("doc1", "hello")
