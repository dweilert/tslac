from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from doc_store import load_doc_candidates
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
class CurateDocView:
    idx: int
    total: int
    doc: dict[str, Any]
    final_blurb: str
    excerpts: list[str]
    selected_image: str
    crops: dict[str, Any]


def build_view_by_index(idx: int) -> CurateDocView:
    docs = load_doc_candidates() or []
    if not docs:
        raise BadRequestError("No doc candidates available. Go back and refresh docs first.")

    if idx < 0 or idx >= len(docs):
        raise BadRequestError(f"Index out of range: {idx} (0..{len(docs)-1})")

    d = docs[idx]
    if not isinstance(d, dict) or not d.get("id"):
        raise BadRequestError("Invalid doc candidate record (missing id).")

    doc_id = str(d["id"])

    cur = load_curation()
    blurb = get_curated_blurb(cur, doc_id)
    excerpts = get_curated_excerpts(cur, doc_id)
    selected_image = get_curated_selected_image(cur, doc_id)

    try:
        crops = get_curated_image_crops(cur, doc_id)
    except Exception:
        crops = {}

    return CurateDocView(
        idx=idx,
        total=len(docs),
        doc=d,
        final_blurb=blurb,
        excerpts=excerpts,
        selected_image=selected_image,
        crops=crops,
    )


def build_view_by_doc_id(doc_id: str) -> CurateDocView:
    doc_id = (doc_id or "").strip()
    if not doc_id:
        raise BadRequestError("Missing doc_id")

    docs = load_doc_candidates() or []
    if not docs:
        raise BadRequestError("No doc candidates available. Go back and refresh docs first.")

    idx = next(
        (i for i, d in enumerate(docs) if isinstance(d, dict) and (d.get("id") or "").strip() == doc_id),
        None,
    )
    if idx is None:
        raise BadRequestError(f"Doc not found: {doc_id}")

    return build_view_by_index(int(idx))


def save_blurb(*, doc_id: str, final_blurb: str) -> None:
    doc_id = (doc_id or "").strip()
    if doc_id:
        upsert_curated_blurb(doc_id, (final_blurb or "").strip())


def add_excerpt(*, doc_id: str, excerpt: str) -> None:
    doc_id = (doc_id or "").strip()
    excerpt = (excerpt or "").strip()
    if doc_id and excerpt:
        add_curated_excerpt(doc_id, excerpt)


def pop_excerpt(*, doc_id: str) -> None:
    doc_id = (doc_id or "").strip()
    if doc_id:
        pop_curated_excerpt(doc_id)


def clear_excerpts(*, doc_id: str) -> None:
    doc_id = (doc_id or "").strip()
    if doc_id:
        clear_curated_excerpts(doc_id)


def compose_blurb_from_excerpts(*, doc_id: str, sep: str = "\n\n") -> str:
    """
    Combine stored excerpts into final blurb and persist it.
    Returns the composed blurb string (may be empty).
    """
    doc_id = (doc_id or "").strip()
    if not doc_id:
        return ""

    cur = load_curation()
    excerpts = get_curated_excerpts(cur, doc_id) or []
    composed = sep.join([x.strip() for x in excerpts if (x or "").strip()]).strip()
    if composed:
        upsert_curated_blurb(doc_id, composed)
    return composed


def save_crop(*, doc_id: str, img_src: str, crop_json: str) -> None:
    doc_id = (doc_id or "").strip()
    img_src = (img_src or "").strip()
    crop_json = (crop_json or "").strip()

    try:
        crop = json.loads(crop_json) if crop_json else {}
    except Exception:
        crop = {}

    if doc_id and img_src and crop:
        upsert_curated_image_crop(doc_id, img_src, crop)


def select_image(*, doc_id: str, img_src: str) -> None:
    doc_id = (doc_id or "").strip()
    img_src = (img_src or "").strip()

    if img_src and not (img_src.startswith("http://") or img_src.startswith("https://")):
        img_src = ""

    if doc_id and img_src:
        upsert_curated_selected_image(doc_id, img_src)


def clear_selected_image(*, doc_id: str) -> None:
    doc_id = (doc_id or "").strip()
    if doc_id:
        clear_curated_selected_image(doc_id)