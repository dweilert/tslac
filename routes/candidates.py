# routes/candidates.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import storage.curation_store as curation_store
from constants import DEFAULT_INTRO, DEFAULT_SUBJECT
from docsys.store import load_doc_candidates
from logutil import debug
from services import watch_service
from services.candidates_service import (
    load_persisted_candidates,
    refresh_candidates,
    reset_seen_urls,
    save_picks,
)
from storage.curation_store import load_curation
from storage.selected_store import load_selected
from templates import html_page
from web.request import Request
from web.response import Response
from web.router import Router


# ----------------------------
# Unified UI Candidate Model
# ----------------------------
@dataclass(frozen=True)
class UICandidate:
    # canonical id, used everywhere (curation.yaml, selected.yaml, /curate?id=...)
    url: str
    # actual open-able link (web URL or drive URL)
    open_url: str
    title: str
    source: str


def _strip(s: Any) -> str:
    return ("" if s is None else str(s)).strip()


def _as_web_id(raw_url: str) -> str:
    u = _strip(raw_url)
    if not u:
        return ""
    if u.startswith("web:"):
        # normalize: web:<no fragment>
        base = u[len("web:") :].split("#", 1)[0].strip()
        return f"web:{base}" if base else ""
    # raw web url => canonical
    base = u.split("#", 1)[0].strip()
    return f"web:{base}" if base else ""


def _web_open_url(content_id: str) -> str:
    s = _strip(content_id)
    if s.startswith("web:"):
        return s[len("web:") :].strip()
    return s


def _as_gdrive_id(raw_id: str) -> str:
    r = _strip(raw_id)
    if not r:
        return ""
    if r.startswith("gdrive:"):
        return r
    if r.startswith("doc:"):
        return "gdrive:" + _strip(r[len("doc:") :])
    # plain doc id
    return "gdrive:" + r


def _ui_from_web_candidate(c: Any) -> UICandidate | None:
    raw_url = _strip(getattr(c, "url", "") or getattr(c, "original_url", ""))
    cid = _as_web_id(raw_url)
    if not cid:
        return None

    title = _strip(getattr(c, "title", "")) or _web_open_url(cid)
    source = _strip(getattr(c, "source", "")) or "web"

    return UICandidate(
        url=cid,
        open_url=_web_open_url(cid),
        title=title,
        source=source,
    )


def _ui_from_doc_candidate(d: dict[str, Any]) -> UICandidate | None:
    if not isinstance(d, dict):
        return None

    did = _as_gdrive_id(d.get("id") or "")
    if not did:
        return None

    title = _strip(d.get("title") or did)
    open_url = _strip(d.get("url") or "") or "#"

    return UICandidate(
        url=did,
        open_url=open_url,
        title=title,
        source="doc",
    )


# ----------------------------
# Routing
# ----------------------------
def register(router: Router) -> None:
    router.get("/", get_main)
    router.get("/refresh", get_refresh)
    router.post("/save", post_save)
    router.post("/seen/reset", post_seen_reset)


def _redir_status(status: str) -> Response:
    qs = urlencode({"status": status}, doseq=False)
    return Response.redirect(f"/?{qs}")


def _parse_post_form(req: Request) -> dict[str, list[str]]:
    raw = req.body.decode("utf-8", errors="replace")
    return parse_qs(raw, keep_blank_values=True)


def post_seen_reset(req: Request, params: dict[str, Any] | None = None) -> Response:
    form = _parse_post_form(req)
    if form.get("confirm", [""])[0] != "1":
        return _redir_status("Reset seen URLs cancelled")

    reset_seen_urls()
    return _redir_status("Reset seen URLs (seen_urls.json cleared)")


