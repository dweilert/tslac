from __future__ import annotations

import html
from typing import Any
from urllib.parse import quote

from docsys.store import load_doc_candidates
from render import render


def _esc(s: object) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def html_page(
    candidates,
    doc_candidates,
    prechecked,
    subject,
    intro,
    status,
    has_blurb_by_url,
    has_blurb_by_docid,
    has_image_by_url=None,
    has_image_by_docid=None,
) -> bytes:
    has_image_by_url = has_image_by_url or {}
    has_image_by_docid = has_image_by_docid or {}

    html = render(
        "candidates.html",
        title="TSL Candidate Review",
        page_css="/static/css/candidates.css",
        candidates=candidates,
        doc_candidates=doc_candidates,
        prechecked=prechecked,
        subject=subject,
        intro=intro,
        status=status,
        has_blurb_by_url=has_blurb_by_url,
        has_blurb_by_docid=has_blurb_by_docid,
        # NEW (use real values if you have them; otherwise placeholders are fine)
        candidates_path="output/candidates_latest.json",
        selected_path="selected.yaml",
        curation_path="curation.yaml",
        selected_count=len(prechecked),
        show_export_zip=True,
        has_image_by_url=has_image_by_url,
        has_image_by_docid=has_image_by_docid,
    )

    return html.encode("utf-8")


def _get_attr(obj, name: str, default=None):
    try:
        return getattr(obj, name)
    except Exception:
        return default


def curate_page_html(
    idx: int,
    total: int,
    c,
    cleaned: dict,
    *,
    final_blurb: str = "",
    excerpts: list[str] | None = None,
    selected_image: str = "",
    status: str = "",
    crops: dict | None = None,
) -> bytes:
    excerpts = excerpts or []
    crops = crops or {}

    # Candidate fields (object or dict)
    if isinstance(c, dict):
        url = (c.get("url") or c.get("original_url") or "").strip()
        cand_title = c.get("title") or ""
        original_url = c.get("original_url") or url
        json_url = c.get("json_url") or ""
    else:
        url = (str(_get_attr(c, "url", "")) or str(_get_attr(c, "original_url", "")) or "").strip()
        cand_title = str(_get_attr(c, "title", "") or "")
        original_url = str(_get_attr(c, "original_url", "") or url)
        json_url = str(_get_attr(c, "json_url", "") or "")

    # Prev/Next
    prev_url = f"/curate/{idx-1}" if idx > 0 else ""
    next_url = f"/curate/{idx+1}" if idx < (total - 1) else ""

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
        url=url,
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


def curate_doc_page_html(*, view, status: str = "") -> bytes:
    d = view.doc or {}
    doc_id = d.get("id", "")
    title = d.get("title", "Document")
    source = d.get("source", "doc")
    summary = d.get("summary", "")

    # Use curated final blurb if present, else fall back to summary
    final_blurb = view.final_blurb or summary

    prev_url = ""
    next_url = ""

    # Basic prev/next navigation by index
    try:
        if view.idx > 0:
            prev_id = (load_doc_candidates() or [])[view.idx - 1].get("id", "")
            if prev_id:
                prev_url = f"/curate_doc?doc_id={quote(str(prev_id))}"
        if view.idx < (view.total - 1):
            next_id = (load_doc_candidates() or [])[view.idx + 1].get("id", "")
            if next_id:
                next_url = f"/curate_doc?doc_id={quote(str(next_id))}"
    except Exception:
        prev_url = ""
        next_url = ""

    html = render(
        "curate_doc.html",
        title="Curate Document",
        page_css="/static/css/curate_doc.css",
        status=status,
        # meta
        doc_id=doc_id,
        doc_title=title,
        source=source,
        idx=view.idx + 1,  # 1-based for display
        total=view.total,
        # content
        summary=summary,
        excerpts=view.excerpts or [],
        final_blurb=final_blurb,
        # nav
        prev_url=prev_url,
        next_url=next_url,
    )
    return html.encode("utf-8")
