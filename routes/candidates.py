from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs

from collect.collector import collect_candidates
from collect.rules import CollectRules
from constants import DEFAULT_INTRO, DEFAULT_SUBJECT
from doc_store import load_doc_candidates
from logutil import info
from state_store import get_curated_blurb, load_curation, load_selected, save_selected
from storage.collector_store import (
    CANDIDATES_FILE,
    SEEN_URLS_FILE,
    load_candidates_file,
    load_seen,
    save_candidates_json,
    save_seen,
)
from templates import html_page
from web.request import Request
from web.response import Response
from web.router import Router

HOMEPAGE_URL = "https://www.tsl.texas.gov/"


def register(router: Router) -> None:
    router.get("/", get_main)
    router.get("/refresh", get_refresh)
    router.post("/save", post_save)


def _parse_post_form(req: Request) -> dict[str, list[str]]:
    raw = req.body.decode("utf-8", errors="replace")
    return parse_qs(raw, keep_blank_values=True)


def get_refresh(_: Request) -> Response:
    try:
        # Load "seen" so refresh doesn't re-add already processed items (if you use this behavior)
        seen = load_seen(SEEN_URLS_FILE)

        rules = CollectRules(
            months_back=3,
            # Keep these empty unless you already have exclude lists you want to enforce here.
            # You can wire your existing exclude lists in later.
            exclude_url_substrings=(),
            exclude_title_substrings=(),
        )

        candidates, errors = collect_candidates(
            HOMEPAGE_URL,
            rules=rules,
            today=date.today(),
            seen_urls=seen,
        )

        # Persist candidates for UI
        save_candidates_json(CANDIDATES_FILE, candidates)

        # Update seen with whatever we just collected
        seen.update(c.url for c in candidates)
        save_seen(SEEN_URLS_FILE, seen)

        doc_cnt = len(load_doc_candidates())

        # Include error count if any
        err_note = f"+(errors:{len(errors)})" if errors else ""
        return Response.redirect(f"/?status=Refreshed+candidate+list+(docs:{doc_cnt}){err_note}")
    except Exception as e:
        msg = str(e).replace(" ", "+")
        return Response.redirect(f"/?status=Refresh+failed:+{msg}")


def post_save(req: Request) -> Response:
    try:
        form = _parse_post_form(req)

        picked = form.get("picked", [])
        subject = form.get("subject", [DEFAULT_SUBJECT])[0] or DEFAULT_SUBJECT
        intro = form.get("intro", [DEFAULT_INTRO])[0] or DEFAULT_INTRO

        save_selected(subject, intro, picked)

        return Response.redirect(f"/?status=Saved+{len(picked)}+item(s)+to+selected.yaml")
    except Exception as e:
        msg = str(e).replace(" ", "+")
        return Response.redirect(f"/?status=Save+failed:+{msg}")


def get_main(req: Request) -> Response:
    status = req.query_first.get("status") or ""

    # UI reads from persisted candidates
    candidates = load_candidates_file(CANDIDATES_FILE)
    info("DEBUG sources:", {getattr(c, "source", None) for c in candidates})

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
