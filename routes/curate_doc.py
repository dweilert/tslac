from __future__ import annotations

from urllib.parse import parse_qs, urlencode

import templates
from services.curate_doc_service import load_doc_for_curate, save_doc_blurb
from web.errors import BadRequestError
from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router) -> None:
    router.get("/curate_doc", get_curate_doc)
    router.post("/curate_doc/save", post_curate_doc_save)


def _parse_post_form(req: Request) -> dict[str, str]:
    raw = req.body.decode("utf-8", errors="replace")
    form = parse_qs(raw, keep_blank_values=True)
    return {k: (v[0] if v else "") for k, v in form.items()}


def _redir_home_status(status: str) -> Response:
    qs = urlencode({"status": status}, doseq=False)
    return Response.redirect(f"/?{qs}")


def get_curate_doc(req: Request) -> Response:
    try:
        doc_id = (req.query_first.get("doc_id") or "").strip()
        status = (req.query_first.get("status") or "").strip()

        model = load_doc_for_curate(doc_id=doc_id, status=status)
        body = templates.curate_doc_page_html(doc=model.doc, status=model.status)
        return Response.html(body)

    except BadRequestError as e:
        return Response.bad_request(str(e))

    except Exception as e:
        return _redir_home_status(f"Doc curate failed: {e}")


def post_curate_doc_save(req: Request) -> Response:
    try:
        form = _parse_post_form(req)
        doc_id = (form.get("doc_id") or "").strip()
        final_blurb = (form.get("final_blurb") or "").strip()

        save_doc_blurb(doc_id=doc_id, final_blurb=final_blurb)

        qs = urlencode({"doc_id": doc_id, "status": "Saved"}, doseq=False)
        return Response.redirect(f"/curate_doc?{qs}")

    except BadRequestError as e:
        # If doc_id missing, treat as client error
        return Response.bad_request(str(e))

    except Exception as e:
        return _redir_home_status(f"Doc save failed: {e}")
