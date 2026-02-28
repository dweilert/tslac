from __future__ import annotations

import json
from urllib.parse import parse_qs

import cleaner
from state_store import (
    add_curated_excerpt,
    clear_curated_excerpts,
    clear_curated_selected_image,
    get_curated_blurb,
    get_curated_excerpts,
    get_curated_image_crops,
    get_curated_selected_image,
    load_curation,
    pop_curated_excerpt,
    upsert_curated_blurb,
    upsert_curated_image_crop,
    upsert_curated_selected_image,
)

# from collect.collector import load_candidates_file
from storage.collector_store import load_candidates_file
from templates import curate_page_html
from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router) -> None:
    # GET /curate/<idx>
    router.route_regex("GET", r"^/curate/\d+$", get_curate_by_index)

    # POST actions (exact match, same as server.py)
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
    # status should already be + friendly (we’ll just replace spaces)
    status_q = status.replace(" ", "+")
    return Response.redirect(f"/curate/{idx}?status={status_q}")


def get_curate_by_index(req: Request) -> Response:
    try:
        path_only = req.path.split("?", 1)[0]
        idx_str = path_only[len("/curate/") :].strip("/")
        idx = int(idx_str)

        candidates = load_candidates_file()
        if not candidates:
            raise ValueError("No candidates available. Go back and click Refresh candidates first.")

        if idx < 0 or idx >= len(candidates):
            raise ValueError(f"Index out of range: {idx} (0..{len(candidates)-1})")

        status = req.query_first.get("status", "")

        c = candidates[idx]
        res = cleaner.clean_article(c.url)

        cleaned = {
            "title": res.title,
            "published_date": res.published_date,
            "date_confidence": res.date_confidence,
            "clean_html": res.clean_html,
            "text_plain": res.text_plain,
            "images": res.images,
            "extraction_quality": res.extraction_quality,
        }

        cur = load_curation()
        blurb = get_curated_blurb(cur, c.url)
        excerpts = get_curated_excerpts(cur, c.url)
        selected_image = get_curated_selected_image(cur, c.url)

        try:
            crops = get_curated_image_crops(cur, c.url)
        except Exception:
            crops = {}

        body = curate_page_html(
            idx,
            len(candidates),
            c,
            cleaned,
            final_blurb=blurb,
            excerpts=excerpts,
            selected_image=selected_image,
            status=status,
            crops=crops,
        )
        return Response.html(body)

    except Exception:
        import traceback

        tb = traceback.format_exc()
        return Response.html(f"<pre>\nCurate error:\n{tb}\n</pre>", status=400)


def post_curate_save(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    url = (form.get("url") or "").strip()
    final_blurb = (form.get("final_blurb") or "").strip()
    if url:
        upsert_curated_blurb(url, final_blurb)
    return _redirect_curate(idx, "Saved blurb")


def post_curate_add_excerpt(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    url = (form.get("url") or "").strip()
    excerpt = (form.get("excerpt") or "").strip()
    if url and excerpt:
        add_curated_excerpt(url, excerpt)
    return _redirect_curate(idx, "Added excerpt")


def post_curate_pop_excerpt(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    url = (form.get("url") or "").strip()
    if url:
        pop_curated_excerpt(url)
    return _redirect_curate(idx, "Removed last excerpt")


def post_curate_save_crop(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    url = (form.get("url") or "").strip()
    img_src = (form.get("img_src") or "").strip()
    crop_json = (form.get("crop") or "").strip()

    try:
        crop = json.loads(crop_json) if crop_json else {}
    except Exception:
        crop = {}

    if url and img_src and crop:
        upsert_curated_image_crop(url, img_src, crop)

    return _redirect_curate(idx, "Saved image crop")


def post_curate_select_image(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    url = (form.get("url") or "").strip()
    img_src = (form.get("img_src") or "").strip()

    # match server.py safety: only allow http(s)
    if img_src and not (img_src.startswith("http://") or img_src.startswith("https://")):
        img_src = ""

    if url and img_src:
        upsert_curated_selected_image(url, img_src)

    return _redirect_curate(idx, "Selected image")


def post_curate_clear_selected_image(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    url = (form.get("url") or "").strip()
    if url:
        clear_curated_selected_image(url)
    return _redirect_curate(idx, "Cleared selected image")


def post_curate_clear_excerpts(req: Request) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    url = (form.get("url") or "").strip()
    if url:
        clear_curated_excerpts(url)
    return _redirect_curate(idx, "Cleared excerpts")
