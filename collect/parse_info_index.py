from datetime import date, datetime, timedelta
from urllib.parse import urljoin
from .models import RawCandidate
from bs4 import BeautifulSoup


def parse_info_news_candidates(
    html: str,
    *,
    base_url: str,
    today: date,
    days_back: int = 90,
) -> list[RawCandidate]:
    """
    Parse the /info page (News listing) into RawCandidate.

    Structure (per spec):
      - each entry starts with: <time datetime=...>VISIBLE_DATE</time>
      - link begins with: <a href="/node/####" hreflang="...">
      - topic/title is found in a region containing: class="field-content"
      - visible date format: "Thursday, February 12, 2026"
      - include only last `days_back` days
    """
    soup = BeautifulSoup(html, "html.parser")
    cutoff = today - timedelta(days=days_back)

    out: list[RawCandidate] = []

    # Usually newest-first; break once we drop older than cutoff
    for t in soup.select('time[datetime]'):
        published = _parse_info_visible_date(t.get_text(" ", strip=True))
        if published is None:
            continue

        if published < cutoff:
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
        if a is None:
            continue
        href = (a.get("href") or "").strip()
        if not href:
            continue

        url = urljoin(base_url, href)

        title_el = entry.select_one(".field-content")
        title = title_el.get_text(" ", strip=True) if title_el else a.get_text(" ", strip=True)
        title = " ".join(title.split())
        if not title:
            continue

        out.append(
            RawCandidate(
                title=title,
                url=url,
                source="News",
                published=published,
                summary=None,
            )
        )

    # De-dup by URL preserving order
    seen: set[str] = set()
    deduped: list[RawCandidate] = []
    for c in out:
        if c.url in seen:
            continue
        seen.add(c.url)
        deduped.append(c)

    return deduped


def _parse_info_visible_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None

    for fmt in ("%A, %B %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None