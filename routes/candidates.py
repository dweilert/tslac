from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse

from constants import DEFAULT_INTRO, DEFAULT_SUBJECT
from docsys.store import load_doc_candidates
from logutil import debug
from services.candidates_service import load_persisted_candidates, refresh_candidates, save_picks, reset_seen_urls
from storage.curation_store import get_curated_blurb, load_curation
from storage.selected_store import load_selected
from templates import html_page

from web.request import Request
from web.response import Response
from web.router import Router

from storage.collector_store import load_seen

from urllib.parse import parse_qs
from services.candidates_service import reset_seen_urls

HOMEPAGE_URL = "https://www.tsl.texas.gov/"


def register(router: Router) -> None:
    router.get("/", get_main)
    router.get("/refresh", get_refresh)
    router.post("/save", post_save)
    router.post("/seen/reset", post_seen_reset)


def _redir_status(status: str) -> Response:
    # Safe query encoding (handles &, ?, %, unicode, etc.)
    qs = urlencode({"status": status}, doseq=False)
    return Response.redirect(f"/?{qs}")


def _parse_post_form(req: Request) -> dict[str, list[str]]:
    raw = req.body.decode("utf-8", errors="replace")
    return parse_qs(raw, keep_blank_values=True)

def post_seen_reset(req: Request, params: dict[str, Any] | None = None) -> Response:
    # Parse form body: confirm=1
    raw = req.body.decode("utf-8", errors="replace")
    form = parse_qs(raw, keep_blank_values=True)

    if form.get("confirm", [""])[0] != "1":
        return _redir_status("Reset seen URLs cancelled")

    reset_seen_urls()
    return _redir_status("Reset seen URLs (seen_urls.json cleared)")

def get_refreshOLD(req: Request) -> Response:
    try:
        # NEW: read ?ignore_seen=1
        parsed = urlparse(req.path)
        qs = parse_qs(parsed.query)
        ignore_seen = qs.get("ignore_seen", ["0"])[0] == "1"

        # NEW: pass flag through
        res = refresh_candidates(ignore_seen=ignore_seen)

        err_note = f" (errors:{res.error_count})" if res.error_count else ""
        note = " (ignored seen URLs)" if ignore_seen else ""
        return _redir_status(f"Refreshed candidate list (docs:{res.doc_count}){err_note}{note}")

    except Exception as e:
        return _redir_status(f"Refresh failed: {e}")

def get_refresh(req: Request) -> Response:
    try:
        # Parse query string for ?ignore_seen=1
        parsed = urlparse(req.path)
        qs = parse_qs(parsed.query)
        ignore_seen = qs.get("ignore_seen", ["0"])[0] == "1"

        # Pass flag into refresh logic
        res = refresh_candidates(ignore_seen=ignore_seen)

        err_note = f" (errors:{res.error_count})" if res.error_count else ""
        note = " (ignored seen URLs)" if ignore_seen else ""

        return _redir_status(
            f"Refreshed candidate list (docs:{res.doc_count}){err_note}{note}"
        )

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
