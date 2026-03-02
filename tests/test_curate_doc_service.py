from __future__ import annotations

import services.curate_doc_service as svc


def test_build_view_by_index_happy_path():
    view = svc.build_view_by_index(
        0,
        load_docs=lambda: [{"id": "doc1", "summary": "orig"}],
        load_cur=lambda: {
            "doc1": {
                "final_blurb": "edited",
                "excerpts": ["E1"],
                "selected_image": "https://img.example/a.jpg",
                "image_crops": {"https://img.example/a.jpg": {"ix": 1, "iy": 2, "iw": 3, "ih": 4}},
            }
        },
    )

    assert view.idx == 0
    assert view.total == 1
    assert view.doc["id"] == "doc1"
    assert view.final_blurb == "edited"
    assert view.excerpts == ["E1"]
    assert view.selected_image == "https://img.example/a.jpg"
    assert view.crops == {"https://img.example/a.jpg": {"ix": 1, "iy": 2, "iw": 3, "ih": 4}}


def test_build_view_by_doc_id_finds_doc():
    view = svc.build_view_by_doc_id(
        "doc1",
        load_docs=lambda: [{"id": "doc1"}, {"id": "doc2"}],
        load_cur=lambda: {"doc1": {"final_blurb": "B"}},
    )
    assert view.doc["id"] == "doc1"
    assert view.final_blurb == "B"


def test_save_blurb_calls_upsert():
    called = {}

    def fake_upsert(doc_id: str, final_blurb: str) -> None:
        called["args"] = (doc_id, final_blurb)

    svc.save_blurb(doc_id="doc1", final_blurb=" hello ", upsert=fake_upsert)
    assert called["args"] == ("doc1", "hello")
