from __future__ import annotations

from datetime import date

from web.fetch import FetchError, fetch_html

from .models import Candidate
from .parse_homepage import parse_homepage_candidates
from .parse_info import parse_info_page
from .rules import CollectRules, is_allowed


def collect_candidates(
    homepage_url: str,
    *,
    rules: CollectRules,
    today: date | None = None,
    timeout_s: float = 15.0,
    seen_urls: set[str] | None = None,
) -> tuple[list[Candidate], list[str]]:
    """
    Returns:
      - candidates: filtered and enriched
      - errors: list of human-readable error strings

    No file IO here. Caller passes seen_urls and persists results elsewhere.
    """
    if today is None:
        today = date.today()
    if seen_urls is None:
        seen_urls = set()

    errors: list[str] = []

    # Fetch homepage
    try:
        home = fetch_html(homepage_url, timeout_s=timeout_s)
    except FetchError as e:
        return ([], [str(e)])

    raw = parse_homepage_candidates(home.text, base_url=home.url)

    # Filter out already seen early (cheap)
    raw = [c for c in raw if c.url not in seen_urls]

    results: list[Candidate] = []
    for rc in raw:
        published = None
        try:
            info = fetch_html(rc.url, timeout_s=timeout_s)
            info_parsed = parse_info_page(info.text)
            published = info_parsed.published
        except FetchError as e:
            # Non-fatal: keep candidate but mark published None, or skip. Match your current behavior.
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Parse failure for {rc.url}: {e}")

        if not is_allowed(rc.title, rc.url, published, rules=rules, today=today):
            continue

        results.append(
            Candidate(
                title=rc.title,
                url=rc.url,
                source=rc.source,
                published=published,
                summary=rc.summary,
            )
        )

    return (results, errors)
