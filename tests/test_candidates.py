from __future__ import annotations

from dataclasses import dataclass

import services.candidates_service as svc


@dataclass
class _Cand:
    url: str


def test_refresh_candidates_persists_candidates(monkeypatch):
    saved_candidates = {}

    def fake_save_candidates_json(_path, candidates):
        saved_candidates["value"] = list(candidates)

    def fake_collect_candidates(_homepage, rules, today):
        cands = [_Cand("https://new.example/1")]
        return cands, []

    def fake_load_doc_candidates():
        return [{"id": "doc1"}]

    monkeypatch.setattr(svc, "load_latest_results", lambda: {"results": []})
    monkeypatch.setattr(svc, "save_candidates_json", fake_save_candidates_json)
    monkeypatch.setattr(svc, "collect_candidates", fake_collect_candidates)

    res = svc.refresh_candidates(load_docs_fn=fake_load_doc_candidates)

    assert res.doc_count == 1
    assert res.candidate_count == 2  # 1 web + 1 doc
    assert res.error_count == 0
    assert [c.url for c in saved_candidates["value"]] == [
        "https://new.example/1",
        "gdrive:doc1",
    ]


def test_save_picks_calls_save_selected(monkeypatch):
    called = {}

    def fake_save_selected(subject, intro, urls):
        called["args"] = (subject, intro, list(urls))

    monkeypatch.setattr(svc, "save_selected", fake_save_selected)

    n = svc.save_picks(
        subject="S",
        intro="I",
        picked_urls=["u1", "u2"],
    )

    assert n == 2
    assert called["args"] == ("S", "I", ["u1", "u2"])
