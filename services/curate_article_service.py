# services/curate_article_service.py
# services/curate_article_service.py
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import docsys.store as doc_store
import services.api_service as api_service
import storage.collector_store as collector_store
import storage.curation_store as curation_store
from services.candidates_service import get_candidate_id
from storage.content_id import canonical_content_id, real_web_url
from web.errors import BadRequestError


@dataclass(frozen=True)
class CurateView:
    idx: int
    total: int
    candidate: Any
    candidate_id: str
    content_id: str
    cleaned: dict[str, Any]
    final_blurb: str
    excerpts: list[str]
    selected_image: str
    crops: dict[str, Any]
    curated_title: str = ""
    curated_subtitle: str = ""

# ----------------------------
# Helpers
# ----------------------------
def _get_attr(obj: Any, name: str, default: Any = "") -> Any:
    try:
        return getattr(obj, name)
    except Exception:
        return default

def _canon_content_id(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    # already canonical
    if s.startswith(("web:", "gdrive:", "local:")):
        return s
    # plain web URL → canonical
    if s.startswith(("http://", "https://")):
        return f"web:{s}"
    return s

def _web_key(u: str) -> str:
    """
    Canonical key for web articles in curation.yaml.
    Always returns 'web:<real_url>' for http(s) pages.
    If passed 'web:https://..' it returns it unchanged.
    """
    u = (u or "").strip()
    if not u:
        return ""
    return u if u.startswith("web:") else f"web:{u}"


# def real_web_url(content_id: str) -> str:
#     s = (content_id or "").strip()
#     if s.startswith("web:"):
#         s = s[4:]
#     return s



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


def _cand_id(c: Any) -> str:
    """
    Canonical content id for curation keys.
    For now:
      - if candidate has 'id', use it
      - else fall back to web:<url>
    """
    if c is None:
        return ""
    if isinstance(c, dict):
        cid = (c.get("id") or "").strip()
        if cid:
            return cid
        url = (c.get("url") or "").strip()
        return f"web:{url}" if url else ""
    cid = str(_get_attr(c, "id", "") or "").strip()
    if cid:
        return cid
    url = _cand_url(c)
    return f"web:{url}" if url else ""


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
    """
    cands = (load_candidates or collector_store.load_candidates_file)()
    if not cands:
        raise BadRequestError("No candidates. Go back and refresh candidates first.")
    if idx < 0 or idx >= len(cands):
        raise BadRequestError(f"Index out of range: {idx} (0..{len(cands) - 1})")

    c = cands[idx]
    raw_url = (_cand_url(c) or "").strip()
    if not raw_url:
        raise BadRequestError("Candidate missing url.")
    # Canonical curation key (what you store in curation.yaml)
    content_id = canonical_content_id(source="web", raw=raw_url)
    if not content_id:
        raise BadRequestError("Candidate missing url.")

    page_url = real_web_url(content_id)
    # page_url = raw_url
    fallback_title = _cand_title(c)

    payload = (fetch_payload or api_service.clean_article_payload)(page_url)
    if not isinstance(payload, dict):
        payload = {}

    cleaned = _build_cleaned_from_payload(payload, fallback_title)

    cur = (load_cur or curation_store.load_curation)()

    final_blurb = curation_store.get_curated_blurb(cur, content_id)
    excerpts = curation_store.get_curated_excerpts(cur, content_id)
    selected_image = curation_store.get_curated_selected_image(cur, content_id)
    crops = curation_store.get_curated_image_crops(cur, content_id)
    curated_title = curation_store.get_curated_title(cur, content_id)
    curated_subtitle = curation_store.get_curated_subtitle(cur, content_id)
    candidate_id = get_candidate_id(c)

    return CurateView(
        idx=idx,
        total=len(cands),
        candidate=c,
        candidate_id=candidate_id,   # ✅
        content_id=content_id,       # ✅
        cleaned=cleaned,             # (keep as dict)
        final_blurb=final_blurb,
        excerpts=excerpts,
        selected_image=selected_image,
        crops=crops,
        curated_title=curated_title,
        curated_subtitle=curated_subtitle,
    )



# def save_title(*, url: str, title: str) -> None:
#     key = _canon_content_id(url)  # if you added canonicalizer; otherwise just url.strip()
#     if key:
#         curation_store.upsert_curated_title(key, (title or "").strip())


# def save_subtitle(*, url: str, subtitle: str) -> None:
#     key = _canon_content_id(url)  # if you added canonicalizer; otherwise just url.strip()
#     if key:
#         curation_store.upsert_curated_subtitle(key, (subtitle or "").strip())

def save_title(*, url: str, title: str) -> None:
    key = (url or "").strip()
    if key:
        curation_store.upsert_curated_title(key, (title or "").strip())

def save_subtitle(*, url: str, subtitle: str) -> None:
    key = (url or "").strip()
    if key:
        curation_store.upsert_curated_subtitle(key, (subtitle or "").strip())


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



# Back-compat wrapper (optional, but avoids touching other callers yet)
def select_image_for_url(*, url: str, img_src: str) -> None:
    select_image(content_id=url, img_src=img_src)


def save_blurb(*, url: str, final_blurb: str) -> None:
    key = _canon_content_id(url)
    if key:
        curation_store.upsert_curated_blurb(key, (final_blurb or "").strip())


def add_excerpt(*, url: str, excerpt: str) -> None:
    key = _canon_content_id(url)
    excerpt = (excerpt or "").strip()
    if key and excerpt:
        curation_store.add_curated_excerpt(key, excerpt)


def pop_excerpt(*, url: str) -> None:
    key = _canon_content_id(url)
    if key:
        curation_store.pop_curated_excerpt(key)


def clear_excerpts(*, url: str) -> None:
    key = _canon_content_id(url)
    if key:
        curation_store.clear_curated_excerpts(key)


def delete_excerpt(*, url: str, excerpt_index: int) -> None:
    key = _canon_content_id(url)
    if not key:
        return
    try:
        i = int(excerpt_index)
    except Exception:
        return
    curation_store.delete_curated_excerpt(key, i)


def move_excerpt(*, url: str, excerpt_index: int, direction: str) -> None:
    key = _canon_content_id(url)
    if not key:
        return
    try:
        i = int(excerpt_index)
    except Exception:
        return
    curation_store.move_curated_excerpt(key, i, direction)


def select_image(*, content_id: str | None = None, url: str | None = None, img_src: str) -> None:
    # Back-compat: older code/tests pass url=
    key = _canon_content_id((content_id or url or "").strip())
    img_src = (img_src or "").strip()
    if not key:
        return

    if not img_src:
        curation_store.clear_curated_selected_image(key)
        return

    if not (img_src.startswith("http://") or img_src.startswith("https://")):
        return

    curation_store.upsert_curated_selected_image(key, img_src)


def clear_selected_image(*, url: str) -> None:
    key = _canon_content_id(url)
    if key:
        curation_store.clear_curated_selected_image(key)





def build_view_by_content_id(
    content_id: str,
    *,
    load_candidates: Callable[[], list[Any]] | None = None,
    load_docs: Callable[[], list[dict[str, Any]]] | None = None,
    fetch_payload: Callable[[str], dict[str, Any]] | None = None,
    load_cur: Callable[[], dict[str, Any]] | None = None,
) -> CurateView:
    """
    Unified builder for BOTH web:* and gdrive:* content IDs.
    Returns CurateView suitable for templates.curate_page_html/curate_article.html.
    """
    cid = (content_id or "").strip()
    if not cid:
        raise BadRequestError("Missing id")

    cur = (load_cur or curation_store.load_curation)()

    # --- WEB ---
    if cid.startswith("web:"):
        page_url = real_web_url(cid)
        if not page_url:
            raise BadRequestError("Invalid web id")

        # Find candidate + idx (needed for prev/next, display, etc.)
        cands = (load_candidates or collector_store.load_candidates_file)()
        if not cands:
            raise BadRequestError("No candidates. Go back and refresh candidates first.")

        idx = None
        cand = None
        for i, c in enumerate(cands):
            raw_url = (_cand_url(c) or "").strip()
            if not raw_url:
                continue
            c_cid = canonical_content_id(source="web", raw=raw_url)
            if c_cid == cid:
                idx = i
                cand = c
                break

        if idx is None or cand is None:
            raise BadRequestError(f"Candidate not found for id={cid}")

        payload = (fetch_payload or api_service.clean_article_payload)(page_url)
        cleaned = _build_cleaned_from_payload(payload, _cand_title(cand))

        return CurateView(
            idx=idx,
            total=len(cands),
            candidate=cand,
            candidate_id=cid,   # for now treat same; you can refine later
            content_id=cid,
            cleaned=cleaned,
            final_blurb=curation_store.get_curated_blurb(cur, cid),
            excerpts=curation_store.get_curated_excerpts(cur, cid),
            selected_image=curation_store.get_curated_selected_image(cur, cid),
            crops=curation_store.get_curated_image_crops(cur, cid),
            curated_title=curation_store.get_curated_title(cur, cid),
            curated_subtitle=curation_store.get_curated_subtitle(cur, cid),
        )

    # --- GDRIVE / DOC ---
    if cid.startswith("gdrive:") or cid.startswith("doc:"):
        # Normalize doc: -> gdrive:
        cid = canonical_content_id(source="doc", raw=cid)

        docs = (load_docs or doc_store.load_doc_candidates)() or []
        if not docs:
            raise BadRequestError("No doc candidates available. Refresh first.")

        wanted = cid[len("gdrive:"):]
        idx = None
        d = None
        for i, rec in enumerate(docs):
            if not isinstance(rec, dict):
                continue
            did = (rec.get("id") or "").strip()
            if did == wanted:
                idx = i
                d = rec
                break

        if idx is None or d is None:
            raise BadRequestError(f"Doc not found: {wanted}")

        # Build a "cleaned" dict compatible with curate_article.html
        # Minimal version: title + html + images list
        cleaned = {
            "title": (d.get("title") or "").strip() or "Curate Document",
            # Prefer summary/html-like field if you have one; adjust keys to your doc payload
            "html": (d.get("summary_html") or d.get("summary") or d.get("html") or "").strip(),
            "images": d.get("images") or [],
        }

        # Candidate for doc can just be the dict; template supports dict candidate
        candidate = {
            "url": cid,                 # canonical id (important!)
            "original_url": d.get("url") or "",
            "title": d.get("title") or "",
            "json_url": "",
            "source": "doc",
        }

        return CurateView(
            idx=idx,
            total=len(docs),
            candidate=candidate,
            candidate_id=cid,
            content_id=cid,
            cleaned=cleaned,
            final_blurb=curation_store.get_curated_blurb(cur, cid),
            excerpts=curation_store.get_curated_excerpts(cur, cid),
            selected_image=curation_store.get_curated_selected_image(cur, cid),
            crops=curation_store.get_curated_image_crops(cur, cid),
            curated_title=curation_store.get_curated_title(cur, cid),
            curated_subtitle=curation_store.get_curated_subtitle(cur, cid),
        )

    raise BadRequestError(f"Unsupported id: {cid}")
