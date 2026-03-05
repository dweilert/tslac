# storage/collector_store.py
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from collect.models import Candidate

# If you already have STATE_DIR defined elsewhere, import it instead.
STATE_DIR = "state"  # change to match your existing convention
CANDIDATES_FILE = Path(STATE_DIR) / "candidates.json"
SEEN_URLS_FILE = Path(STATE_DIR) / "seen_urls.json"


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")))


def save_seen(path: Path, seen: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(seen), indent=2), encoding="utf-8")


def _split_content_id(u: str) -> tuple[str, str, str]:
    """
    Returns (content_id, origin, open_url)
    content_id: "web:<url>" or "gdrive:<id>"
    origin: "web" | "gdrive"
    open_url: actual openable URL
    """
    s = (u or "").strip()
    if not s:
        return ("", "web", "")

    if s.startswith("web:"):
        raw = s[len("web:") :].strip()
        return (f"web:{raw}", "web", raw)

    if s.startswith("gdrive:"):
        doc_id = s[len("gdrive:") :].strip()
        open_url = f"https://docs.google.com/document/d/{doc_id}/edit" if doc_id else ""
        return (f"gdrive:{doc_id}", "gdrive", open_url)

    # Back-compat: raw http(s) treated as web
    if s.startswith("http://") or s.startswith("https://"):
        return (f"web:{s}", "web", s)

    # Back-compat: bare doc id treated as gdrive
    doc_id = s
    open_url = f"https://docs.google.com/document/d/{doc_id}/edit" if doc_id else ""
    return (f"gdrive:{doc_id}", "gdrive", open_url)


def _normalize_candidate_record(r: dict[str, Any]) -> dict[str, Any]:
    url = r.get("url")
    if isinstance(url, str) and url.strip():
        cid, origin, open_url = _split_content_id(url)
        if cid:
            r.setdefault("id", cid)
            r.setdefault("origin", origin)
            r.setdefault("open_url", open_url)
            # Normalize url to canonical id if it was raw
            r["url"] = cid
        else:
            r.setdefault("origin", "web")
    else:
        r.setdefault("origin", "web")
    return r


def save_candidates_json(path: Path, candidates: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    payload: list[dict[str, Any]] = []
    for c in candidates:
        cid, origin, open_url = _split_content_id(c.url)

        published = c.published.isoformat() if isinstance(c.published, date) else None
        payload.append(
            {
                "id": cid,
                "origin": origin,
                "title": c.title,
                "url": cid,  # canonical id stored everywhere
                "open_url": open_url,  # convenience for UI/preview
                "source": str(c.source),
                "published": published,
                "summary": c.summary or "",
            }
        )

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_candidates_file(path: str | Path | None = None) -> list[Candidate]:
    p = Path(path) if path is not None else CANDIDATES_FILE
    if not p.exists():
        return []

    data = json.loads(p.read_text(encoding="utf-8"))
    out: list[Candidate] = []

    # Expect list[dict], but be defensive
    if not isinstance(data, list):
        return []

    for raw in data:
        if not isinstance(raw, dict):
            continue

        r = _normalize_candidate_record(raw)

        published_raw = r.get("published")
        published = (
            date.fromisoformat(published_raw)
            if isinstance(published_raw, str) and published_raw
            else None
        )

        out.append(
            Candidate(
                title=r.get("title", ""),
                url=r.get("url", ""),
                source=r.get("source", "featured"),
                published=published,
                summary=r.get("summary"),
            )
        )

    return out
