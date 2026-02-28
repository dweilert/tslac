"""
LEGACY: kept temporarily while other modules migrate to collect.collector.collect_candidates().
Do not add new logic here.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import (
    BASE,
    CANDIDATES_FILE,
    EXACT_EXCLUDE_PATHS,
    EXCLUDE_TEXTS,
    HEADERS,
    HOME,
    LAST_3_MONTHS_DAYS,
    NEWS,
    OUT_DIR,
    STATE_DIR,
)
from doc_pipeline import build_doc_candidates
from doc_sources import GDriveSource, LocalDirSource
from doc_store import save_doc_candidates
from logutil import info
from models import Candidate
from state_store import load_seen, norm_url, save_seen


def is_tsl_url(u: str) -> bool:
    try:
        return urlparse(u).netloc.lower().endswith("tsl.texas.gov")
    except Exception:
        return False


def path_of(url: str) -> str:
    try:
        return (urlparse(url).path or "/").rstrip("/") or "/"
    except Exception:
        return ""


def is_node_article(url: str) -> bool:
    return "/node" in path_of(url)


def is_excluded_by_path(url: str) -> bool:
    return path_of(url) in EXACT_EXCLUDE_PATHS


def is_excluded_by_title(title: str) -> bool:
    t = (title or "").strip().lower()
    return t in EXCLUDE_TEXTS


def fetch_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def extract_links_from_section_by_heading(
    soup: BeautifulSoup, heading_text: str
) -> list[tuple[str, str]]:
    heading_re = re.compile(rf"^\s*{re.escape(heading_text)}\s*$", re.I)
    heading = None
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        if heading_re.search(tag.get_text(" ", strip=True) or ""):
            heading = tag
            break
    if not heading:
        return []

    container = heading.find_parent(["section", "div"]) or heading.parent
    if not container:
        return []

    links: list[tuple[str, str]] = []
    for a in container.find_all("a", href=True):
        title = (a.get_text(" ", strip=True) or "").strip()
        href = norm_url(urljoin(BASE, a["href"]))
        if not title or not is_tsl_url(href):
            continue
        links.append((title, href))

    seen = set()
    out = []
    for t, u in links:
        if u not in seen:
            out.append((t, u))
            seen.add(u)
    return out


# ----------------------------
# Carousel extraction (matches your HTML)
# ----------------------------
def extract_carousel_links(soup: BeautifulSoup) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []

    slides = soup.select("div.views_slideshow_cycle_slide")
    if not slides:
        slides = soup.select("div.views_slideshow_slide")

    for slide in slides:
        a = slide.select_one("div.views-field.views-field-field-image a[href]")
        title_el = slide.select_one("div.views-field.views-field-title-1 span.field-content")

        if not a or not title_el:
            continue

        href = norm_url(urljoin(BASE, a["href"]))
        if not is_tsl_url(href):
            continue

        title = (title_el.get_text(" ", strip=True) or "").strip()
        if not title:
            continue

        if is_excluded_by_title(title):
            continue
        if is_excluded_by_path(href):
            continue

        items.append((title, href))

    seen = set()
    out: list[tuple[str, str]] = []
    for t, u in items:
        if u not in seen:
            out.append((t, u))
            seen.add(u)
    return out


def is_featured_news_allowed(title: str, url: str) -> bool:
    if is_excluded_by_title(title):
        return False
    if is_excluded_by_path(url):
        return False
    if not is_node_article(url):
        return False

    return is_node_article(url)


# ----------------------------
# /info filtering: node + date in text, last 3 months
# ----------------------------
_RX_DOW_MONTH_D_Y = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+([A-Za-z]+)\.?\s+(\d{1,2}),\s+(\d{4})\b"
)
_RX_MONTH_D_Y = re.compile(r"\b([A-Za-z]+)\.?\s+(\d{1,2}),\s+(\d{4})\b")

_MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def _parse_month_name(m: str) -> int | None:
    return _MONTHS.get((m or "").strip().lower().rstrip("."))


def extract_item_date(text: str) -> datetime | None:
    if not text:
        return None

    m = _RX_DOW_MONTH_D_Y.search(text)
    if m:
        mon = _parse_month_name(m.group(1))
        if mon:
            return datetime(int(m.group(3)), mon, int(m.group(2)))

    m2 = _RX_MONTH_D_Y.search(text)
    if m2:
        mon = _parse_month_name(m2.group(1))
        if mon:
            return datetime(int(m2.group(3)), mon, int(m2.group(2)))

    return None


def extract_datetime_from_time_tag(container: BeautifulSoup) -> datetime | None:
    if not container:
        return None
    t = container.find("time")
    if not t:
        return None
    dt = t.get("datetime")
    if not dt:
        return None
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        try:
            return datetime.strptime(dt[:10], "%Y-%m-%d")
        except Exception:
            return None


def within_last_3_months(dt: datetime) -> bool:
    now = datetime.now()
    cutoff = now - timedelta(days=LAST_3_MONTHS_DAYS)
    return cutoff.date() <= dt.date() <= now.date()


def extract_info_node_items_last_3_months(soup: BeautifulSoup) -> list[Candidate]:
    out: list[Candidate] = []

    for a in soup.find_all("a", href=True):
        href = norm_url(urljoin(BASE, a["href"]))
        if not is_tsl_url(href):
            continue
        if not is_node_article(href):
            continue
        if is_excluded_by_path(href):
            continue

        title = (a.get_text(" ", strip=True) or "").strip()
        if len(title) < 6:
            continue

        container = a
        dt = None
        for _ in range(5):
            container = (
                container.find_parent(["article", "li", "div", "section"]) or container.parent
            )
            if not container:
                break
            dt = extract_datetime_from_time_tag(container)
            if dt:
                break
            blob = container.get_text(" ", strip=True) or ""
            dt = extract_item_date(blob)
            if dt:
                break

        if not dt:
            continue
        if not within_last_3_months(dt):
            continue

        title_with_date = f"{title} ({dt.strftime('%b %d, %Y')})"
        out.append(Candidate(title=title_with_date, url=href, source="tsl:/info(last_3_months)"))

    uniq: dict[str, Candidate] = {}
    for c in out:
        uniq.setdefault(c.url, c)
    return list(uniq.values())


# ----------------------------
# Candidate collection
# ----------------------------
def collect_candidates() -> list[Candidate]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    seen = load_seen()

    home_html = fetch_html(HOME)
    home_soup = BeautifulSoup(home_html, "html.parser")

    # Carousel candidates
    carousel = extract_carousel_links(home_soup)
    carousel_candidates = [
        Candidate(title=t, url=u, source="homepage:carousel") for t, u in carousel
    ]

    # Featured News candidates
    featured = extract_links_from_section_by_heading(home_soup, "Featured News")
    featured_candidates: list[Candidate] = []
    for t, u in featured:
        if is_featured_news_allowed(t, u):
            featured_candidates.append(Candidate(title=t, url=u, source="homepage:featured_news"))

    # /info candidates
    news_html = fetch_html(NEWS)
    news_soup = BeautifulSoup(news_html, "html.parser")
    info_candidates = extract_info_node_items_last_3_months(news_soup)

    # Document candidates
    doc_candidates = build_document_candidates()
    save_doc_candidates(doc_candidates)

    # Keep ordering: carousel -> featured -> info
    ordered = carousel_candidates + featured_candidates + info_candidates

    # Dedup preserving first occurrence
    combined: dict[str, Candidate] = {}
    for c in ordered:
        combined.setdefault(c.url, c)

    all_items = list(combined.values())

    for c in all_items:
        seen.add(c.url)
    save_seen(seen)

    CANDIDATES_FILE.write_text(
        json.dumps([asdict(c) for c in all_items], indent=2, ensure_ascii=False),
        "utf-8",
    )
    return all_items


def load_candidates_file() -> list[Candidate]:
    if not CANDIDATES_FILE.exists():
        return []
    data = json.loads(CANDIDATES_FILE.read_text("utf-8"))
    out: list[Candidate] = []
    for x in data:
        t = (x.get("title") or "").strip()
        u = (x.get("url") or "").strip()
        s = (x.get("source") or "").strip()
        if t and u:
            out.append(Candidate(title=t, url=u, source=s))
    return out


# def build_document_candidates() -> list[dict]:
#     mode = os.getenv("DOC_INPUT_MODE", "gdrive").lower()
#     debug(f"Docs: collector: building doc candidates (mode={mode})")

#     if mode == "gdrive":
#         src = GDriveSource(
#             os.getenv("GDRIVE_INPUT_FOLDER_NAME", "tslac_input"),
#             os.getenv("GDRIVE_ARCHIVE_FOLDER_NAME", "tslac_saved"),
#         )
#     elif mode == "local":
#         src = LocalDirSource(
#             os.environ["LOCAL_INPUT_DIR"],
#             os.environ["LOCAL_ARCHIVE_DIR"],
#         )
#     else:
#         raise RuntimeError(f"Unknown DOC_INPUT_MODE: {mode}")

#     docs = build_doc_candidates(src)
#     info(f"Docs: collector: built {len(docs)} doc candidate(s)")
#     return docs


def build_document_candidates():
    mode = os.getenv("DOC_INPUT_MODE", "gdrive").lower()
    info(f"Docs: building doc candidates (mode={mode})")
    if mode == "gdrive":
        src = GDriveSource(
            os.getenv("GDRIVE_INPUT_FOLDER_NAME", "tslac_input"),
            os.getenv("GDRIVE_ARCHIVE_FOLDER_NAME", "tslac_saved"),
        )
    elif mode == "local":
        src = LocalDirSource(
            os.environ["LOCAL_INPUT_DIR"],
            os.environ["LOCAL_ARCHIVE_DIR"],
        )
    else:
        raise RuntimeError(f"Unknown DOC_INPUT_MODE: {mode}")
    return build_doc_candidates(src)
