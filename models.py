from __future__ import annotations

from dataclasses import dataclass

@dataclass
class Candidate:
    title: str
    url: str
    source: str