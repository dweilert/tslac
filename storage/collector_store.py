from __future__ import annotations

import json
from datetime import date
from pathlib import Path

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


def save_candidates_json(path: Path, candidates: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "title": c.title,
            "url": c.url,
            "source": c.source,
            "published": c.published,
            "summary": c.summary,
        }
        for c in candidates
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_candidates_file(path: str | Path | None = None) -> list[Candidate]:
    p = Path(path) if path is not None else CANDIDATES_FILE
    if not p.exists():
        return []

    data = json.loads(p.read_text(encoding="utf-8"))
    out: list[Candidate] = []

    for r in data:
        published = date.fromisoformat(r["published"]) if r.get("published") else None
        out.append(
            Candidate(
                title=r["title"],
                url=r["url"],
                source=r.get("source", "featured"),
                published=published,
                summary=r.get("summary"),
            )
        )
    return out
