from __future__ import annotations

from collections.abc import Callable, Iterable
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

    candidates, errors = collect_fn(
        HOMEPAGE_URL,
        rules,
        today or date.today(),
        seen,
    )

    # We still count docs (for status message), but we do not merge them yet.
    # Merging docs will be reintroduced once we have ONE unified candidate model and persistence schema.
    docs = load_docs_fn() or []

    # ---- Merge watch results into candidates ----
    try:
        wr = load_latest_results()
        w_results = wr.get("results") or []
        watch_candidates: list[Any] = []

        for r in w_results:
            if not isinstance(r, dict):
                continue

            url = r.get("url") or r.get("page_url") or r.get("link") or r.get("href") or ""
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

        candidates = list(candidates) + watch_candidates
    except Exception:
        pass

    save_candidates_fn(CANDIDATES_FILE, candidates)

    def _cand_url(c: Any) -> str:
        if hasattr(c, "url"):
            return str(getattr(c, "url") or "").strip()
        if isinstance(c, dict):
            return str(c.get("url") or "").strip()
        return ""

    seen.update(u for u in (_cand_url(c) for c in candidates) if u)
    save_seen_fn(SEEN_URLS_FILE, seen)

    return RefreshResult(
        doc_count=len(docs),
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


def get_candidate_id(c: Any) -> str:
    """
    Canonical candidate id.
    - If object has .id, use it (future gdrive/local support).
    - Else fall back to web:<url> for existing Candidate / WatchCandidate types.
    """
    cid = getattr(c, "id", None)
    if isinstance(cid, str) and cid:
        return cid

    url = getattr(c, "url", None)
    if isinstance(url, str) and url:
        return f"web:{url}"

    return ""


def find_candidate_by_id(candidates: Iterable[Any], candidate_id: str) -> Any | None:
    """
    Return the first candidate whose canonical id matches candidate_id.
    Also supports legacy: if candidate_id is a raw URL, match web:<url>.
    """
    if not candidate_id:
        return None

    wanted = candidate_id
    # If caller passed a raw URL, treat it as web:<url>
    if "://" in wanted and not wanted.startswith(("web:", "gdrive:", "local:")):
        wanted = f"web:{wanted}"

    for c in candidates:
        if get_candidate_id(c) == wanted:
            return c
    return None


def _as_str(x: Any) -> str:
    return "" if x is None else str(x)


def _canon_doc_id(did: str) -> str:
    did = (did or "").strip()
    if not did:
        return ""
    if did.startswith("doc:"):
        return "gdrive:" + did[len("doc:"):].strip()
    return did


def _as_str(x: Any) -> str:
    return "" if x is None else str(x)


def _canon_doc_id(did: str) -> str:
    did = (did or "").strip()
    if not did:
        return ""
    if did.startswith("doc:"):
        return "gdrive:" + did[len("doc:"):].strip()
    return did


def _canon_web_id(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return ""
    return u if u.startswith("web:") else f"web:{u}"


def unify_candidates(web_candidates: list[Any]) -> list[dict[str, Any]]:
    """
    Produce one list for candidates.html.
    Each item has: title, url (canonical content_id), source, open_url
    """
    out: list[dict[str, Any]] = []

    # --- web candidates ---
    for c in web_candidates or []:
        if isinstance(c, dict):
            raw = _as_str(c.get("url") or c.get("original_url") or "").strip()
            title = _as_str(c.get("title") or "").strip()
            source = _as_str(c.get("source") or "web").strip() or "web"
        else:
            raw = _as_str(getattr(c, "url", "") or getattr(c, "original_url", "")).strip()
            title = _as_str(getattr(c, "title", "")).strip()
            source = _as_str(getattr(c, "source", "web")).strip() or "web"

        if not raw:
            continue

        cid = _canon_web_id(raw)
        open_url = raw[len("web:") :] if raw.startswith("web:") else raw

        out.append(
            {
                "title": title or open_url,
                "url": cid,          # ✅ canonical content id
                "source": source,
                "open_url": open_url,
            }
        )

    # --- doc candidates ---
    docs = load_doc_candidates() or []
    for d in docs:
        if not isinstance(d, dict):
            continue

        did = _canon_doc_id(_as_str(d.get("id")).strip())
        if not did:
            continue

        title = _as_str(d.get("title") or did).strip()
        open_url = _as_str(d.get("url") or "").strip() or "#"

        out.append(
            {
                "title": title,
                "url": did,          # ✅ gdrive:...
                "source": "doc",
                "open_url": open_url,
            }
        )

    return out
