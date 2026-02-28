# storage/candidates_store.py
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from collect.models import Candidate


def load_candidates_file(path: str | Path) -> list[Candidate]:
    p = Path(path)
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
