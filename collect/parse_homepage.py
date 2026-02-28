from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .models import RawCandidate


def parse_homepage_candidates(html: str, *, base_url: str) -> list[RawCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[RawCandidate] = []

    # Slideshow / “carousel”
    out.extend(_parse_slideshow(soup, base_url=base_url))

    # “News and Events” list block
    out.extend(_parse_news_block(soup, base_url=base_url))

    # De-dup by URL preserving order
    seen: set[str] = set()
    deduped: list[RawCandidate] = []
    for c in out:
        if c.url in seen:
            continue
        seen.add(c.url)
        deduped.append(c)

    return deduped


def _parse_slideshow(soup: BeautifulSoup, *, base_url: str) -> list[RawCandidate]:
    candidates: list[RawCandidate] = []

    block = soup.select_one("#block-tslac-views-block-wr-homepage-slideshow-block-1")
    if not block:
        return candidates

    seen: set[str] = set()

    # Each slide is a views_slideshow_cycle_slide with a nested .views-row
    for slide in block.select(".views_slideshow_cycle_slide, .views_slideshow_slide"):
        # URL is on the image link
        a = slide.select_one(".views-field-field-image a[href]")
        if not a:
            continue
        href = a.get("href")
        if not href:
            continue
        url = urljoin(base_url, href)

        # Title text is in the title field (not inside the <a>)
        title_el = slide.select_one(".views-field-title-1 .field-content")
        title = " ".join(title_el.get_text(" ", strip=True).split()) if title_el else ""

        # If title missing, still skip (or keep with placeholder) — your choice.
        if not title:
            continue

        if url in seen:
            continue
        seen.add(url)

        candidates.append(RawCandidate(title=title, url=url, source="carousel"))

    return candidates


def _parse_news_block(soup: BeautifulSoup, *, base_url: str) -> list[RawCandidate]:
    """
    News front page block:
      block id: block-tslac-views-block-news-front-page-block
      title field: .views-field-title a[href]
    """
    candidates: list[RawCandidate] = []

    block = soup.select_one("#block-tslac-views-block-news-front-page-block")
    if not block:
        return candidates

    for a in block.select(".views-field-title a[href]"):
        title = " ".join(a.get_text(" ", strip=True).split())
        href = a.get("href")
        if not title or not href:
            continue

        # Skip the “See More News and Events >>” which points to "info"
        if href.strip() == "info":
            continue

        url = urljoin(base_url, href)
        candidates.append(RawCandidate(title=title, url=url, source="featured"))

    return candidates
