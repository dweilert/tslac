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

    content_id:
      - "web:<url>"
      - "gdrive:<file_id>"
      - "local:<path_or_id>"

    origin:
      - "web" | "gdrive" | "local"

    open_url:
      - actual openable URL (best-effort)
    """
    s = (u or "").strip()
    if not s:
        return ("", "web", "")

    if s.startswith("web:"):
        raw = s[len("web:") :].strip()
        return (f"web:{raw}", "web", raw)

    if s.startswith("gdrive:"):
        file_id = s[len("gdrive:") :].strip()
        # Universal Drive open link works for Google Docs *and* PDFs/DOCX/TXT stored in Drive.
        open_url = f"https://drive.google.com/open?id={file_id}" if file_id else ""
        return (f"gdrive:{file_id}", "gdrive", open_url)

    if s.startswith("local:"):
        local_id = s[len("local:") :].strip()
        # Browsers won't reliably open arbitrary local paths for security reasons.
        # We'll keep this as placeholder until a local-serving route exists.
        open_url = ""
        return (f"local:{local_id}", "local", open_url)

    # Back-compat: raw http(s) treated as web
    if s.startswith("http://") or s.startswith("https://"):
        return (f"web:{s}", "web", s)

    # Back-compat: bare doc id treated as gdrive
    file_id = s
    open_url = f"https://drive.google.com/open?id={file_id}" if file_id else ""
    return (f"gdrive:{file_id}", "gdrive", open_url)


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


def _published_to_iso(p: Any) -> str | None:
    if isinstance(p, date):
        return p.isoformat()
    if isinstance(p, str):
        s = p.strip()
        return s or None
    return None


def _as_str(x: Any) -> str:
    return "" if x is None else str(x)


def _candidate_to_record(c: Any) -> dict[str, Any] | None:
    """
    Convert any candidate-like object into a JSON record.
    Supports:
      - collect.models.Candidate
      - WatchCandidate
      - dict records
      - DocCandidate-like objects (no .published)
    """
    if isinstance(c, dict):
        r = dict(c)
        # Ensure it has canonical id/url/open_url fields
        return _normalize_candidate_record(r)

    url = _as_str(getattr(c, "url", "")).strip()
    if not url:
        return None

    cid, origin, open_url = _split_content_id(url)

    title = _as_str(getattr(c, "title", "")).strip()
    source = _as_str(getattr(c, "source", "")).strip()
    summary = _as_str(getattr(c, "summary", "")).strip()

    published_iso = _published_to_iso(getattr(c, "published", None))

    r: dict[str, Any] = {
        "id": cid,
        "origin": origin,
        "title": title or cid,
        "url": cid,  # canonical id stored everywhere
        "open_url": open_url,  # best-effort convenience for UI/preview
        "source": source,
        "published": published_iso,
        "summary": summary,
    }

    # Optional fields (won't exist on all candidate types)
    watched = getattr(c, "watched", None)
    if watched is not None:
        r["watched"] = bool(watched)

    site = getattr(c, "site", None)
    if site:
        r["site"] = _as_str(site).strip()

    score = getattr(c, "score", None)
    if score is not None:
        r["score"] = score

    best_topic = getattr(c, "best_topic", None)
    if best_topic:
        r["best_topic"] = _as_str(best_topic).strip()

    return r


def save_candidates_json(path: Path, candidates: list[Any]) -> None:
    """
    Persist a unified candidates list to JSON.

    IMPORTANT:
    - This must tolerate multiple candidate shapes without assuming attributes exist.
    - The on-disk format remains list[dict].
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    payload: list[dict[str, Any]] = []
    for c in candidates:
        rec = _candidate_to_record(c)
        if rec is not None:
            payload.append(rec)

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
