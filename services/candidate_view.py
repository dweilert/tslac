# services/candidate_view.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.content_ids import canonical_content_id, split_content_id

@dataclass(frozen=True)
class UICandidate:
    url: str       # canonical content_id (yes, keep name "url" for template compat)
    open_url: str  # openable URL
    title: str
    source: str    # "web" | "watch" | "gdrive" | ...
    origin: str    # "web" | "gdrive" | "local"


def _strip(x: Any) -> str:
    return ("" if x is None else str(x)).strip()


def ui_from_candidate_record(r: Any) -> UICandidate | None:
    """
    Accepts either:
      - dict candidate record (from candidates.json)
      - dataclass Candidate object (from collect.models)
    """
    if r is None:
        return None

    # Pull fields from dict or object
    if isinstance(r, dict):
        raw_id = _strip(r.get("id") or r.get("url") or "")
        title = _strip(r.get("title") or "")
        source = _strip(r.get("source") or r.get("origin") or "")
    else:
        raw_id = _strip(getattr(r, "url", "") or getattr(r, "id", ""))
        title = _strip(getattr(r, "title", ""))
        source = _strip(getattr(r, "source", ""))

    cid = canonical_content_id(raw_id)
    if not cid:
        return None

    cref = split_content_id(cid)

    # default title if missing
    if not title:
        title = cref.open_url or cid

    # default source label
    if not source:
        source = "gdrive" if cref.origin == "gdrive" else "web"

    return UICandidate(
        url=cid,
        open_url=cref.open_url,
        title=title,
        source=source,
        origin=cref.origin,
    )