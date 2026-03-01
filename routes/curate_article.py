from __future__ import annotations

from urllib.parse import parse_qs, urlencode

from services.curate_article_service import (
    add_excerpt,
    build_view_by_index,
    clear_excerpts,
    clear_selected_image,
    pop_excerpt,
    save_blurb,
    save_crop,
    select_image,
)
from templates import curate_page_html
from web.errors import BadRequestError
from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router) -> None:
    router.route_regex("GET", r"^/curate/(?P<idx>[0-9]+)/?$", get_curate_by_index)

    router.post("/curate/save", post_curate_save)
    router.post("/curate/add_excerpt", post_curate_add_excerpt)
    router.post("/curate/pop_excerpt", post_curate_pop_excerpt)
    router.post("/curate/save_crop", post_curate_save_crop)
    router.post("/curate/select_image", post_curate_select_image)
    router.post("/curate/clear_selected_image", post_curate_clear_selected_image)
    router.post("/curate/clear_excerpts", post_curate_clear_excerpts)


def _parse_post_form(req: Request) -> dict[str, str]:
    raw = req.body.decode("utf-8", errors="replace")
    form = parse_qs(raw, keep_blank_values=True)
    return {k: (v[0] if v else "") for k, v in form.items()}


def _safe_int(s: str, default: int = 0) -> int:
    try:
        return int((s or "").strip())
    except Exception:
        return default


def _redirect_curate(idx: int, status: str) -> Response:
    qs = urlencode({"status": status}, doseq=False)
    return Response.redirect(f"/curate/{idx}?{qs}")


def get_curate_by_index(req: Request, params: dict[str, str]) -> Response:
    idx_raw = params.get("idx", "")

    try:
        idx = int(idx_raw)
    except ValueError as err:
        raise BadRequestError(f"Invalid curate index: {idx_raw!r}") from err

    status = req.query_first.get("status", "")

    view = build_view_by_index(idx)

    body = curate_page_html(
        view.idx,
        view.total,
        view.candidate,
        view.cleaned,
        final_blurb=view.final_blurb,
        excerpts=view.excerpts,
        selected_image=view.selected_image,
        status=status,
        crops=view.crops,
    )
    return Response.html(body)


def post_curate_save(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    save_blurb(url=form.get("url", ""), final_blurb=form.get("final_blurb", ""))
    return _redirect_curate(idx, "Saved blurb")


def post_curate_add_excerpt(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    add_excerpt(url=form.get("url", ""), excerpt=form.get("excerpt", ""))
    return _redirect_curate(idx, "Added excerpt")


def post_curate_pop_excerpt(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    pop_excerpt(url=form.get("url", ""))
    return _redirect_curate(idx, "Removed last excerpt")


def post_curate_save_crop(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    save_crop(
        url=form.get("url", ""), img_src=form.get("img_src", ""), crop_json=form.get("crop", "")
    )
    return _redirect_curate(idx, "Saved image crop")


def post_curate_select_image(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    select_image(url=form.get("url", ""), img_src=form.get("img_src", ""))
    return _redirect_curate(idx, "Selected image")


def post_curate_clear_selected_image(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    clear_selected_image(url=form.get("url", ""))
    return _redirect_curate(idx, "Cleared selected image")


def post_curate_clear_excerpts(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    clear_excerpts(url=form.get("url", ""))
    return _redirect_curate(idx, "Cleared excerpts")
