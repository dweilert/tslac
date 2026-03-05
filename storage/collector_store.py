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


def _compute_web_id(url: str) -> str:
    # Canonical web candidate id format for Milestone 2
    return f"web:{url}"


def _normalize_candidate_record(r: dict[str, Any]) -> dict[str, Any]:
    """
    Backfill fields for older candidates.json records.
    Keeps existing fields intact and only adds missing ones.
    """
    url = r.get("url")
    if isinstance(url, str) and url:
        r.setdefault("origin", "web")
        r.setdefault("id", _compute_web_id(url))
    else:
        # If a record is malformed/missing url, don't invent ids.
        r.setdefault("origin", "web")
    return r


def save_candidates_json(path: Path, candidates: list[Candidate]) -> None:
    """
    Writes candidates.json including new Milestone 2 fields:
      - id
      - origin
    while preserving existing schema fields used by current UI.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    payload: list[dict[str, Any]] = []
    for c in candidates:
        url = c.url
        published = c.published.isoformat() if isinstance(c.published, date) else c.published

        payload.append(
            {
                "id": _compute_web_id(url),
                "origin": "web",
                "title": c.title,
                "url": url,
                "source": c.source,
                "published": published,
                "summary": c.summary,
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
        published = date.fromisoformat(published_raw) if isinstance(published_raw, str) and published_raw else None

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