def get_refresh(req: Request) -> Response:
    try:
        parsed = urlparse(req.path)
        qs = parse_qs(parsed.query)
        ignore_seen = qs.get("ignore_seen", ["0"])[0] == "1"

        res = refresh_candidates(ignore_seen=ignore_seen)

        watch_note = ""
        try:
            started = watch_service.start_scan()
            watch_note = " + watch scan started" if started else " + watch scan already running"
        except Exception as e:
            watch_note = f" + watch scan failed: {e}"

        err_note = f" (errors:{res.error_count})" if getattr(res, "error_count", 0) else ""
        note = " (ignored seen URLs)" if ignore_seen else ""

        doc_count = getattr(res, "doc_count", 0)
        return _redir_status(f"Refreshed candidate list (docs:{doc_count}){err_note}{note}{watch_note}")

    except Exception as e:
        return _redir_status(f"Refresh failed: {e}")


def post_save(req: Request) -> Response:
    try:
        form = _parse_post_form(req)

        picked = form.get("picked", [])
        subject = (form.get("subject", [DEFAULT_SUBJECT])[0] or DEFAULT_SUBJECT).strip()
        intro = (form.get("intro", [DEFAULT_INTRO])[0] or DEFAULT_INTRO).strip()

        n = save_picks(subject=subject, intro=intro, picked_urls=picked)
        return _redir_status(f"Saved {n} item(s) to selected.yaml")

    except Exception as e:
        return _redir_status(f"Save failed: {e}")


# ----------------------------
# Curation badges / indicators
# ----------------------------
def _is_curated(cur: dict[str, Any], key: str) -> bool:
    """
    True if ANY curation signal exists for this canonical key.
    """
    if not key:
        return False

    rec = cur.get(key)
    if not rec:
        # fallback if older file normalized differently
        rec = cur.get(curation_store.norm_url(key))

    if not isinstance(rec, dict):
        return False

    if _strip(rec.get("final_blurb")):
        return True

    xs = rec.get("excerpts")
    if isinstance(xs, list) and any(_strip(x) for x in xs if isinstance(x, str)):
        return True

    if _strip(rec.get("selected_image")):
        return True

    if _strip(rec.get("title")):
        return True

    if _strip(rec.get("subtitle")):
        return True

    return False


def get_main(req: Request, params: dict[str, Any] | None = None) -> Response:
    status = req.query_first.get("status") or ""

    # 1) Build ONE unified list (web + doc) for the UI
    web_raw = load_persisted_candidates()
    doc_raw = load_doc_candidates() or []

    candidates: list[UICandidate] = []
    for c in web_raw:
        ui = _ui_from_web_candidate(c)
        if ui:
            candidates.append(ui)

    for d in doc_raw:
        ui = _ui_from_doc_candidate(d)
        if ui:
            candidates.append(ui)

    debug(f"candidate sources: {[c.source for c in candidates]}")

    # 2) Selection state (selected.yaml uses the same canonical ids now)
    sel = load_selected()
    prechecked: set[str] = set()
    if isinstance(sel, dict):
        for it in sel.get("items") or []:
            if isinstance(it, dict) and it.get("url"):
                prechecked.add(_strip(it["url"]))

    subject = _strip(sel.get("subject")) if isinstance(sel, dict) else ""
    intro = _strip(sel.get("intro")) if isinstance(sel, dict) else ""
    if not subject:
        subject = DEFAULT_SUBJECT
    if not intro:
        intro = DEFAULT_INTRO

    # 3) Curation indicators keyed by canonical id
    cur = load_curation()

    has_blurb_by_url: dict[str, bool] = {}
    has_image_by_url: dict[str, bool] = {}

    for c in candidates:
        has_blurb_by_url[c.url] = _is_curated(cur, c.url)
        has_image_by_url[c.url] = bool(curation_store.get_curated_selected_image(cur, c.url))

    # 4) Render
    body = html_page(
        candidates=candidates,
        prechecked=prechecked,
        subject=subject,
        intro=intro,
        status=status,
        has_blurb_by_url=has_blurb_by_url,
        has_image_by_url=has_image_by_url,
    )
    return Response.html(body)
