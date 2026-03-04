from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import docsys.store as doc_store
import storage.curation_store as curation_store
from web.errors import BadRequestError
from services.curate_article_service import select_image  # adjust import path to match your project


@dataclass(frozen=True)
class CurateDocView:
    idx: int
    total: int
    doc: dict[str, Any]
    final_blurb: str
    excerpts: list[str]
    selected_image: str
    crops: dict[str, Any]


# ----------------------------
# Public API
# ----------------------------
def build_view_by_index(
    idx: int,
    *,
    load_docs: Callable[[], list[dict[str, Any]]] | None = None,
    load_cur: Callable[[], dict[str, Any]] | None = None,
) -> CurateDocView:
    docs = (load_docs or doc_store.load_doc_candidates)() or []
    if not docs:
        raise BadRequestError("No doc candidates available. Go back and refresh docs first.")

    if idx < 0 or idx >= len(docs):
        raise BadRequestError(f"Index out of range: {idx} (0..{len(docs) - 1})")

    d = docs[idx]
    if not isinstance(d, dict) or not (d.get("id") or "").strip():
        raise BadRequestError("Invalid doc candidate record (missing id).")

    doc_id = str(d["id"]).strip()

    cur = (load_cur or curation_store.load_curation)()
    final_blurb = curation_store.get_curated_blurb(cur, doc_id)
    excerpts = curation_store.get_curated_excerpts(cur, doc_id)
    selected_image = curation_store.get_curated_selected_image(cur, doc_id)
    crops = curation_store.get_curated_image_crops(cur, doc_id)

    return CurateDocView(
        idx=idx,
        total=len(docs),
        doc=d,
        final_blurb=final_blurb,
        excerpts=excerpts,
        selected_image=selected_image,
        crops=crops,
    )


def build_view_by_doc_id(
    doc_id: str,
    *,
    load_docs: Callable[[], list[dict[str, Any]]] | None = None,
    load_cur: Callable[[], dict[str, Any]] | None = None,
) -> CurateDocView:
    doc_id = (doc_id or "").strip()
    if not doc_id:
        raise BadRequestError("Missing doc_id")

    docs = (load_docs or doc_store.load_doc_candidates)() or []
    if not docs:
        raise BadRequestError("No doc candidates available. Go back and refresh docs first.")

    idx = next(
        (
            i
            for i, d in enumerate(docs)
            if isinstance(d, dict) and (d.get("id") or "").strip() == doc_id
        ),
        None,
    )
    if idx is None:
        raise BadRequestError(f"Doc not found: {doc_id}")

    return build_view_by_index(int(idx), load_docs=load_docs, load_cur=load_cur)


def save_blurb(
    *,
    doc_id: str,
    final_blurb: str,
    upsert: Callable[[str, str], None] | None = None,
) -> None:
    doc_id = (doc_id or "").strip()
    if not doc_id:
        return
    fn = upsert or curation_store.upsert_curated_blurb
    fn(doc_id, (final_blurb or "").strip())


def add_excerpt(*, doc_id: str, excerpt: str) -> None:
    doc_id = (doc_id or "").strip()
    excerpt = (excerpt or "").strip()
    if doc_id and excerpt:
        curation_store.add_curated_excerpt(doc_id, excerpt)


def pop_excerpt(*, doc_id: str) -> None:
    doc_id = (doc_id or "").strip()
    if doc_id:
        curation_store.pop_curated_excerpt(doc_id)


def clear_excerpts(*, doc_id: str) -> None:
    doc_id = (doc_id or "").strip()
    if doc_id:
        curation_store.clear_curated_excerpts(doc_id)


def compose_blurb_from_excerpts(*, doc_id: str, sep: str = "\n\n") -> str:
    """
    Combine stored excerpts into final blurb and persist it.
    Returns the composed blurb string (may be empty).
    """
    doc_id = (doc_id or "").strip()
    if not doc_id:
        return ""

    cur = curation_store.load_curation()
    excerpts = curation_store.get_curated_excerpts(cur, doc_id) or []
    composed = sep.join([x.strip() for x in excerpts if (x or "").strip()]).strip()
    if composed:
        curation_store.upsert_curated_blurb(doc_id, composed)
    return composed


def save_crop(*, doc_id: str, img_src: str, crop_json: str) -> None:
    doc_id = (doc_id or "").strip()
    img_src = (img_src or "").strip()
    crop_json = (crop_json or "").strip()

    try:
        crop = json.loads(crop_json) if crop_json else {}
    except Exception:
        crop = {}

    if doc_id and img_src and isinstance(crop, dict) and crop:
        curation_store.upsert_curated_image_crop(doc_id, img_src, crop)


# def select_image(*, doc_id: str, img_src: str) -> None:
#     doc_id = (doc_id or "").strip()
#     img_src = (img_src or "").strip()

#     if img_src and not (img_src.startswith("http://") or img_src.startswith("https://")):
#         img_src = ""

#     if doc_id and img_src:
#         curation_store.upsert_curated_selected_image(doc_id, img_src)




def select_image(*, doc_id: str, img_src: str) -> None:
    select_image(content_id=doc_id, img_src=img_src)

def clear_selected_image(*, doc_id: str) -> None:
    doc_id = (doc_id or "").strip()
    if doc_id:
        curation_store.clear_curated_selected_image(doc_id)
