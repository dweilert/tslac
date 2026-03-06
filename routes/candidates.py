# routes/candidates.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlencode

import storage.curation_store as curation_store
from core.templates import html_page
from services import watch_service
from services.candidates_service import (
    load_persisted_candidates,
    refresh_candidates,
    toggle_pick,
)
from storage.curation_store import load_curation
from storage.selected_store import load_selected
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


def _get_field(obj: Any, name: str) -> str:
    if isinstance(obj, dict):
        return _strip(obj.get(name))
    return _strip(getattr(obj, name, ""))


def _as_web_id(raw_url: str) -> str:
    u = _strip(raw_url)
    if not u:
        return ""
    if u.startswith("web:"):
        base = u[len("web:") :].split("#", 1)[0].strip()
        return f"web:{base}" if base else ""
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


def _gdrive_open_url(content_id: str) -> str:
    # content_id is "gdrive:<file_id>" or legacy "doc:<id>"
    cid = (content_id or "").strip()

    if cid.startswith("doc:"):
        cid = "gdrive:" + cid[len("doc:") :].strip()

    if not cid.startswith("gdrive:"):
        return ""

    file_id = cid[len("gdrive:") :].strip()
    if not file_id:
        return ""

    # Universal Drive open link: works for Docs, PDFs, DOCX, TXT, etc.
    return f"https://drive.google.com/open?id={file_id}"


def _ui_from_candidate(c: Any) -> UICandidate | None:
    """
    Accepts either:
      - object candidates (with attributes)
      - dict candidates (e.g. merged doc candidates)
    """
    raw_url = _get_field(c, "url") or _get_field(c, "original_url")
    # raw_url = (
    #     _get_field(c, "url")
    #     or _get_field(c, "original_url")
    #     or _get_field(c, "link")
    #     or _get_field(c, "href")
    #     or _get_field(c, "page_url")
    # )
    raw_title = _get_field(c, "title")
    raw_source = _get_field(c, "source")

    # Heuristic:
    # - explicit prefixes win (web:/doc:/gdrive:)
    # - http(s) => web
    # - otherwise treat as doc id => gdrive
    if raw_url.startswith(("web:", "http://", "https://")):
        cid = _as_web_id(raw_url)
        if not cid:
            return None
        open_url = _web_open_url(cid)
        title = raw_title or open_url
        source = raw_source or "web"
        return UICandidate(url=cid, open_url=open_url, title=title, source=source)

    if raw_url.startswith(("gdrive:", "doc:")):
        cid = _as_gdrive_id(raw_url)
        if not cid:
            return None
        open_url = _gdrive_open_url(cid)
        title = raw_title or open_url
        source = raw_source or "gdrive"
        return UICandidate(url=cid, open_url=open_url, title=title, source=source)

    # If it's not a URL and not prefixed, assume it is a bare doc id.
    # (This supports older doc lists that stored just the raw id.)
    cid = _as_gdrive_id(raw_url)
    if cid:
        open_url = _gdrive_open_url(cid)
        title = raw_title or open_url
        source = raw_source or "gdrive"
        return UICandidate(url=cid, open_url=open_url, title=title, source=source)

    return None


# ----------------------------
# Routing
# ----------------------------
def register(router: Router) -> None:
    router.get("/", get_main)
    router.get("/refresh", get_refresh)
    router.post("/selection/toggle", post_selection_toggle)


def _redir_status(status: str) -> Response:
    qs = urlencode({"status": status}, doseq=False)
    return Response.redirect(f"/?{qs}")


def _parse_post_form(req: Request) -> dict[str, list[str]]:
    raw = req.body.decode("utf-8", errors="replace")
    return parse_qs(raw, keep_blank_values=True)


def get_refresh(req: Request) -> Response:
    try:
        res = refresh_candidates()

        watch_note = ""
        try:
            started = watch_service.start_scan()
            watch_note = " + watch scan started" if started else " + watch scan already running"
        except Exception as e:
            watch_note = f" + watch scan failed: {e}"

        err_note = f" (errors:{res.error_count})" if getattr(res, "error_count", 0) else ""
        doc_count = getattr(res, "doc_count", 0)
        return _redir_status(f"Refreshed candidate list (docs:{doc_count}){err_note}{watch_note}")

    except Exception as e:
        return _redir_status(f"Refresh failed: {e}")


def post_selection_toggle(req: Request) -> Response:
    try:
        form = _parse_post_form(req)
        url = _strip(form.get("url", [""])[0])
        selected_raw = _strip(form.get("selected", [""])[0]).lower()

        if not url:
            return Response.json({"ok": False, "error": "Missing url"}, status=400)

        if selected_raw not in {"1", "true", "yes", "on", "0", "false", "no", "off"}:
            return Response.json({"ok": False, "error": "Invalid selected value"}, status=400)

        selected = selected_raw in {"1", "true", "yes", "on"}
        changed = toggle_pick(url=url, selected=selected)

        sel = load_selected()
        count = 0
        if isinstance(sel, dict):
            count = sum(
                1
                for it in (sel.get("items") or [])
                if isinstance(it, dict) and _strip(it.get("url"))
            )

        return Response.json({"ok": True, "changed": changed, "selected": selected, "count": count})

    except Exception as e:
        return Response.json({"ok": False, "error": str(e)}, status=500)


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

    # 1) Build ONE unified list for the UI (web + doc + watch if persisted)
    raw = load_persisted_candidates()

    candidates: list[UICandidate] = []
    for c in raw:
        ui = _ui_from_candidate(c)
        if ui:
            candidates.append(ui)

    # 2) Selection state (selected.yaml uses canonical ids)
    sel = load_selected()
    prechecked: set[str] = set()
    if isinstance(sel, dict):
        for it in sel.get("items") or []:
            if isinstance(it, dict) and it.get("url"):
                prechecked.add(_strip(it["url"]))

    subject = _strip(sel.get("subject")) if isinstance(sel, dict) else ""
    intro = _strip(sel.get("intro")) if isinstance(sel, dict) else ""
    if not subject:
        subject = ""
    if not intro:
        intro = ""

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
