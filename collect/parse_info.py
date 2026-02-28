from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class InfoParseResult:
    published: date | None


DATE_PATTERNS = [
    # Examples; adjust to what tslac pages actually use
    re.compile(
        r"(\bJanuary\b|\bFebruary\b|\bMarch\b|\bApril\b|\bMay\b|\bJune\b|\bJuly\b|\bAugust\b|\bSeptember\b|\bOctober\b|\bNovember\b|\bDecember\b)\s+(\d{1,2}),\s+(\d{4})"
    ),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
]


def parse_info_page(html: str) -> InfoParseResult:
    soup = BeautifulSoup(html, "html.parser")

    published = _extract_published_date(soup)
    return InfoParseResult(published=published)


def _extract_published_date(soup: BeautifulSoup) -> date | None:
    # Replace with your existing extraction rules.
    # Common spots:
    # - <time datetime="...">
    # - "Published:" label
    # - meta property tags
    time = soup.find("time")
    if time and time.get("datetime"):
        dt = _try_parse_iso_date(time["datetime"])
        if dt:
            return dt

    text = soup.get_text(" ", strip=True)
    return _scan_text_for_date(text)


def _try_parse_iso_date(s: str) -> date | None:
    # handles "2026-02-26" or "2026-02-26T10:00:00Z"
    try:
        # try date first
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return datetime.fromisoformat(s[:10]).date()
    except ValueError:
        return None
    return None


def _scan_text_for_date(text: str) -> date | None:
    # Conservative scan; you already have business rules—copy them here.
    for pat in DATE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        # pattern 1: MonthName DD, YYYY
        if pat.pattern.startswith("("):  # rough check; you can handle more cleanly
            month_name, day_s, year_s = m.group(1), m.group(2), m.group(3)
            try:
                return datetime.strptime(f"{month_name} {day_s} {year_s}", "%B %d %Y").date()
            except ValueError:
                continue
        # pattern 2: YYYY-MM-DD
        if len(m.groups()) == 3 and m.group(1).isdigit():
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue

    return None
