# templates.py
from __future__ import annotations
import os
import html
from typing import Any
from urllib.parse import quote

from core.render import render

def _esc(s: object) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def html_page(
    candidates,
    prechecked,
    subject,
    intro,
    status,
    has_blurb_by_url,
    has_image_by_url=None,
) -> bytes:
    has_image_by_url = has_image_by_url or {}

    html = render(
        "candidates.html",
        title="TSL Candidate Review",
        page_css="/static/css/candidates.css",
        candidates=candidates,
        prechecked=prechecked,
        subject=subject,
        intro=intro,
        status=status,
        has_blurb_by_url=has_blurb_by_url,
        candidates_path="output/candidates_latest.json",
        selected_path="selected.yaml",
        curation_path="curation.yaml",
        selected_count=len(prechecked),
        show_export_zip=True,
        has_image_by_url=has_image_by_url,
    )
    return html.encode("utf-8")


def _get_attr(obj, name: str, default=None):
    try:
        return getattr(obj, name)
    except Exception:
        return default


def curate_page_html(
    index,
    total,
    candidate,
    cleaned,
    *,
    candidate_id: str = "",
    prev_id: str = "",
    next_id: str = "",
    final_blurb="",
    excerpts=None,
    selected_image="",
    status="",
    crops=None,
    curated_title="",
    curated_subtitle="",
    tinymce_api_key: str = "",
) -> bytes:

    c = candidate
    idx = index
    excerpts = excerpts or []
    crops = crops or {}

    # Candidate fields (object or dict)
    if isinstance(c, dict):
        raw_url = (c.get("url") or c.get("original_url") or "").strip()
        cand_title = (c.get("title") or "").strip()
        original_url = (c.get("original_url") or raw_url).strip()
        json_url = (c.get("json_url") or "").strip()
    else:
        raw_url = (
            str(_get_attr(c, "url", "")) or str(_get_attr(c, "original_url", "")) or ""
        ).strip()
        cand_title = str(_get_attr(c, "title", "") or "").strip()
        original_url = (str(_get_attr(c, "original_url", "") or raw_url)).strip()
        json_url = str(_get_attr(c, "json_url", "") or "").strip()

    # Canonical key + real page url
    page_url = raw_url
    if raw_url.startswith("web:"):
        page_url = raw_url[len("web:") :].strip()

    content_id = f"web:{page_url}" if page_url else raw_url

    # Prev/Next now use stable ids (not list positions)
    prev_url = f"/curate?id={quote(prev_id)}" if prev_id else ""
    next_url = f"/curate?id={quote(next_id)}" if next_id else ""

    # Cleaned title/body/images (robust keys)
    title = (
        (cleaned.get("title") if isinstance(cleaned, dict) else "")
        or cand_title
        or "Curate Article"
    )

    cleaned_html = ""
    if isinstance(cleaned, dict):
        cleaned_html = (
            cleaned.get("html") or cleaned.get("cleaned_html") or cleaned.get("content_html") or ""
        )

    # Images: prefer cleaned["images"], else candidate.images
    images = []
    if isinstance(cleaned, dict):
        v = cleaned.get("images") or cleaned.get("image_candidates") or []
        if isinstance(v, list):
            images = v

    if not images:
        if isinstance(c, dict):
            v = c.get("images") or c.get("image_candidates") or []
            if isinstance(v, list):
                images = v
        else:
            v = _get_attr(c, "images", None) or _get_attr(c, "image_candidates", None) or []
            if isinstance(v, list):
                images = v

    html = render(
        "curate_article.html",
        title=title,
        status=status,
        page_css="/static/css/curate_article.css",
        index=idx,
        total=total,
        url=page_url,  # real URL
        content_id=content_id,  # canonical id
        original_url=original_url,
        json_url=json_url,
        prev_url=prev_url,
        next_url=next_url,
        final_blurb=final_blurb or "",
        excerpts=excerpts,
        images=images,
        selected_image=selected_image or "",
        crops=crops,
        cleaned_html=cleaned_html,
        curated_title=curated_title,
        curated_subtitle=curated_subtitle,
        tinymce_api_key=tinymce_api_key or "",
    )
    return html.encode("utf-8")


def watch_page_html(
    sites_text: str,
    topics_text: str,
    status: str,
    latest: dict[str, Any],
) -> bytes:
    results = latest.get("results") if isinstance(latest, dict) else None
    errors = latest.get("errors") if isinstance(latest, dict) else None
    latest_error = (latest.get("_error") or "") if isinstance(latest, dict) else ""

    html = render(
        "watch.html",
        title="Watch Sites",
        page_css="/static/css/watch.css",  # ✅ page-specific CSS
        status=status,
        sites_text=sites_text,
        topics_text=topics_text,
        results=results,
        errors=errors,
        latest_error=str(latest_error) if latest_error else "",
    )
    return html.encode("utf-8")
