from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from dateutil.relativedelta import relativedelta


@dataclass(frozen=True)
class CollectRules:
    months_back: int = 3
    exclude_url_substrings: tuple[str, ...] = ()
    exclude_title_substrings: tuple[str, ...] = ()


def is_allowed(
    title: str, url: str, published: date | None, *, rules: CollectRules, today: date
) -> bool:
    # Exclusions
    lt = title.lower()
    lu = url.lower()

    for s in rules.exclude_title_substrings:
        if s.lower() in lt:
            return False
    for s in rules.exclude_url_substrings:
        if s.lower() in lu:
            return False

    # Date window: if no date, keep it (or drop it) — match your current behavior
    if published is None:
        return True  # or False if you prefer strict

    cutoff = today - relativedelta(months=rules.months_back)
    return published >= cutoff
