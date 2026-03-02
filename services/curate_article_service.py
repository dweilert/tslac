from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from services.api_service import clean_article_payload
from storage.collector_store import load_candidates_file
from storage.curation_store import (
    add_curated_excerpt,
    clear_curated_excerpts,
    clear_curated_selected_image,
    delete_curated_excerpt,
    get_curated_blurb,
    get_curated_excerpts,
    get_curated_image_crops,
    get_curated_selected_image,
    load_curation,
    move_curated_excerpt,
    pop_curated_excerpt,
    upsert_curated_blurb,
    upsert_curated_image_crop,
    upsert_curated_selected_image,
)
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


def _build_cleaned_from_api(url: str, fallback_title: str) -> dict[str, Any]:
    """
    candidates.json only contains metadata, so we fetch/extract on demand via api_service.
    """
    payload = clean_article_payload(url) or {}

    title = payload.get("title") or fallback_title or "Curate Article"
    html = payload.get("html") or payload.get("content_html") or payload.get("cleaned_html") or ""
    if not isinstance(html, str):
        html = str(html or "")

    images = payload.get("images") or payload.get("image_candidates") or []
    if not isinstance(images, list):
        images = []

    # templates.py is tolerant, but we provide all common keys
    return {
        "title": title,
        "html": html,
        "content_html": html,
        "cleaned_html": html,
        "images": images,
    }


def build_view_by_index(idx: int) -> CurateView:
    cands = load_candidates_file()
    if not cands:
        raise BadRequestError("No candidates. Go back and refresh candidates first.")

    if idx < 0 or idx >= len(cands):
        raise BadRequestError(f"Index out of range: {idx} (0..{len(cands)-1})")

    c = cands[idx]
    url = _cand_url(c)
    if not url:
        raise BadRequestError("Candidate missing url.")

    fallback_title = _cand_title(c)
    cleaned = _build_cleaned_from_api(url, fallback_title)

    cur = load_curation()
    final_blurb = get_curated_blurb(cur, url)
    excerpts = get_curated_excerpts(cur, url)
    selected_image = get_curated_selected_image(cur, url)
    crops = get_curated_image_crops(cur, url)

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
        upsert_curated_blurb(url, (final_blurb or "").strip())


def add_excerpt(*, url: str, excerpt: str) -> None:
    url = (url or "").strip()
    excerpt = (excerpt or "").strip()
    if url and excerpt:
        add_curated_excerpt(url, excerpt)


def pop_excerpt(*, url: str) -> None:
    url = (url or "").strip()
    if url:
        pop_curated_excerpt(url)


def clear_excerpts(*, url: str) -> None:
    url = (url or "").strip()
    if url:
        clear_curated_excerpts(url)


def delete_excerpt(*, url: str, excerpt_index: int) -> None:
    url = (url or "").strip()
    if not url:
        return
    try:
        i = int(excerpt_index)
    except Exception:
        return
    delete_curated_excerpt(url, i)


def move_excerpt(*, url: str, excerpt_index: int, direction: str) -> None:
    url = (url or "").strip()
    if not url:
        return
    try:
        i = int(excerpt_index)
    except Exception:
        return
    move_curated_excerpt(url, i, direction)


def compose_blurb_from_excerpts(*, url: str, sep: str = "\n\n") -> str:
    url = (url or "").strip()
    if not url:
        return ""

    cur = load_curation()
    xs = get_curated_excerpts(cur, url) or []
    composed = sep.join([x.strip() for x in xs if (x or "").strip()]).strip()
    if composed:
        upsert_curated_blurb(url, composed)
    return composed


def save_crop(*, url: str, img_src: str, crop_json: str) -> None:
    url = (url or "").strip()
    img_src = (img_src or "").strip()
    crop_json = (crop_json or "").strip()

    try:
        crop = json.loads(crop_json) if crop_json else {}
    except Exception:
        crop = {}

    if url and img_src and crop:
        upsert_curated_image_crop(url, img_src, crop)


def select_image(*, url: str, img_src: str) -> None:
    url = (url or "").strip()
    img_src = (img_src or "").strip()

    if img_src and not (img_src.startswith("http://") or img_src.startswith("https://")):
        img_src = ""

    if url and img_src:
        upsert_curated_selected_image(url, img_src)


def clear_selected_image(*, url: str) -> None:
    url = (url or "").strip()
    if url:
        clear_curated_selected_image(url)
