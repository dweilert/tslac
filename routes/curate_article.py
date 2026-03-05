# routes/curate_article.py
# routes/curate_article.py
from __future__ import annotations

import html as _html
from typing import Any
from urllib.parse import parse_qs, urlencode

from services.candidates_service import (
    get_candidate_id,
    load_persisted_candidates,
)
from services.curate_article_service import (
    add_excerpt,
    build_view_by_content_id,
    build_view_by_index,
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

    # Existing index-based route (keep)
    router.route_regex("GET", r"^/curate/(?P<idx>[0-9]+)/?$", get_curate_by_index)

    # Unified id-based route
    router.get("/curate", get_curate_by_id)

    # Curate actions
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


def _form_key(form: dict[str, str]) -> str:
    """
    Canonical key used for curation writes.

    Priority:
      1) content_id (new)
      2) doc_id (some older flows)
      3) url (back-compat; should already be canonical in your template)
    """
    return (form.get("content_id") or form.get("doc_id") or form.get("url") or "").strip()


def _redirect_curate(idx: int, status: str) -> Response:
    qs = urlencode({"status": status}, doseq=False)
    return Response.redirect(f"/curate/{idx}?{qs}#detected-images")


def _redirect_curate_no_anchor(idx: int, status: str) -> Response:
    qs = urlencode({"status": status}, doseq=False)
    return Response.redirect(f"/curate/{idx}?{qs}")


# ----------------------------
# GET handlers
# ----------------------------

def get_curate_by_id(req: Request, params: dict[str, Any] | None = None) -> Response:
    cid = (req.query_first.get("id", "") or "").strip()
    if not cid:
        return Response.redirect("/?" + urlencode({"status": "Missing id for /curate"}, doseq=False))

    try:
        view = build_view_by_content_id(cid)
    except BadRequestError as e:
        return Response.redirect("/?" + urlencode({"status": f"Curate failed: {e}"}, doseq=False))

    status = req.query_first.get("status", "")

    body = curate_page_html(
        view.idx,
        view.total,
        view.candidate,
        view.cleaned,
        candidate_id=view.candidate_id,
        prev_id="",            # you can wire these later
        next_id="",            # you can wire these later
        final_blurb=view.final_blurb,
        excerpts=view.excerpts,
        selected_image=view.selected_image,
        status=status,
        crops=view.crops,
        curated_title=view.curated_title,
        curated_subtitle=view.curated_subtitle,
    )
    return Response.html(body)


def get_curate_by_index(req: Request, params: dict[str, Any] | None = None) -> Response:
    params = params or {}
    idx_raw = (params.get("idx") or "").strip()

    try:
        idx = int(idx_raw)
    except ValueError as err:
        raise BadRequestError(f"Invalid curate index: {idx_raw!r}") from err

    status = req.query_first.get("status", "") or ""

    view = build_view_by_index(idx)

    candidates = load_persisted_candidates()

    prev_id = ""
    next_id = ""
    if idx > 0:
        prev_id = get_candidate_id(candidates[idx - 1])
    if idx < (len(candidates) - 1):
        next_id = get_candidate_id(candidates[idx + 1])

    body = curate_page_html(
        view.idx,
        view.total,
        view.candidate,
        view.cleaned,
        candidate_id=view.candidate_id if hasattr(view, "candidate_id") else "",
        prev_id=prev_id,
        next_id=next_id,
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
    idx = _safe_int(form.get("index", "0"), 0)
    key = _form_key(form)

    save_blurb(url=key, final_blurb=form.get("final_blurb", ""))
    save_title(url=key, title=form.get("curated_title", ""))
    save_subtitle(url=key, subtitle=form.get("curated_subtitle", ""))

    return _redirect_curate(idx, "Saved blurb")


def post_curate_add_excerpt(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    key = _form_key(form)

    add_excerpt(url=key, excerpt=form.get("excerpt", ""))
    return _redirect_curate(idx, "Added excerpt")


def post_curate_pop_excerpt(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    key = _form_key(form)

    pop_excerpt(url=key)
    return _redirect_curate(idx, "Removed last excerpt")


def post_curate_delete_excerpt(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    key = _form_key(form)
    ex_idx = _safe_int(form.get("excerpt_index", "0"), 0)

    delete_excerpt(url=key, excerpt_index=ex_idx)
    return _redirect_curate(idx, f"Deleted excerpt #{ex_idx + 1}")


def post_curate_move_excerpt(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    key = _form_key(form)
    ex_idx = _safe_int(form.get("excerpt_index", "0"), 0)
    direction = (form.get("direction", "") or "").strip().lower()

    if direction not in ("up", "down"):
        return _redirect_curate(idx, "Invalid move direction")

    move_excerpt(url=key, excerpt_index=ex_idx, direction=direction)
    return _redirect_curate(idx, f"Moved excerpt #{ex_idx + 1} {direction}")


def post_curate_clear_excerpts(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    key = _form_key(form)

    clear_excerpts(url=key)
    return _redirect_curate(idx, "Cleared excerpts")


def post_curate_compose_blurb(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    key = _form_key(form)

    composed = compose_blurb_from_excerpts(url=key)
    if composed:
        return _redirect_curate(idx, "Composed final blurb from excerpts")
    return _redirect_curate(idx, "No excerpts to compose")


def post_curate_save_crop(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    key = _form_key(form)

    save_crop(url=key, img_src=form.get("img_src", ""), crop_json=form.get("crop", ""))
    return _redirect_curate(idx, "Saved image crop")


def post_curate_select_image(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    key = _form_key(form)

    select_image(content_id=key, img_src=form.get("img_src", ""))
    return _redirect_curate(idx, "Selected image")


def post_curate_clear_selected_image(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    idx = _safe_int(form.get("index", "0"), 0)
    key = _form_key(form)

    clear_selected_image(url=key)
    return _redirect_curate(idx, "Cleared selected image")






# If you have canonical_content_id already, use it; otherwise keep this tiny normalizer.
def _strip(s: object) -> str:
    return "" if s is None else str(s).strip()

def _as_web_id(raw: str) -> str:
    r = _strip(raw)
    if not r:
        return ""
    if r.startswith("web:"):
        # remove fragment if you want; optional
        return "web:" + r[len("web:") :].split("#", 1)[0].strip()
    return "web:" + r.split("#", 1)[0].strip()

def _as_gdrive_id(raw: str) -> str:
    r = _strip(raw)
    if not r:
        return ""
    if r.startswith("gdrive:"):
        return "gdrive:" + r[len("gdrive:") :].strip()
    if r.startswith("doc:"):
        return "gdrive:" + r[len("doc:") :].strip()
    # allow passing plain doc id
    return "gdrive:" + r

def _doc_summary_to_html(summary: str) -> str:
    s = _strip(summary)
    if not s:
        return ""
    # super-safe, simple paragraphs
    parts = [p.strip() for p in s.split("\n\n") if p.strip()]
    return "".join(f"<p>{_html.escape(p)}</p>" for p in parts)

def get_curate_by_id(req: Request, params: dict[str, Any] | None = None) -> Response:
    """
    Unified entrypoint: /curate?id=<canonical_content_id>
      - web:...  -> existing web curate
      - gdrive:... (or doc:... or raw docid) -> render SAME curate page
    """
    raw_id = _strip(req.query_first.get("id", ""))
    if not raw_id:
        return Response.redirect("/?" + urlencode({"status": "Missing id for /curate"}, doseq=False))

    # --- DOC path ---
    if raw_id.startswith(("gdrive:", "doc:")) or (":" not in raw_id and len(raw_id) >= 10):
        cid = _as_gdrive_id(raw_id)
        doc_id = cid[len("gdrive:") :]

        status = _strip(req.query_first.get("status", ""))
        view = build_view_by_doc_id(doc_id)

        d = view.doc or {}
        doc_title = _strip(d.get("title")) or cid
        open_url = _strip(d.get("url")) or ""
        summary = _strip(d.get("summary")) or ""

        cleaned = {
            "title": doc_title,
            # until you implement real doc->html extraction, show summary as HTML:
            "html": _doc_summary_to_html(summary),
            "images": [],
        }

        # Candidate dict shaped enough for curate_page_html
        candidate = {
            "url": cid,                  # IMPORTANT: canonical id
            "title": doc_title,
            "original_url": open_url,
            "json_url": "",
            "source": "doc",
        }

        body = curate_page_html(
            index=view.idx,
            total=view.total,
            candidate=candidate,
            cleaned=cleaned,
            final_blurb=view.final_blurb,
            excerpts=view.excerpts,
            selected_image=view.selected_image,
            status=status,
            crops=view.crops,
            curated_title="",            # optional: if you add title/subtitle for docs later
            curated_subtitle="",
            candidate_id=cid,
            prev_id="",                  # optional: wire later using unified list
            next_id="",
        )
        return Response.html(body)

    # --- WEB path ---
    cid = _as_web_id(raw_id)

    # Find idx by matching canonical web id against persisted candidates
    candidates = load_persisted_candidates()
    idx = None
    for i, c in enumerate(candidates):
        cand_url = _strip(getattr(c, "url", "") or getattr(c, "original_url", ""))
        if _as_web_id(cand_url) == cid:
            idx = i
            break

    if idx is None:
        return Response.redirect(
            "/?" + urlencode({"status": f"Curate failed: web candidate not found for id={cid}"}, doseq=False)
        )

    # keep your existing behavior using build_view_by_index + /curate/<idx> if you want
    # But simplest: just render directly here using build_view_by_index
    status = _strip(req.query_first.get("status", ""))
    view = build_view_by_index(int(idx))

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
        curated_title=view.curated_title,
        curated_subtitle=view.curated_subtitle,
        candidate_id=cid,
        prev_id="",
        next_id="",
    )
    return Response.html(body)
