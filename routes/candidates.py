from __future__ import annotations

from urllib.parse import parse_qs

from web.request import Request
from web.response import Response
from web.router import Router

# These imports are based on the code you pasted.
# If any import name differs in your repo, tell me the ImportError and I’ll adjust in one pass.
from collector import collect_candidates
from collector import load_candidates_file  # or wherever load_candidates_file lives
from doc_store import load_doc_candidates
from state_store import load_selected, load_curation, get_curated_blurb, save_selected

from templates import html_page
from constants import DEFAULT_SUBJECT, DEFAULT_INTRO

def register(router: Router) -> None:
    router.get("/", get_main)
    router.get("/refresh", get_refresh)
    router.post("/save", post_save)


def _parse_post_form(req: Request) -> dict[str, list[str]]:
    raw = req.body.decode("utf-8", errors="replace")
    return parse_qs(raw, keep_blank_values=True)


def get_refresh(_: Request) -> Response:
    try:
        collect_candidates()
        doc_cnt = len(load_doc_candidates())
        return Response.redirect(f"/?status=Refreshed+candidate+list+(docs:{doc_cnt})")
    except Exception as e:
        msg = str(e).replace(" ", "+")
        return Response.redirect(f"/?status=Refresh+failed:+{msg}")


def post_save(req: Request) -> Response:
    try:
        form = _parse_post_form(req)

        picked = form.get("picked", [])
        subject = (form.get("subject", [DEFAULT_SUBJECT])[0] or DEFAULT_SUBJECT)
        intro = (form.get("intro", [DEFAULT_INTRO])[0] or DEFAULT_INTRO)

        save_selected(subject, intro, picked)

        return Response.redirect(f"/?status=Saved+{len(picked)}+item(s)+to+selected.yaml")
    except Exception as e:
        msg = str(e).replace(" ", "+")
        return Response.redirect(f"/?status=Save+failed:+{msg}")


def get_main(req: Request) -> Response:
    # status comes from querystring (Request already parsed it)
    status = (req.query_first.get("status") or "")

    candidates = load_candidates_file()
    sel = load_selected()

    prechecked: set[str] = set()
    if isinstance(sel, dict):
        for it in sel.get("items") or []:
            if isinstance(it, dict) and it.get("url"):
                prechecked.add(it["url"])

    subject = sel.get("subject") if isinstance(sel, dict) and sel.get("subject") else DEFAULT_SUBJECT
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