from dataclasses import dataclass

import services.candidates_service as svc


@dataclass
class _Cand:
    url: str


def test_refresh_candidates_di(monkeypatch):
    monkeypatch.setattr(svc, "load_latest_results", lambda: {"results": []})

    saved_candidates = {}

    def save_candidates_fn(_path, candidates):
        saved_candidates["cands"] = list(candidates)

    def collect_fn(_homepage, _rules, _day):
        return [_Cand("https://new.example/1")], ["err"]

    def load_docs_fn():
        return [{"id": "d1"}, {"id": "d2"}]

    res = svc.refresh_candidates(
        collect_fn=collect_fn,
        save_candidates_fn=save_candidates_fn,
        load_docs_fn=load_docs_fn,
    )

    assert res.doc_count == 2
    assert res.candidate_count == 3  # 1 web + 2 docs
    assert res.error_count == 1

    assert {c.url for c in saved_candidates["cands"]} == {
        "https://new.example/1",
        "gdrive:d1",
        "gdrive:d2",
    }
