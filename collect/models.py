from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

SourceKind = Literal["featured", "carousel", "other"]


@dataclass(frozen=True)
class RawCandidate:
    """Result of parsing the homepage only (no per-article fetch)."""

    title: str
    url: str
    source: SourceKind
    summary: str | None = None


@dataclass(frozen=True)
class Candidate:
    """Fully evaluated candidate after fetching info page and applying rules."""

    title: str
    url: str
    source: SourceKind
    published: date | None
    summary: str | None = None
