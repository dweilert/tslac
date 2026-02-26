# cleaner.py
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# import certifi
# requests.get(url, verify=certifi.where())
# httpx.Client(verify=certifi.where())

# ----------------------------
# Cleaner config
# ----------------------------
UA = {"User-Agent": "newsletter-bot/1.0 (local script)"}

MAIN_SELECTORS = [
    "main",
    "article",
    ".node__content",
    ".field--name-body",
    ".field--type-text-with-summary",
    ".layout-content .region-content",
    ".region-content",
    "#content",
    ".layout-content",
]

# Remove obvious noise blocks (by tag)
NOISE_TAGS = {"nav", "header", "footer", "aside", "form", "noscript", "script", "style"}

# Remove blocks by keyword in class/id
NOISE_KEYWORDS = [
    "breadcrumb",
    "sidebar",
    "menu",
    "navigation",
    "pager",
    "pagination",
    "share",
    "social",
    "addthis",
    "cookie",
    "consent",
    "subscribe",
    "calendar",
    "search",
    "utility",
    "related",
    "recommended",
]

# Image junk filtering
IMG_BAD_KEYWORDS = ["icon", "sprite", "favicon", "seal", "badge", "pixel", "tracker", "1x1"]


@dataclass
class CleanResult:
    url: str
    title: str
    published_date: Optional[str]
    date_confidence: str
    clean_html: str
    text_plain: str
    images: List[Dict[str, Any]]
    extraction_quality: str


# ----------------------------
# Fetch
# ----------------------------
def fetch_html(url: str, timeout: int = 30) -> str:
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r.text

# ----------------------------
# Helpers
# ----------------------------
def _tag_attr(tag, attr: str):
    """Safe tag.get(attr): returns None if tag is None."""
    if tag is None:
        return None
    try:
        return tag.get(attr)
    except Exception:
        return None


def _meta_content(soup, *, name: str | None = None, prop: str | None = None):
    """Safe meta content fetcher: <meta name=... content=...> or <meta property=... content=...>."""
    if prop:
        tag = soup.find("meta", attrs={"property": prop})
        val = _tag_attr(tag, "content")
        return val.strip() if isinstance(val, str) and val.strip() else None
    if name:
        tag = soup.find("meta", attrs={"name": name})
        val = _tag_attr(tag, "content")
        return val.strip() if isinstance(val, str) and val.strip() else None
    return None


# ----------------------------
# Utilities
# ----------------------------
def _norm_url(u: str) -> str:
    p = urlparse(u.strip())
    return p._replace(fragment="").geturl()


def _abs(base_url: str, href: str) -> str:
    return _norm_url(urljoin(base_url, href))


def _text_len(el) -> int:
    # Count meaningful-ish text characters
    txt = el.get_text(" ", strip=True) if el else ""
    return len(txt)


def _link_density(el) -> float:
    if not el:
        return 0.0
    text = el.get_text(" ", strip=True) or ""
    words = max(1, len(text.split()))
    links = len(el.find_all("a", href=True))
    return links / words


def _strip_noise(container):
    # Always remove the footer block if it appears inside extracted content
    for t in list(container.select("#tslac-footer")):
        try:
            t.decompose()
        except Exception:
            pass

    # Remove by tags
    for t in list(container.find_all(list(NOISE_TAGS))):
        try:
            t.decompose()
        except Exception:
            pass

    # Remove by class/id keywords (be defensive: some tags become "detached")
    for t in list(container.find_all(True)):
        # If a tag was decomposed earlier, bs4 can leave a detached object with attrs=None
        try:
            attrs = getattr(t, "attrs", None)
            if not isinstance(attrs, dict):
                continue

            cls_list = attrs.get("class") or []
            if not isinstance(cls_list, list):
                cls_list = [str(cls_list)]

            cls = " ".join(str(x) for x in cls_list).lower()
            _id = str(attrs.get("id") or "").lower()
            hay = f"{cls} {_id}".strip()

            if any(k in hay for k in NOISE_KEYWORDS):
                try:
                    t.decompose()
                except Exception:
                    pass
        except Exception:
            # Last-resort: never let cleaning crash the whole page
            continue


def _absolutize_links(container: BeautifulSoup, base_url: str) -> None:
    for a in container.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("javascript:"):
            a.unwrap()
            continue
        a["href"] = _abs(base_url, href)


def _absolutize_images(container: BeautifulSoup, base_url: str) -> None:
    for img in container.find_all("img"):
        src = (img.get("src") or "").strip()
        if not src:
            continue
        img["src"] = _abs(base_url, src)


def _pick_main_container(soup: BeautifulSoup) -> Optional[BeautifulSoup]:
    best = None
    best_score = -1

    for sel in MAIN_SELECTORS:
        for cand in soup.select(sel):
            # quick heuristics
            tlen = _text_len(cand)
            if tlen < 200:
                continue
            dens = _link_density(cand)
            # penalize menu-like containers
            score = tlen - int(dens * 800)
            if score > best_score:
                best_score = score
                best = cand

    return best

