from __future__ import annotations

from urllib.parse import parse_qs, urlencode

from services.curate_doc_service import (
    build_view_by_doc_id,
)
from templates import curate_doc_page_html
from web.errors import BadRequestError
from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router) -> None:
    router.get("/curate_doc", get_curate_doc)

    router.post("/curate_doc/save", post_curate_doc_save)
    router.post("/curate_doc/add_excerpt", post_curate_doc_add_excerpt)
    router.post("/curate_doc/pop_excerpt", post_curate_doc_pop_excerpt)
    router.post("/curate_doc/clear_excerpts", post_curate_doc_clear_excerpts)
    router.post("/curate_doc/compose_blurb", post_curate_doc_compose_blurb)


def _parse_post_form(req: Request) -> dict[str, str]:
    raw = req.body.decode("utf-8", errors="replace")
    form = parse_qs(raw, keep_blank_values=True)
    return {k: (v[0] if v else "") for k, v in form.items()}


def _redir_home_status(status: str) -> Response:
    qs = urlencode({"status": status}, doseq=False)
    return Response.redirect(f"/?{qs}")


def _redir_doc(doc_id: str, status: str) -> Response:
    qs = urlencode({"doc_id": doc_id, "status": status}, doseq=False)
    return Response.redirect(f"/curate_doc?{qs}")


def get_curate_doc(req: Request) -> Response:
    try:
        doc_id = (req.query_first.get("doc_id") or "").strip()
        status = (req.query_first.get("status") or "").strip()

        view = build_view_by_doc_id(doc_id)

        body = curate_doc_page_html(
            view=view,
            status=status,
        )
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

        save_blurb(doc_id=doc_id, final_blurb=final_blurb)
        return _redir_doc(doc_id, "Saved")

    except BadRequestError as e:
        return Response.bad_request(str(e))

    except Exception as e:
        return _redir_home_status(f"Doc save failed: {e}")


def post_curate_doc_add_excerpt(req: Request) -> Response:
    try:
        form = _parse_post_form(req)
        doc_id = (form.get("doc_id") or "").strip()
        excerpt = (form.get("excerpt") or "").strip()

        add_excerpt(doc_id=doc_id, excerpt=excerpt)
        return _redir_doc(doc_id, "Added excerpt")

    except BadRequestError as e:
        return Response.bad_request(str(e))

    except Exception as e:
        return _redir_home_status(f"Doc add excerpt failed: {e}")


def post_curate_doc_pop_excerpt(req: Request) -> Response:
    try:
        form = _parse_post_form(req)
        doc_id = (form.get("doc_id") or "").strip()

        pop_excerpt(doc_id=doc_id)
        return _redir_doc(doc_id, "Removed last excerpt")

    except BadRequestError as e:
        return Response.bad_request(str(e))

    except Exception as e:
        return _redir_home_status(f"Doc pop excerpt failed: {e}")


def post_curate_doc_clear_excerpts(req: Request) -> Response:
    try:
        form = _parse_post_form(req)
        doc_id = (form.get("doc_id") or "").strip()

        clear_excerpts(doc_id=doc_id)
        return _redir_doc(doc_id, "Cleared excerpts")

    except BadRequestError as e:
        return Response.bad_request(str(e))

    except Exception as e:
        return _redir_home_status(f"Doc clear excerpts failed: {e}")


def post_curate_doc_compose_blurb(req: Request) -> Response:
    try:
        form = _parse_post_form(req)
        doc_id = (form.get("doc_id") or "").strip()

        composed = compose_blurb_from_excerpts(doc_id=doc_id)
        if composed:
            return _redir_doc(doc_id, "Composed final blurb from excerpts")
        return _redir_doc(doc_id, "No excerpts to compose")

    except BadRequestError as e:
        return Response.bad_request(str(e))

    except Exception as e:
        return _redir_home_status(f"Doc compose blurb failed: {e}")
