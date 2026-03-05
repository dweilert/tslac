from __future__ import annotations

from datetime import date, datetime
from typing import Any

from logutil import debug
from models import Candidate
from web.fetch import FetchError, fetch_html

from .parse_homepage import parse_homepage_candidates
from .parse_info_index import parse_info_news_candidates
from .rules import CollectRules, is_allowed


# ---------------------------
# Helpers
# ---------------------------
# ---------------------------
# Helpers
# ---------------------------
def _norm_source(s: object) -> str:
    """
    Normalize source into a stable, display-ready set:
      Carousel | Featured | News | Watch | Doc | Unknown
    Accepts None/str/anything.
    """
    if s is None:
        return "Unknown"

    v = str(s).strip()
    if not v:
        return "Unknown"

    v_low = v.lower()

    if v_low in ("carousel",):
        return "Carousel"
    if v_low in ("featured", "feature", "featurednews", "featured_news"):
        return "Featured"
    if v_low in ("news", "info"):
        return "News"
    if v_low in ("watch", "watched"):
        return "Watch"
    if v_low in ("doc", "docs", "document", "documents"):
        return "Doc"

    return "Unknown"


def _count_by_source(items: list[object]) -> dict[str, int]:
    out: dict[str, int] = {}
    for it in items:
        src = _norm_source(getattr(it, "source", None))
        out[src] = out.get(src, 0) + 1
    return out


def _as_date(p: Any) -> date | None:
    """
    Normalize various published representations into date | None
    for rules filtering (is_allowed expects date semantics).
    Accepts:
      - date
      - datetime
      - ISO strings like "YYYY-MM-DD" (or "YYYY-MM-DDTHH:MM:SS...")
    """
    if p is None:
        return None

    if isinstance(p, datetime):
        return p.date()

    # datetime is also a date; ensure pure date stays date
    if isinstance(p, date) and not isinstance(p, datetime):
        return p

    if isinstance(p, str):
        s = p.strip()
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            try:
                return datetime.fromisoformat(s[:10]).date()
            except ValueError:
                return None
        return None

    return None


def _to_iso_date_str(p: Any) -> str | None:
    """
    Normalize published into an ISO string for storage/UI.
    Accepts date/datetime/ISO string; returns "YYYY-MM-DD" or None.
    """
    if p is None:
        return None

    if isinstance(p, datetime):
        return p.date().isoformat()

    if isinstance(p, date) and not isinstance(p, datetime):
        return p.isoformat()

    if isinstance(p, str):
        s = p.strip()
        if not s:
            return None
        # If it's already ISO-ish, keep YYYY-MM-DD portion
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return s[:10]
        return s

    # last resort: stringify (shouldn’t happen, but avoids crashing refresh)
    return str(p)


# ---------------------------
# Main
# ---------------------------
def collect_candidates(
    homepage_url: str,
    *,
    rules: CollectRules,
    today: date | None = None,
    timeout_s: float = 15.0,
    seen_urls: set[str] | None = None,
) -> tuple[list[Candidate], list[str]]:
    if today is None:
        today = date.today()
    if seen_urls is None:
        seen_urls = set()

    errors: list[str] = []

    debug(f"collector: start homepage_url={homepage_url} timeout_s={timeout_s}")

    # ---------------------------
    # Fetch homepage + parse
    # ---------------------------
    try:
        # info("DEBUG collector: fetching homepage...")
        home = fetch_html(homepage_url, timeout_s=timeout_s)
        debug(f"collector: homepage fetched bytes={len(home.text)} url={home.url}")
    except FetchError as e:
        debug(f"collector: homepage fetch FAILED: {e}")
        return ([], [str(e)])

    # info("DEBUG collector: parsing homepage candidates...")
    home_raw = parse_homepage_candidates(home.text, base_url=home.url)

    # ---------------------------
    # Fetch /info + parse (90 days)
    # ---------------------------
    info_url = home.url.rstrip("/") + "/info"
    news_raw: list[object] = []

    try:
        debug(f"collector: fetching /info... url={info_url}")
        info_page = fetch_html(info_url, timeout_s=timeout_s)
        debug(f"collector: /info fetched bytes={len(info_page.text)}")

        news_raw = parse_info_news_candidates(
            info_page.text,
            base_url=info_page.url,
            today=today,
            days_back=90,
        )

    except FetchError as e:
        debug(f"collector: /info fetch FAILED: {e}")
        errors.append(str(e))

    except Exception as e:
        debug(f"collector: /info parse FAILED: {e}")
        errors.append(f"Parse failure for {info_url}: {e}")

    # ---------------------------
    # Apply rules + finalize
    # ---------------------------
    results: list[Candidate] = []

    # ---------------------------
    # Combine + seen filter
    # ---------------------------
    raw = list(home_raw) + list(news_raw)
    raw = [c for c in raw if c.url not in seen_urls]

    # ---------------------------
    # Apply rules + finalize
    # ---------------------------
    results: list[Candidate] = []
    dropped_news = 0

    for rc in raw:
        pub_for_rules = _as_date(getattr(rc, "published", None))

        if not is_allowed(rc.title, rc.url, pub_for_rules, rules=rules, today=today):
            if getattr(rc, "source", "") == "News":
                dropped_news += 1
            continue

        results.append(
            Candidate(
                title=rc.title,
                url=rc.url,
                source=_norm_source(getattr(rc, "source", None)),
                published=_to_iso_date_str(getattr(rc, "published", None)),
                summary=getattr(rc, "summary", None),
            )
        )

    if dropped_news:
        debug(f"DEBUG collector: rules dropped News count={dropped_news}")

    debug(f"collector: final results count={len(results)}")
    debug(f"collector: final sources={sorted({c.source for c in results})}")

    return (results, errors)
