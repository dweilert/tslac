from __future__ import annotations

from dataclasses import dataclass

import services.candidates_service as svc


@dataclass
class _Cand:
    url: str


def test_refresh_candidates_persists_candidates_and_seen(monkeypatch):
    seen_in = {"https://old.example/a"}

    def fake_load_seen(_path):
        return set(seen_in)

    saved_seen = {}

    def fake_save_seen(_path, seen):
        saved_seen["value"] = set(seen)

    saved_candidates = {}

    def fake_save_candidates_json(_path, candidates):
        saved_candidates["value"] = list(candidates)

    def fake_collect_candidates(_homepage, rules, today, seen_urls):
        cands = [_Cand("https://new.example/1")]
        return cands, []

    def fake_load_doc_candidates():
        return [{"id": "doc1"}]

    # NEW: make watch merge deterministic (no extra candidates)
    monkeypatch.setattr(svc, "load_latest_results", lambda: {"results": []})

    monkeypatch.setattr(svc, "load_seen", fake_load_seen)
    monkeypatch.setattr(svc, "save_seen", fake_save_seen)
    monkeypatch.setattr(svc, "save_candidates_json", fake_save_candidates_json)
    monkeypatch.setattr(svc, "collect_candidates", fake_collect_candidates)
    monkeypatch.setattr(svc, "load_doc_candidates", fake_load_doc_candidates)

    res = svc.refresh_candidates()

    assert res.doc_count == 1
    assert res.candidate_count == 2  # 1 web + 1 doc
    assert res.error_count == 0


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