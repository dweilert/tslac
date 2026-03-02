from __future__ import annotations

from urllib.parse import parse_qs, urlencode

from constants import DEFAULT_INTRO, DEFAULT_SUBJECT
from docsys.store import load_doc_candidates
from logutil import debug
from services.candidates_service import load_persisted_candidates, refresh_candidates, save_picks
from storage.curation_store import get_curated_blurb, load_curation
from storage.selected_store import load_selected
from templates import html_page
from web.request import Request
from web.response import Response
from web.router import Router

HOMEPAGE_URL = "https://www.tsl.texas.gov/"


def register(router: Router) -> None:
    router.get("/", get_main)
    router.get("/refresh", get_refresh)
    router.post("/save", post_save)


def _redir_status(status: str) -> Response:
    # Safe query encoding (handles &, ?, %, unicode, etc.)
    qs = urlencode({"status": status}, doseq=False)
    return Response.redirect(f"/?{qs}")


def _parse_post_form(req: Request) -> dict[str, list[str]]:
    raw = req.body.decode("utf-8", errors="replace")
    return parse_qs(raw, keep_blank_values=True)


def get_refresh(_: Request) -> Response:
    try:
        res = refresh_candidates()

        err_note = f" (errors:{res.error_count})" if res.error_count else ""
        return _redir_status(f"Refreshed candidate list (docs:{res.doc_count}){err_note}")

    except Exception as e:
        return _redir_status(f"Refresh failed: {e}")


def post_save(req: Request) -> Response:
    try:
        form = _parse_post_form(req)

        picked = form.get("picked", [])
        subject = form.get("subject", [DEFAULT_SUBJECT])[0] or DEFAULT_SUBJECT
        intro = form.get("intro", [DEFAULT_INTRO])[0] or DEFAULT_INTRO

        n = save_picks(subject=subject, intro=intro, picked_urls=picked)

        return _redir_status(f"Saved {n} item(s) to selected.yaml")

    except Exception as e:
        return _redir_status(f"Save failed: {e}")


def get_main(req: Request) -> Response:
    status = req.query_first.get("status") or ""

    # UI reads from persisted candidates
    # candidates = load_candidates_file(CANDIDATES_FILE)
    candidates = load_persisted_candidates()

    # Avoid passing non-string args to logutil.info()
    debug(f"sources: {[getattr(c, 'source', None) for c in candidates]}")

    sel = load_selected()

    prechecked: set[str] = set()
    if isinstance(sel, dict):
        for it in sel.get("items") or []:
            if isinstance(it, dict) and it.get("url"):
                prechecked.add(it["url"])

    subject = (
        sel.get("subject") if isinstance(sel, dict) and sel.get("subject") else DEFAULT_SUBJECT
    )
    intro = sel.get("intro") if isinstance(sel, dict) and sel.get("intro") else DEFAULT_INTRO

    cur = load_curation()
    has_blurb_by_url = {c.url: bool(get_curated_blurb(cur, c.url)) for c in candidates}

    doc_candidates = load_doc_candidates()
    has_blurb_by_docid = {
        d["id"]: bool(get_curated_blurb(cur, d["id"]))
        for d in (doc_candidates or [])
        if isinstance(d, dict) and d.get("id")
    }

    body = html_page(
        candidates=candidates,
        doc_candidates=doc_candidates,
        prechecked=prechecked,
        subject=subject,
        intro=intro,
        status=status,
        has_blurb_by_url=has_blurb_by_url,
        has_blurb_by_docid=has_blurb_by_docid,
    )
    return Response.html(body)