def _extract_title(soup) -> str:
    og = _meta_content(soup, prop="og:title")
    if og:
        return og

    tw = _meta_content(soup, name="twitter:title")
    if tw:
        return tw

    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(" ", strip=True)

    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(" ", strip=True)

    return "Untitled"



_DATE_RE_1 = re.compile(
    r"\b(?:Mon|Tue|Tues|Wed|Thu|Thur|Fri|Sat|Sun)[a-z]*,\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(\d{1,2}),\s+(\d{4})\b",
    re.I,
)
_DATE_RE_2 = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(\d{1,2}),\s+(\d{4})\b",
    re.I,
)


def _extract_date(soup: BeautifulSoup, container: Optional[BeautifulSoup]) -> tuple[Optional[str], str]:
    # 1) <time datetime="...">
    t = soup.find("time")
    if t and t.get("datetime"):
        dt = t["datetime"].strip()
        # best effort normalize
        try:
            # allow ISO-ish prefixes
            iso = dt[:19]
            datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return iso, "high"
        except Exception:
            return dt, "medium"

    # 2) meta published time
    for key in ["article:published_time", "article:modified_time"]:
        m = soup.find("meta", attrs={"property": key})
        if m and m.get("content"):
            return m["content"].strip(), "medium"

    # 3) pattern match near the top of container
    hay = ""
    if container:
        hay = container.get_text("\n", strip=True)[:2000]
    else:
        hay = soup.get_text("\n", strip=True)[:2000]

    m1 = _DATE_RE_1.search(hay)
    if m1:
        month, day, year = m1.group(1), m1.group(2), m1.group(3)
        try:
            dt = datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date().isoformat()
            return dt, "medium"
        except Exception:
            return m1.group(0), "low"

    m2 = _DATE_RE_2.search(hay)
    if m2:
        month, day, year = m2.group(1), m2.group(2), m2.group(3)
        try:
            dt = datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date().isoformat()
            return dt, "medium"
        except Exception:
            return m2.group(0), "low"

    return None, "none"


def _collect_images(container: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
    imgs: List[Dict[str, Any]] = []

    # Prefer container images first
    for img in container.find_all("img"):
        src = (img.get("src") or "").strip()
        if not src:
            continue
        abs_src = _abs(base_url, src)
        alt = (img.get("alt") or "").strip()

        # dimensions if present
        w = _safe_int(img.get("width"))
        h = _safe_int(img.get("height"))

        # keyword filters

        low = abs_src.lower()
        penalty = 0.0
        if "logo" in low:
            penalty += 0.35
        if alt and "logo" in alt.lower():
            penalty += 0.35


        if any(k in low for k in IMG_BAD_KEYWORDS):
            continue
        if alt and any(k in alt.lower() for k in IMG_BAD_KEYWORDS):
            continue

        # size filter (weak if unknown)
        if w is not None and w < 250:
            continue
        if h is not None and h < 150:
            continue

        # score = 0.0
        # if w and h:
        #     score += min(1.0, (w * h) / (1200 * 675))
        # if alt:
        #     score += 0.1

        score = 0.0
        if w and h:
            score += min(1.0, (w * h) / (1200 * 675))
        else:
            # unknown dims: give small baseline
            score += 0.15

        if alt:
            score += 0.05

        score = max(0.0, score - penalty)


        imgs.append({"src": abs_src, "alt": alt, "width": w, "height": h, "score": round(score, 3)})

    # If none found, consider og:image as fallback
    if not imgs:
        og = container.find_parent().find("meta", attrs={"property": "og:image"}) if container.find_parent() else None
        if og and og.get("content"):
            imgs.append({"src": _abs(base_url, og["content"].strip()), "alt": "", "width": None, "height": None, "score": 0.5})

    # Sort best-first
    imgs.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Dedupe by src
    seen = set()
    out = []
    for it in imgs:
        s = it["src"]
        if s not in seen:
            out.append(it)
            seen.add(s)
    return out


def _safe_int(x) -> Optional[int]:
    try:
        if x is None:
            return None
        return int(str(x).strip())
    except Exception:
        return None


# ----------------------------
# Public API
# ----------------------------
def clean_article(url: str) -> CleanResult:
    url = _norm_url(url)
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    container = _pick_main_container(soup)
    extraction_quality = "high" if container else "low"

    if not container:
        # last resort: use body
        container = soup.body or soup

    # Work on a copy-ish: wrap selected content in a new soup fragment
    frag = BeautifulSoup(str(container), "html.parser")

    if frag is None:
        raise ValueError("Could not locate a main content container")

    _strip_noise(frag)
    _absolutize_links(frag, url)
    _absolutize_images(frag, url)

    title = _extract_title(soup)
    pub_date, conf = _extract_date(soup, frag)

    images = _collect_images(frag, url)

    # Clean HTML payload: keep just the fragment
    clean_html = str(frag)

    # Plain text: paragraphs split
    text_plain = frag.get_text("\n", strip=True)

    return CleanResult(
        url=url,
        title=title,
        published_date=pub_date,
        date_confidence=conf,
        clean_html=clean_html,
        text_plain=text_plain,
        images=images,
        extraction_quality=extraction_quality,
    )
