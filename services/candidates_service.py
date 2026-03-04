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
from watch.scan import load_latest_results
from collections import Counter
from logutil import info


HOMEPAGE_URL = "https://www.tsl.texas.gov/"


@dataclass(frozen=True)
class WatchCandidate:
    url: str
    title: str
    published: str = ""
    summary: str = ""          
    source: str = "watch"
    watched: bool = True
    site: str = ""
    score: int | float = 0
    best_topic: str = ""


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
    ignore_seen: bool = False,
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

    from logutil import info
    #info(f"DEBUG: inside services.refresh_candidates(ignore_seen={ignore_seen})")    

    def _default_collect(homepage: str, rules: CollectRules, day: date, seen_urls: set[str]):
        return collect_candidates(homepage, rules=rules, today=day, seen_urls=seen_urls)

    collect_fn = collect_fn or _default_collect
    load_seen_fn = load_seen_fn or load_seen
    save_seen_fn = save_seen_fn or save_seen
    save_candidates_fn = save_candidates_fn or save_candidates_json
    load_docs_fn = load_docs_fn or load_doc_candidates

    seen = set() if ignore_seen else load_seen_fn(SEEN_URLS_FILE)

    rules = CollectRules(
        months_back=months_back,
        exclude_url_substrings=(),
        exclude_title_substrings=(),
    )

    #info("DEBUG: calling collect_candidates()")

    candidates, errors = collect_fn(
        HOMEPAGE_URL,
        rules,
        today or date.today(),
        seen,
    )

    #info(f"DEBUG: collector returned candidates={len(candidates)} errors={len(errors)}")

    sources = sorted({getattr(c, "source", "?") for c in candidates})
    #info(f"DEBUG: collector sources={sources}")


    # ---- Merge watch results into candidates ----
    try:
        wr = load_latest_results()
        w_results = wr.get("results") or []
        #info(f"DEBUG: watch results loaded={len(w_results)}")
        watch_candidates: list[Any] = []
        #info(f"DEBUG: watch candidates added={len(watch_candidates)}")

        for r in w_results:
            if not isinstance(r, dict):
                continue

            # Try hard to find a URL field; fall back to site
            url = (
                (r.get("url") or r.get("page_url") or r.get("link") or r.get("href") or "")
            )
            url = str(url).strip() or str(r.get("site") or "").strip()
            if not url:
                continue

            title = str(r.get("title") or r.get("page_title") or r.get("best_title") or url).strip()

            watch_candidates.append(
                WatchCandidate(
                    url=url,
                    title=title,
                    summary=str(r.get("excerpt") or r.get("snippet") or r.get("summary") or "").strip(),
                    site=str(r.get("site") or "").strip(),
                    score=r.get("score") or 0,
                    best_topic=str(r.get("best_topic") or r.get("topic") or "").strip(),
                )
            )

        # Append watch items after TSL scrape items
        candidates = list(candidates) + watch_candidates
        #info(f"DEBUG: total candidates after watch merge={len(candidates)}")
    except Exception:
        # Watch is best-effort; do not fail refresh if watch results can’t load
        pass

    save_candidates_fn(CANDIDATES_FILE, candidates)
    #info(f"DEBUG: saving candidates to {CANDIDATES_FILE} count={len(candidates)}")

    src_counts = Counter((getattr(c, "source", None) or "Unknown") for c in candidates)
    #info(f"REFRESH saved candidates={len(candidates)} sources={dict(src_counts)} errors={len(errors)} ignore_seen={ignore_seen}")


    # candidates are expected to have .url
    seen.update(c.url for c in candidates)

    #info(f"DEBUG: updating seen URLs with {len(candidates)} candidates")
    save_seen_fn(SEEN_URLS_FILE, seen)

    doc_cnt = len(load_docs_fn())

    #info(f"DEBUG: refresh complete doc_count={doc_cnt} candidate_count={len(candidates)} error_count={len(errors)}")
    return RefreshResult(
        doc_count=doc_cnt,
        candidate_count=len(candidates),
        error_count=len(errors),
    )


def reset_seen_urls(*, save_seen_fn: SaveSeenFn | None = None) -> None:
    """
    Wipe seen_urls.json so refresh can rediscover previously seen URLs.
    DI param exists to make unit tests easy.
    """
    save_seen_fn = save_seen_fn or save_seen
    save_seen_fn(SEEN_URLS_FILE, set())


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
