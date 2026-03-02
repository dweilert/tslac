from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from collect.collector import collect_candidates
from collect.rules import CollectRules
from docsys.store import load_doc_candidates
from storage.collector_store import (
    CANDIDATES_FILE,
    SEEN_URLS_FILE,
    load_candidates_file,
    load_seen,
    save_candidates_json,
    save_seen,
)
from storage.selected_store import save_selected

HOMEPAGE_URL = "https://www.tsl.texas.gov/"


@dataclass(frozen=True)
class RefreshResult:
    doc_count: int
    candidate_count: int
    error_count: int


# Dependency-injection callable types
CollectFn = Callable[[str, CollectRules, date, set[str]], tuple[list[Any], list[Any]]]
LoadSeenFn = Callable[[Any], set[str]]
SaveSeenFn = Callable[[Any, set[str]], None]
SaveCandidatesFn = Callable[[Any, list[Any]], None]
LoadDocsFn = Callable[[], list[Any]]
LoadCandidatesFileFn = Callable[[Any], list[Any]]


def refresh_candidates(
    *,
    today: date | None = None,
    months_back: int = 3,
    collect_fn: CollectFn | None = None,
    load_seen_fn: LoadSeenFn | None = None,
    save_seen_fn: SaveSeenFn | None = None,
    save_candidates_fn: SaveCandidatesFn | None = None,
    load_docs_fn: LoadDocsFn | None = None,
) -> RefreshResult:
    """
    Refresh candidate list from tsl.texas.gov and persist:
      - candidates.json (for UI)
      - seen_urls.json (to avoid reprocessing)

    DI parameters are optional; they exist to make unit tests easy.
    """

    def _default_collect(homepage: str, rules: CollectRules, day: date, seen_urls: set[str]):
        return collect_candidates(homepage, rules=rules, today=day, seen_urls=seen_urls)

    collect_fn = collect_fn or _default_collect
    load_seen_fn = load_seen_fn or load_seen
    save_seen_fn = save_seen_fn or save_seen
    save_candidates_fn = save_candidates_fn or save_candidates_json
    load_docs_fn = load_docs_fn or load_doc_candidates

    seen = load_seen_fn(SEEN_URLS_FILE)

    rules = CollectRules(
        months_back=months_back,
        exclude_url_substrings=(),
        exclude_title_substrings=(),
    )

    candidates, errors = collect_fn(
        HOMEPAGE_URL,
        rules,
        today or date.today(),
        seen,
    )

    save_candidates_fn(CANDIDATES_FILE, candidates)

    # candidates are expected to have .url
    seen.update(c.url for c in candidates)
    save_seen_fn(SEEN_URLS_FILE, seen)

    doc_cnt = len(load_docs_fn())

    return RefreshResult(
        doc_count=doc_cnt,
        candidate_count=len(candidates),
        error_count=len(errors),
    )


def save_picks(*, subject: str, intro: str, picked_urls: list[str]) -> int:
    """
    Persist selection to the selected-items store. Returns number of items saved.
    """
    save_selected(subject, intro, picked_urls)
    return len(picked_urls)


def load_persisted_candidates(
    *,
    load_candidates_file_fn: LoadCandidatesFileFn | None = None,
) -> list[Any]:
    """
    Routes/templates can call this for rendering.
    DI exists to make tests easy.
    """
    load_candidates_file_fn = load_candidates_file_fn or load_candidates_file
    return load_candidates_file_fn(CANDIDATES_FILE)
