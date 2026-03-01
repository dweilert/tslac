from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import cleaner
from storage.collector_store import load_candidates_file
from storage.curation_store import (
    add_curated_excerpt,
    clear_curated_excerpts,
    clear_curated_selected_image,
    get_curated_blurb,
    get_curated_excerpts,
    get_curated_image_crops,
    get_curated_selected_image,
    load_curation,
    pop_curated_excerpt,
    upsert_curated_blurb,
    upsert_curated_image_crop,
    upsert_curated_selected_image,
)
from web.errors import BadRequestError


@dataclass(frozen=True)
class CurateArticleView:
    idx: int
    total: int
    candidate: Any
    cleaned: dict[str, Any]
    final_blurb: str
    excerpts: list[str]
    selected_image: str
    crops: dict[str, Any]


def build_view_by_index(idx: int) -> CurateArticleView:
    candidates = load_candidates_file()
    if not candidates:
        raise BadRequestError(
            "No candidates available. Go back and click Refresh candidates first."
        )

    if idx < 0 or idx >= len(candidates):
        raise BadRequestError(f"Index out of range: {idx} (0..{len(candidates)-1})")

    c = candidates[idx]
    res = cleaner.clean_article(c.url)

    cleaned = {
        "title": res.title,
        "published_date": res.published_date,
        "date_confidence": res.date_confidence,
        "clean_html": res.clean_html,
        "text_plain": res.text_plain,
        "images": res.images,
        "extraction_quality": res.extraction_quality,
    }

    cur = load_curation()
    blurb = get_curated_blurb(cur, c.url)
    excerpts = get_curated_excerpts(cur, c.url)
    selected_image = get_curated_selected_image(cur, c.url)

    try:
        crops = get_curated_image_crops(cur, c.url)
    except Exception:
        crops = {}

    return CurateArticleView(
        idx=idx,
        total=len(candidates),
        candidate=c,
        cleaned=cleaned,
        final_blurb=blurb,
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

    # Only allow http(s)
    if img_src and not (img_src.startswith("http://") or img_src.startswith("https://")):
        img_src = ""

    if url and img_src:
        upsert_curated_selected_image(url, img_src)


def clear_selected_image(*, url: str) -> None:
    url = (url or "").strip()
    if url:
        clear_curated_selected_image(url)
