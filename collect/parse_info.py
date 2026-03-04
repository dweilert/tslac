from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup


# -------------------------
# Data models
# -------------------------

@dataclass(frozen=True)
class InfoParseResult:
    published: date | None


@dataclass(frozen=True)
class IndexCandidate:
    """
    A lightweight normalized candidate produced by parsing the /info listing page.
    Collector can map this into your real models.Candidate.
    """
    title: str
    url: str
    source: str  # "News"
    published: date | None
    summary: str | None = None


# -------------------------
# Existing date scan patterns (kept)
# -------------------------

DATE_PATTERNS = [
    # MonthName DD, YYYY
    re.compile(
        r"(\bJanuary\b|\bFebruary\b|\bMarch\b|\bApril\b|\bMay\b|\bJune\b|\bJuly\b|\bAugust\b|\bSeptember\b|\bOctober\b|\bNovember\b|\bDecember\b)\s+(\d{1,2}),\s+(\d{4})"
    ),
    # YYYY-MM-DD
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
]


# -------------------------
# Article page parsing (existing behavior)
# -------------------------

def parse_info_page(html: str) -> InfoParseResult:
    """
    Parse an individual article page and try to extract its published date.
    """
    soup = BeautifulSoup(html, "html.parser")
    published = _extract_published_date(soup)
    return InfoParseResult(published=published)


def _extract_published_date(soup: BeautifulSoup) -> date | None:
    # Common spots:
    # - <time datetime="...">
    # - "Published:" label
    # - meta property tags
    time_el = soup.find("time")
    if time_el and time_el.get("datetime"):
        dt = _try_parse_iso_date(str(time_el["datetime"]))
        if dt:
            return dt

    text = soup.get_text(" ", strip=True)
    return _scan_text_for_date(text)


def _try_parse_iso_date(s: str) -> date | None:
    # handles "2026-02-26" or "2026-02-26T10:00:00Z"
    try:
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return datetime.fromisoformat(s[:10]).date()
    except ValueError:
        return None
    return None


def _scan_text_for_date(text: str) -> date | None:
    # Conservative scan
    for pat in DATE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue

        # pattern 1: MonthName DD, YYYY
        if pat is DATE_PATTERNS[0]:
            month_name, day_s, year_s = m.group(1), m.group(2), m.group(3)
            try:
                return datetime.strptime(f"{month_name} {day_s} {year_s}", "%B %d %Y").date()
            except ValueError:
                continue

        # pattern 2: YYYY-MM-DD
        if pat is DATE_PATTERNS[1]:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue

    return None


# -------------------------
# NEW: /info index/listing parsing (Milestone 1)
# -------------------------

def parse_info_index_candidates(
    html: str,
    *,
    base_url: str,
    today: date,
    days_back: int = 90,
) -> list[IndexCandidate]:
    """
    Parse the /info listing page and return "News" candidates for the last `days_back` days.

    Signals (per your spec):
      - Each item begins with: <time datetime=...>VISIBLE_DATE</time>
      - Link is: <a href="/node/####" ...>
      - Title/topic is in: class="field-content"
      - Visible date format: "Thursday, February 12, 2026"

    Notes:
      - Filters to the last `days_back` days (inclusive).
      - Assumes listing is generally newest-first; will break early once older than cutoff.
    """
    soup = BeautifulSoup(html, "html.parser")
    cutoff = today - timedelta(days=days_back)

    out: list[IndexCandidate] = []

    for t in soup.select('time[datetime]'):
        published = _parse_info_visible_date(_text(t))
        if published is None:
            # If we can't parse the visible date, skip this entry (don’t guess).
            continue

        if published < cutoff:
            # /info listings are typically newest-first; stop once we drop past cutoff.
            break

        entry = (
            t.find_parent("article")
            or t.find_parent("li")
            or t.find_parent("div")
            or t.parent
        )
        if entry is None:
            continue

        a = entry.select_one('a[href^="/node/"]')
        if a is None or not a.get("href"):
            continue

        href = str(a["href"]).strip()
        url = urljoin(base_url, href)

        title_el = entry.select_one(".field-content")
        title = _text(title_el) if title_el else _text(a)
        if not title:
            continue

        out.append(
            IndexCandidate(
                title=title,
                url=url,
                source="News",
                published=published,
                summary=None,
            )
        )

    return out


def _parse_info_visible_date(s: str) -> date | None:
    """
    /info listing visible date formats:
      - "Thursday, February 12, 2026"
      - (fallback) "February 12, 2026"
    """
    s = (s or "").strip()
    if not s:
        return None

    for fmt in ("%A, %B %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    return None


def _text(el) -> str:
    if el is None:
        return ""
    return el.get_text(" ", strip=True)