from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from web.errors import BadRequestError


# -----------------------------
# Helpers
# -----------------------------
def _abs(base: str, u: str) -> str:
    u = (u or "").strip()
    if not u:
        return ""
    return urljoin(base, u)


def _pick_main_container(soup: BeautifulSoup):
    """
    Try common "main content" containers.
    This is intentionally heuristic.
    """
    # Strong candidates
    selectors = [
        "main",
        "article",
        "#content",
        "#main",
        ".region-content",
        ".layout-content",
        ".content",
        ".node__content",
        ".field--name-body",
        ".page__content",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            return el

    # fallback: body
    return soup.body or soup


def _strip_noise(root) -> None:
    # Remove obvious noise inside the chosen root
    for sel in [
        "script",
        "style",
        "noscript",
        "svg",
        "header",
        "footer",
        "nav",
        "form",
        "iframe",
        ".breadcrumbs",
        ".breadcrumb",
        ".site-header",
        ".site-footer",
        ".skip-link",
        ".menu",
        ".navigation",
        ".nav",
        ".share",
        ".social",
        ".print",
        ".search",
        ".alert",
    ]:
        for t in list(root.select(sel)):
            t.decompose()


def _build_clean_html(root, *, max_paragraphs: int = 10, max_chars: int = 6000) -> str:
    """
    Keep only useful elements, and limit size so Curate is manageable.
    """
    keep_tags = {"h1", "h2", "h3", "p", "ul", "ol", "li", "blockquote", "strong", "em", "a"}

    out_parts: list[str] = []
    char_count = 0
    p_count = 0

    # Prefer a headline if present
    h1 = root.find(["h1", "h2"])
    if h1:
        out_parts.append(str(h1))
        char_count += len(h1.get_text(" ", strip=True))

    # Then walk paragraphs/lists
    for node in root.find_all(["p", "ul", "ol", "blockquote", "h2", "h3"], recursive=True):
        if node.name == "p":
            txt = node.get_text(" ", strip=True)
            if not txt:
                continue
            p_count += 1
            if p_count > max_paragraphs:
                break

        # prune child tags to keep it clean/selectable
        for child in list(node.find_all(True)):
            if child.name not in keep_tags:
                child.unwrap()

        html = str(node)
        out_parts.append(html)
        char_count += len(node.get_text(" ", strip=True))
        if char_count >= max_chars:
            break

    # If we got nothing, at least return some text
    if not out_parts:
        txt = root.get_text("\n", strip=True)
        return "<pre>" + (txt[:max_chars] if txt else "") + "</pre>"

    return "\n".join(out_parts)


def _extract_images(soup: BeautifulSoup, root, base_url: str, *, max_images: int = 12) -> list[dict[str, Any]]:
    imgs: list[dict[str, Any]] = []

    # 1) og:image is usually the hero image (this is what you likely want)
    og = soup.select_one('meta[property="og:image"], meta[name="og:image"]')
    if og and og.get("content"):
        src = _abs(base_url, og["content"])
        if src:
            imgs.append({"src": src, "alt": "og:image", "score": 1000})

    # 2) images inside main content
    for im in root.select("img"):
        src = im.get("src") or im.get("data-src") or ""
        src = _abs(base_url, src)
        if not src:
            continue
        alt = (im.get("alt") or "").strip()

        # quick scoring: prefer larger-looking images
        score = 0
        w = im.get("width")
        h = im.get("height")
        try:
            if w and h:
                score += int(w) * int(h) // 1000
        except Exception:
            pass

        # Prefer likely hero/banner/logo filenames a bit
        low = src.lower()
        if any(k in low for k in ("hero", "banner", "logo", "header")):
            score += 200

        imgs.append({"src": src, "alt": alt, "score": score})

    # de-dup preserving best score
    best: dict[str, dict[str, Any]] = {}
    for x in imgs:
        s = x["src"]
        if s not in best or (x.get("score", 0) > best[s].get("score", 0)):
            best[s] = x

    imgs2 = sorted(best.values(), key=lambda d: d.get("score", 0), reverse=True)
    return imgs2[:max_images]


# -----------------------------
# Public API used by routes/api.py and Curate
# -----------------------------
def clean_article_payload(url: str) -> dict[str, Any]:
    url = (url or "").strip()
    if not url:
        raise BadRequestError("Missing url")

    # try:
    #     r = requests.get(url, timeout=25, headers={"User-Agent": "tslac-newsletter-helper/1.0"})
    #     r.raise_for_status()
    #     html = r.text
    # except Exception as e:
    #     raise BadRequestError(f"Failed to fetch URL: {url}") from e

    try:
        r = requests.get(
            url,
            timeout=25,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            allow_redirects=True,
        )
        status = r.status_code
        final_url = r.url
        r.raise_for_status()
        html = r.text
    except requests.exceptions.SSLError as e:
        raise BadRequestError(f"SSL error fetching URL: {url} ({e})") from e
    except requests.exceptions.Timeout as e:
        raise BadRequestError(f"Timeout fetching URL: {url} ({e})") from e
    except requests.exceptions.TooManyRedirects as e:
        raise BadRequestError(f"Too many redirects fetching URL: {url} ({e})") from e
    except requests.exceptions.HTTPError as e:
        # include status + final url for debugging
        code = getattr(getattr(e, "response", None), "status_code", None)
        raise BadRequestError(
            f"HTTP {code} fetching URL: {url} (final: {getattr(r,'url',url)})"
        ) from e
    except requests.exceptions.RequestException as e:
        raise BadRequestError(f"Request error fetching URL: {url} ({e})") from e


    soup = BeautifulSoup(html, "lxml")

    # Title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Main content selection + cleanup
    root = _pick_main_container(soup)
    _strip_noise(root)

    cleaned_html = _build_clean_html(root, max_paragraphs=10, max_chars=6000)
    images = _extract_images(soup, root, url, max_images=12)

    return {
        "title": title,
        "html": cleaned_html,   # Curate uses this
        "images": images,       # Curate uses this
    }