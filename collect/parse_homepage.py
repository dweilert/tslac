# collect/parse_homepage.py
from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from logutil import debug

from .models import RawCandidate


def parse_homepage_candidates(html: str, *, base_url: str) -> list[RawCandidate]:
    from logutil import info

    debug(f"parse_homepage: start html_len={len(html)} base_url={base_url}")

    soup = BeautifulSoup(html, "html.parser")
    # info("DEBUG parse_homepage: soup built")

    out: list[RawCandidate] = []

    # Carousel / slideshow
    # info("DEBUG parse_homepage: parsing slideshow...")
    slides = _parse_slideshow(soup, base_url=base_url)
    debug(f"parse_homepage: slideshow count={len(slides)}")
    out.extend(slides)

    # Featured News (if implemented)
    if "_parse_featured_news" in globals():
        # info("DEBUG parse_homepage: parsing featured...")
        featured = _parse_featured_news(soup, base_url=base_url)
        debug(f"parse_homepage: featured count={len(featured)}")
        out.extend(featured)
    else:
        info("DEBUG parse_homepage: featured parser not implemented (skipping)")

    # De-dup by URL preserving order
    debug(f"parse_homepage: dedup input count={len(out)}")
    seen: set[str] = set()
    deduped: list[RawCandidate] = []
    for c in out:
        if c.url in seen:
            continue
        seen.add(c.url)
        deduped.append(c)

    debug(f"parse_homepage: done deduped count={len(deduped)}")
    return deduped


def _parse_featured_news(soup: BeautifulSoup, *, base_url: str) -> list[RawCandidate]:
    out: list[RawCandidate] = []

    h2 = None
    for node in soup.find_all("h2"):
        txt = node.get_text(" ", strip=True)
        if "Featured News" in txt:
            h2 = node
            break
    debug(f"featured: h2 found={bool(h2)}")
    if h2 is None:
        return out

    # Iterate forward, but only consider <a> tags (cheaper) and stop at next h2
    for a in h2.find_all_next("a"):
        # stop if we crossed into next section
        prev_h2 = a.find_previous("h2")
        if prev_h2 is not None and prev_h2 is not h2:
            break

        text = a.get_text(" ", strip=True)
        if not text:
            continue

        if "See More News and Events" in text:
            break

        href = (a.get("href") or "").strip()
        if not href or href == "#" or href.startswith(("mailto:", "tel:")):
            continue

        out.append(
            RawCandidate(
                title=text,
                url=urljoin(base_url, href),
                source="Featured",
                summary=None,
            )
        )

    return _dedup_raw_by_url(out)


# def _parse_featured_news(soup: BeautifulSoup, *, base_url: str) -> list[RawCandidate]:
#     out: list[RawCandidate] = []

#     # 1) Find the Featured News heading
#     h2 = None
#     for node in soup.find_all("h2"):
#         txt = node.get_text(" ", strip=True)
#         if txt == "Featured News" or "Featured News" in txt:
#             h2 = node
#             break
#     if h2 is None:
#         return out

#     # 2) Walk forward collecting links until the end marker or the next h2
#     for el in h2.find_all_next():
#         # stop at next section heading to avoid bleeding into other homepage areas
#         if el.name == "h2" and el is not h2:
#             break

#         if el.name != "a":
#             continue

#         text = el.get_text(" ", strip=True)
#         if not text:
#             continue

#         if "See More News and Events" in text:
#             break

#         href = (el.get("href") or "").strip()
#         if not href or href == "#" or href.startswith(("mailto:", "tel:")):
#             continue

#         out.append(
#             RawCandidate(
#                 title=text,
#                 url=urljoin(base_url, href),
#                 source="Featured",
#                 summary=None,
#             )
#         )

#     # De-dupe featured URLs
#     seen: set[str] = set()
#     deduped: list[RawCandidate] = []
#     for c in out:
#         if c.url in seen:
#             continue
#         seen.add(c.url)
#         deduped.append(c)
#     return deduped


def _dedup_raw_by_url(items: list[RawCandidate]) -> list[RawCandidate]:
    seen: set[str] = set()
    out: list[RawCandidate] = []
    for c in items:
        if c.url in seen:
            continue
        seen.add(c.url)
        out.append(c)
    return out


def _parse_slideshow(soup: BeautifulSoup, *, base_url: str) -> list[RawCandidate]:

    candidates: list[RawCandidate] = []

    # info("DEBUG slideshow: locating slideshow block...")
    block = soup.select_one("#block-tslac-views-block-wr-homepage-slideshow-block-1")
    debug(f"slideshow: block found={bool(block)}")
    if not block:
        return candidates

    # info("DEBUG slideshow: selecting slide nodes...")
    slides = block.select(".views_slideshow_cycle_slide, .views_slideshow_slide")
    debug(f"slideshow: slide nodes={len(slides)}")

    seen: set[str] = set()

    for idx, slide in enumerate(slides):
        debug(f"slideshow: processing slide {idx+1}/{len(slides)}")

        href = ""
        img_field = slide.find("div", class_="views-field-field-image")
        if img_field:
            a = img_field.find("a", href=True)
            if a:
                href = (a.get("href") or "").strip()
        if not href:
            debug(f"slideshow: no href; skip slide {idx+1}")
            continue

        url = urljoin(base_url, href)

        title = ""
        title_field = slide.find("div", class_="views-field-title-1")
        if title_field:
            fc = title_field.find(class_="field-content")
            if fc:
                title = " ".join(fc.get_text(" ", strip=True).split())
        if not title:
            debug(f"slideshow: no title; skip slide {idx+1}")
            continue

        if url in seen:
            debug(f"slideshow: dup url; skip slide {idx+1}")
            continue
        seen.add(url)

        candidates.append(RawCandidate(title=title, url=url, source="Carousel"))

    debug(f"slideshow: returning candidates={len(candidates)}")
    return candidates


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
