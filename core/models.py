from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    title: str
    url: str
    source: str
    published: str | None = None  # ISO date like "2026-03-02"
    summary: str | None = None
