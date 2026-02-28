from __future__ import annotations

from urllib.parse import parse_qs, quote

import templates
from doc_store import load_doc_candidates
from state_store import get_curated_blurb, load_curation, upsert_curated_blurb
from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router) -> None:
    router.get("/curate_doc", get_curate_doc)
    router.post("/curate_doc/save", post_curate_doc_save)


def _parse_post_form(req: Request) -> dict[str, str]:
    # Your server.py uses application/x-www-form-urlencoded + parse_qs
    raw = req.body.decode("utf-8", errors="replace")
    form = parse_qs(raw, keep_blank_values=True)
    return {k: (v[0] if v else "") for k, v in form.items()}


def get_curate_doc(req: Request) -> Response:
    try:
        doc_id = (req.query_first.get("doc_id") or "").strip()
        status = (req.query_first.get("status") or "").strip()
        if not doc_id:
            return Response.bad_request("Missing doc_id")

        doc_candidates = load_doc_candidates()
        d = next(
            (
                x
                for x in doc_candidates
                if isinstance(x, dict) and (x.get("id") or "").strip() == doc_id
            ),
            None,
        )
        if not d:
            return Response.bad_request(f"Doc not found: {doc_id}")

        # Load saved curation; doc_id is used as the key (same as server.py)
        cur = load_curation()
        final_blurb = get_curated_blurb(cur, doc_id)

        doc_d = dict(d)
        if final_blurb:
            # show saved edit instead
            doc_d["summary"] = final_blurb

        body = templates.curate_doc_page_html(doc=doc_d, status=status)
        return Response.html(body)

    except Exception as e:
        # match server.py behavior: bounce back to list page with status
        msg = str(e).replace(" ", "+")
        return Response.redirect(f"/?status=Doc+curate+failed:+{msg}")


def post_curate_doc_save(req: Request) -> Response:
    try:
        form = _parse_post_form(req)
        doc_id = (form.get("doc_id") or "").strip()
        final_blurb = (form.get("final_blurb") or "").strip()

        if not doc_id:
            raise ValueError("Missing doc_id (hidden field not posted)")

        upsert_curated_blurb(doc_id, final_blurb)

        return Response.redirect(f"/curate_doc?doc_id={quote(doc_id)}&status=Saved")

    except Exception as e:
        msg = str(e).replace(" ", "+")
        return Response.redirect(f"/?status=Doc+save+failed:+{msg}")
