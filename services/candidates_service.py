from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from collect.collector import collect_candidates
from collect.models import Candidate
from collect.rules import CollectRules
from docsys.pipeline import build_doc_candidates
from docsys.sources import from_env
from storage.collector_store import (
    CANDIDATES_FILE,
    load_candidates_file,
    save_candidates_json,
)
from storage.selected_store import remove_selected_item, save_selected, save_selected_item
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
CollectFn = Callable[[str, CollectRules, date], tuple[list[Any], list[Any]]]
SaveCandidatesFn = Callable[[Any, list[Any]], None]
LoadDocsFn = Callable[[], list[dict[str, Any]]]
LoadCandidatesFileFn = Callable[[Any], list[Any]]


def refresh_candidates(
    *,
    today: date | None = None,
    months_back: int = 3,
    collect_fn: CollectFn | None = None,
    save_candidates_fn: SaveCandidatesFn | None = None,
    load_docs_fn: LoadDocsFn | None = None,
) -> RefreshResult:
    def _default_collect(homepage: str, rules: CollectRules, day: date):
        return collect_candidates(homepage, rules=rules, today=day)

    def _default_load_docs() -> list[dict[str, Any]]:
        # Builds doc candidates from configured source (gdrive or local),
        # and summarizes content via OpenAI (with caching) as needed.
        return build_doc_candidates(from_env())

    collect_fn = collect_fn or _default_collect
    save_candidates_fn = save_candidates_fn or save_candidates_json
    load_docs_fn = load_docs_fn or _default_load_docs

    rules = CollectRules(
        months_back=months_back,
        exclude_url_substrings=(),
        exclude_title_substrings=(),
    )

    candidates, errors = collect_fn(
        HOMEPAGE_URL,
        rules,
        today or date.today(),
    )

    # ---- Merge doc candidates (live build from configured source) into candidates ----
    docs = load_docs_fn() or []
    doc_candidates: list[Any] = []

    for d in docs:
        if not isinstance(d, dict):
            continue

        raw_id = str(d.get("id") or "").strip()
        if not raw_id:
            continue

        doc_source = str(d.get("source") or "").strip() or "gdrive"  # "gdrive" or "local"
        title = str(d.get("title") or "").strip() or f"Doc {raw_id}"
        summary = str(d.get("summary") or "").strip()

        # Canonical id used across app
        if raw_id.startswith(("gdrive:", "local:")):
            cid = raw_id
        else:
            cid = f"{doc_source}:{raw_id}"

        doc_candidates.append(
            Candidate(
                title=title,
                url=cid,  # canonical id
                source=doc_source,
                published=None,
                summary=summary,
            )
        )

    candidates = list(candidates) + doc_candidates

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
                    summary=str(
                        r.get("excerpt") or r.get("snippet") or r.get("summary") or ""
                    ).strip(),
                    site=str(r.get("site") or "").strip(),
                    score=r.get("score") or 0,
                    best_topic=str(r.get("best_topic") or r.get("topic") or "").strip(),
                )
            )

        candidates = list(candidates) + watch_candidates
    except Exception:
        pass

    save_candidates_fn(CANDIDATES_FILE, candidates)

    return RefreshResult(
        doc_count=len(docs),
        candidate_count=len(candidates),
        error_count=len(errors),
    )


def save_picks(*, subject: str, intro: str, picked_urls: list[str]) -> int:
    """
    Persist selection to the selected-items store. Returns number of items saved.
    """
    save_selected(subject, intro, picked_urls)
    return len(picked_urls)


def toggle_pick(*, url: str, selected: bool) -> bool:
    """Toggle one selected item in selected.yaml. Returns True if file changed."""
    if selected:
        return save_selected_item(url)
    return remove_selected_item(url)


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


def _canon_web_id(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return ""
    return u if u.startswith("web:") else f"web:{u}"


def unify_candidates(web_candidates: list[Any]) -> list[dict[str, Any]]:
    """
    Produce one list for candidates.html.
    Each item has: title, url (canonical content_id), source, open_url

    Note: doc candidates are built live from configured source (gdrive/local).
    open_url for docs is best-effort until we propagate stable open URLs
    from docsys.sources/build_doc_candidates.
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
                "url": cid,  # canonical content id
                "source": source,
                "open_url": open_url,
            }
        )

    # --- doc candidates (live) ---
    docs = build_doc_candidates(from_env()) or []
    for d in docs:
        if not isinstance(d, dict):
            continue

        raw_id = _as_str(d.get("id")).strip()
        if not raw_id:
            continue

        src = _as_str(d.get("source") or "gdrive").strip() or "gdrive"

        if raw_id.startswith(("gdrive:", "local:")):
            did = raw_id
        else:
            did = f"{src}:{raw_id}"

        title = _as_str(d.get("title") or did).strip()

        # Best-effort. If you later include open_url in pipeline output, this will “just work”.
        open_url = _as_str(d.get("open_url") or d.get("url") or "").strip() or "#"

        out.append(
            {
                "title": title,
                "url": did,
                "source": src,
                "open_url": open_url,
            }
        )

    return out
