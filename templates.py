from __future__ import annotations

import html
from typing import Any
from urllib.parse import quote

from models import Candidate
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
) -> bytes:

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
        show_export_zip=False,
    )

    return html.encode("utf-8")


def curate_page_html(
    index: int,
    total: int,
    c: Candidate,
    cleaned: dict[str, Any],
    final_blurb: str,
    excerpts: list[str],
    selected_image: str,
    status: str,
    crops: dict[str, Any],
) -> bytes:
    title = cleaned.get("title") or c.title
    pub = cleaned.get("published_date") or "n/a"
    conf = cleaned.get("date_confidence") or "n/a"
    images = cleaned.get("images") or []
    clean_html = cleaned.get("clean_html") or "<p><em>No cleaned HTML returned.</em></p>"

    prev_url = f"/curate/{index-1}" if index > 0 else ""
    next_url = f"/curate/{index+1}" if (index + 1) < total else ""
    original_url = c.url

    # If you don't have /api/clean yet, set this to "" to hide the button.
    json_url = f"/api/clean?url={quote(c.url, safe='')}"

    html = render(
        "curate_article.html",
        title="Curate Article",
        page_css="/static/css/curate_article.css",
        prev_url=prev_url,
        next_url=next_url,
        original_url=original_url,
        json_url=json_url,
        index=index,
        item_num=index + 1,
        total=total,
        url=c.url,
        source=c.source,
        title_text=title,
        # title=title,
        pub=pub,
        conf=conf,
        final_blurb=final_blurb or "",
        excerpts=excerpts or [],
        images=images,
        crops=crops or {},
        selected_image=(selected_image or "").strip(),
        clean_html=clean_html,
        status=status or "",
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


def curate_doc_page_html(doc: dict, status: str = "") -> bytes:
    doc_id = doc.get("id", "")
    # title = doc.get("title", "Document")
    summary = doc.get("summary", "")
    source = doc.get("source", "doc")

    html = render(
        "curate_doc.html",
        title="Curate Document",
        page_css="/static/css/curate_doc.css",
        status=status,
        doc_id=doc_id,
        summary=summary,
        source=source,
    )
    return html.encode("utf-8")
