# routes/curate_article.py
from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlencode

from services.curate_article_service import (
    add_excerpt,
    build_view_by_content_id,
    clear_excerpts,
    clear_selected_image,
    compose_blurb_from_excerpts,
    delete_excerpt,
    move_excerpt,
    pop_excerpt,
    save_blurb,
    save_crop,
    save_subtitle,
    save_title,
    select_image,
)
from templates import curate_page_html
from web.errors import BadRequestError
from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router) -> None:
    # Unified curate route only:
    #   /curate?id=<content_id>
    router.get("/curate", get_curate_by_id)

    # Curate actions (POST)
    router.post("/curate/save", post_curate_save)
    router.post("/curate/add_excerpt", post_curate_add_excerpt)
    router.post("/curate/pop_excerpt", post_curate_pop_excerpt)
    router.post("/curate/delete_excerpt", post_curate_delete_excerpt)
    router.post("/curate/move_excerpt", post_curate_move_excerpt)
    router.post("/curate/clear_excerpts", post_curate_clear_excerpts)
    router.post("/curate/compose_blurb", post_curate_compose_blurb)

    # Images
    router.post("/curate/save_crop", post_curate_save_crop)
    router.post("/curate/select_image", post_curate_select_image)
    router.post("/curate/clear_selected_image", post_curate_clear_selected_image)


# ----------------------------
# Helpers
# ----------------------------
def _safe_int(s: str, default: int = 0) -> int:
    try:
        return int((s or "").strip())
    except Exception:
        return default


def _parse_post_form(req: Request) -> dict[str, str]:
    raw = req.body.decode("utf-8", errors="replace")
    form = parse_qs(raw, keep_blank_values=True)
    return {k: (v[0] if v else "") for k, v in form.items()}


def _form_content_id(form: dict[str, str]) -> str:
    """
    Canonical key used for curation writes.

    Priority:
      1) content_id (new unified flow)
      2) url (back-compat: some templates may still post url as canonical id)
      3) doc_id (older flows; keep only as a last-ditch fallback)
    """
    return (form.get("content_id") or form.get("url") or form.get("doc_id") or "").strip()


def _redirect_curate_by_id(content_id: str, status: str) -> Response:
    if not content_id:
        return Response.redirect("/?" + urlencode({"status": status or "Missing content_id"}, doseq=False))
    qs = urlencode({"id": content_id, "status": status}, doseq=False)
    return Response.redirect("/curate?" + qs)


# ----------------------------
# GET handler
# ----------------------------
def get_curate_by_id(req: Request, params: dict[str, Any] | None = None) -> Response:
    cid = (req.query_first.get("id", "") or "").strip()
    if not cid:
        return Response.redirect("/?" + urlencode({"status": "Missing id for /curate"}, doseq=False))

    try:
        view = build_view_by_content_id(cid)
    except BadRequestError as e:
        return Response.redirect("/?" + urlencode({"status": f"Curate failed: {e}"}, doseq=False))

    status = req.query_first.get("status", "") or ""

    body = curate_page_html(
        view.idx,
        view.total,
        view.candidate,
        view.cleaned,
        candidate_id=view.candidate_id,
        prev_id="",  # optional: wire later via stable ordering
        next_id="",  # optional: wire later via stable ordering
        final_blurb=view.final_blurb,
        excerpts=view.excerpts,
        selected_image=view.selected_image,
        status=status,
        crops=view.crops,
        curated_title=view.curated_title,
        curated_subtitle=view.curated_subtitle,
    )
    return Response.html(body)


# ----------------------------
# POST handlers
# ----------------------------
def post_curate_save(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    cid = _form_content_id(form)

    save_blurb(url=cid, final_blurb=form.get("final_blurb", ""))
    save_title(url=cid, title=form.get("curated_title", ""))
    save_subtitle(url=cid, subtitle=form.get("curated_subtitle", ""))

    return _redirect_curate_by_id(cid, "Saved blurb")


def post_curate_add_excerpt(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    cid = _form_content_id(form)

    add_excerpt(url=cid, excerpt=form.get("excerpt", ""))
    return _redirect_curate_by_id(cid, "Added excerpt")


def post_curate_pop_excerpt(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    cid = _form_content_id(form)

    pop_excerpt(url=cid)
    return _redirect_curate_by_id(cid, "Removed last excerpt")


def post_curate_delete_excerpt(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    cid = _form_content_id(form)
    ex_idx = _safe_int(form.get("excerpt_index", "0"), 0)

    delete_excerpt(url=cid, excerpt_index=ex_idx)
    return _redirect_curate_by_id(cid, f"Deleted excerpt #{ex_idx + 1}")


def post_curate_move_excerpt(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    cid = _form_content_id(form)
    ex_idx = _safe_int(form.get("excerpt_index", "0"), 0)
    direction = (form.get("direction", "") or "").strip().lower()

    if direction not in ("up", "down"):
        return _redirect_curate_by_id(cid, "Invalid move direction")

    move_excerpt(url=cid, excerpt_index=ex_idx, direction=direction)
    return _redirect_curate_by_id(cid, f"Moved excerpt #{ex_idx + 1} {direction}")


def post_curate_clear_excerpts(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    cid = _form_content_id(form)

    clear_excerpts(url=cid)
    return _redirect_curate_by_id(cid, "Cleared excerpts")


def post_curate_compose_blurb(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    cid = _form_content_id(form)

    composed = compose_blurb_from_excerpts(url=cid)
    if composed:
        return _redirect_curate_by_id(cid, "Composed final blurb from excerpts")
    return _redirect_curate_by_id(cid, "No excerpts to compose")


def post_curate_save_crop(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    cid = _form_content_id(form)

    save_crop(url=cid, img_src=form.get("img_src", ""), crop_json=form.get("crop", ""))
    return _redirect_curate_by_id(cid, "Saved image crop")


def post_curate_select_image(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    cid = _form_content_id(form)

    select_image(content_id=cid, img_src=form.get("img_src", ""))
    return _redirect_curate_by_id(cid, "Selected image")


def post_curate_clear_selected_image(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    cid = _form_content_id(form)

    clear_selected_image(url=cid)
    return _redirect_curate_by_id(cid, "Cleared selected image")
