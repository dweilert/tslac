from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import services.api_service as api_service
import storage.collector_store as collector_store
import storage.curation_store as curation_store
from web.errors import BadRequestError


@dataclass(frozen=True)
class CurateView:
    idx: int
    total: int
    candidate: Any
    cleaned: dict[str, Any]
    final_blurb: str
    excerpts: list[str]
    selected_image: str
    crops: dict[str, Any]


# ----------------------------
# Helpers
# ----------------------------
def _get_attr(obj: Any, name: str, default: Any = "") -> Any:
    try:
        return getattr(obj, name)
    except Exception:
        return default


def _cand_url(c: Any) -> str:
    if c is None:
        return ""
    if isinstance(c, dict):
        return (c.get("url") or c.get("original_url") or "").strip()
    return str(_get_attr(c, "url", "") or _get_attr(c, "original_url", "") or "").strip()


def _cand_title(c: Any) -> str:
    if c is None:
        return ""
    if isinstance(c, dict):
        return str(c.get("title") or "")
    return str(_get_attr(c, "title", "") or "")


def _build_cleaned_from_payload(payload: dict[str, Any], fallback_title: str) -> dict[str, Any]:
    """
    Normalize api_service output into a shape templates expect.
    """
    payload = payload or {}

    title = (
        (payload.get("title") or "").strip() or (fallback_title or "").strip() or "Curate Article"
    )

    html = payload.get("html") or payload.get("content_html") or payload.get("cleaned_html") or ""
    if not isinstance(html, str):
        html = str(html or "")

    images = payload.get("images") or payload.get("image_candidates") or []
    if not isinstance(images, list):
        images = []

    return {
        "title": title,
        "html": html,
        "content_html": html,
        "cleaned_html": html,
        "images": images,
    }


# ----------------------------
# Public API
# ----------------------------
def build_view_by_index(
    idx: int,
    *,
    load_candidates: Callable[[], list[Any]] | None = None,
    fetch_payload: Callable[[str], dict[str, Any]] | None = None,
    load_cur: Callable[[], dict[str, Any]] | None = None,
) -> CurateView:
    """
    Build the Curate view model for an article candidate index.

    Dependency injection points (for tests):
      - load_candidates: returns list of candidates (dicts or objects)
      - fetch_payload: returns dict with keys like title/html/images
      - load_cur: returns parsed curation dict
    """
    cands = (load_candidates or collector_store.load_candidates_file)()
    if not cands:
        raise BadRequestError("No candidates. Go back and refresh candidates first.")

    if idx < 0 or idx >= len(cands):
        raise BadRequestError(f"Index out of range: {idx} (0..{len(cands) - 1})")

    c = cands[idx]
    url = _cand_url(c)
    if not url:
        raise BadRequestError("Candidate missing url.")

    fallback_title = _cand_title(c)

    payload = (fetch_payload or api_service.clean_article_payload)(url)
    cleaned = _build_cleaned_from_payload(payload, fallback_title)

    cur = (load_cur or curation_store.load_curation)()
    final_blurb = curation_store.get_curated_blurb(cur, url)
    excerpts = curation_store.get_curated_excerpts(cur, url)
    selected_image = curation_store.get_curated_selected_image(cur, url)
    crops = curation_store.get_curated_image_crops(cur, url)

    return CurateView(
        idx=idx,
        total=len(cands),
        candidate=c,
        cleaned=cleaned,
        final_blurb=final_blurb,
        excerpts=excerpts,
        selected_image=selected_image,
        crops=crops,
    )


def save_blurb(*, url: str, final_blurb: str) -> None:
    url = (url or "").strip()
    if url:
        curation_store.upsert_curated_blurb(url, (final_blurb or "").strip())


def add_excerpt(*, url: str, excerpt: str) -> None:
    url = (url or "").strip()
    excerpt = (excerpt or "").strip()
    if url and excerpt:
        curation_store.add_curated_excerpt(url, excerpt)


def pop_excerpt(*, url: str) -> None:
    url = (url or "").strip()
    if url:
        curation_store.pop_curated_excerpt(url)


def clear_excerpts(*, url: str) -> None:
    url = (url or "").strip()
    if url:
        curation_store.clear_curated_excerpts(url)


def delete_excerpt(*, url: str, excerpt_index: int) -> None:
    url = (url or "").strip()
    if not url:
        return
    try:
        i = int(excerpt_index)
    except Exception:
        return
    curation_store.delete_curated_excerpt(url, i)


def move_excerpt(*, url: str, excerpt_index: int, direction: str) -> None:
    url = (url or "").strip()
    if not url:
        return
    try:
        i = int(excerpt_index)
    except Exception:
        return
    curation_store.move_curated_excerpt(url, i, direction)


def compose_blurb_from_excerpts(*, url: str, sep: str = "\n\n") -> str:
    """
    Combine stored excerpts into final blurb and persist it.
    Returns the composed blurb string (may be empty).
    """
    url = (url or "").strip()
    if not url:
        return ""

    cur = curation_store.load_curation()
    xs = curation_store.get_curated_excerpts(cur, url) or []
    composed = sep.join([x.strip() for x in xs if (x or "").strip()]).strip()
    if composed:
        curation_store.upsert_curated_blurb(url, composed)
    return composed


def save_crop(*, url: str, img_src: str, crop_json: str) -> None:
    url = (url or "").strip()
    img_src = (img_src or "").strip()
    crop_json = (crop_json or "").strip()

    try:
        crop = json.loads(crop_json) if crop_json else {}
    except Exception:
        crop = {}

    if url and img_src and isinstance(crop, dict) and crop:
        curation_store.upsert_curated_image_crop(url, img_src, crop)


def select_image(*, url: str, img_src: str) -> None:
    url = (url or "").strip()
    img_src = (img_src or "").strip()

    # Only allow absolute http(s) for now (consistent with your prior behavior)
    if img_src and not (img_src.startswith("http://") or img_src.startswith("https://")):
        img_src = ""

    if url and img_src:
        curation_store.upsert_curated_selected_image(url, img_src)


def clear_selected_image(*, url: str) -> None:
    url = (url or "").strip()
    if url:
        curation_store.clear_curated_selected_image(url)
