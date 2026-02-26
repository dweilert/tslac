from __future__ import annotations

from web.request import Request
from web.response import Response
from web.router import Router
from typing import Dict, List
from urllib.parse import parse_qs

import templates
import watcher
import watch_store


def register(router: Router) -> None:
    router.get("/watch", get_watch_page)
    router.get("/watch/status", get_watch_status)
    router.get("/watch/scan", get_watch_scan)
    router.get("/watch/cancel", get_watch_cancel)
    router.post("/watch/save", post_watch_save)


def get_watch_status(_: Request) -> Response:
    st = watcher.get_watch_status()
    return Response.json(st)


def get_watch_scan(_: Request) -> Response:
    try:
        started = watcher.start_watch_scan_async()
        return Response.redirect("/watch?status=" + ("Scan+started" if started else "Scan+already+running"))
    except Exception as e:
        msg = str(e).replace(" ", "+")
        return Response.redirect(f"/watch?status=Scan+failed:+{msg}")


def get_watch_cancel(_: Request) -> Response:
    watcher.cancel_watch_scan()
    return Response.redirect("/watch?status=Cancel+requested")


def get_watch_page(req: Request) -> Response:
    try:
        status = (req.query_first.get("status") or "")
        cfg = watch_store.load_watch()
        latest = watcher.load_latest_results()

        sites_text = "\n".join(cfg.sites or [])
        topics_text = "\n".join(cfg.topics or [])

        body = templates.watch_page_html(
            sites_text=sites_text,
            topics_text=topics_text,
            status=status,
            latest=latest,
        )
        return Response.html(body)
    except Exception:
        import traceback
        tb = traceback.format_exc()
        return Response.html(f"<pre>\nWatch error:\n{tb}\n</pre>", status=400)


def _parse_post_form(req: Request) -> dict[str, str]:
    """
    Parse typical HTML form posts. Supports:
      - application/x-www-form-urlencoded
      - multipart/form-data (best-effort minimal parsing if your templates use it)

    Returns first value for each key.
    """
    ctype = (req.headers.get("Content-Type") or "").lower()

    # Common case: application/x-www-form-urlencoded
    if "application/x-www-form-urlencoded" in ctype or ctype == "":
        raw = req.body.decode("utf-8", errors="replace")
        q = parse_qs(raw, keep_blank_values=True)
        return {k: (v[0] if v else "") for k, v in q.items()}

    # If your form is multipart, the easiest fix is to set the form to urlencoded.
    # But we can still do a basic extraction for small text fields.
    if "multipart/form-data" in ctype:
        # Minimal multipart parsing (text fields only). Good enough for textarea fields.
        boundary = None
        for part in ctype.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                boundary = part.split("=", 1)[1].strip().strip('"')
        if not boundary:
            return {}

        data = req.body
        sep = ("--" + boundary).encode("utf-8")
        out: dict[str, str] = {}

        for chunk in data.split(sep):
            if b'Content-Disposition:' not in chunk:
                continue
            try:
                header_blob, value_blob = chunk.split(b"\r\n\r\n", 1)
            except ValueError:
                continue
            # name="field"
            hb = header_blob.decode("utf-8", errors="replace")
            name = None
            for token in hb.split(";"):
                token = token.strip()
                if token.startswith('name="') and token.endswith('"'):
                    name = token[6:-1]
                    break
            if not name:
                continue
            value = value_blob.strip()
            # strip trailing multipart terminator
            if value.endswith(b"--"):
                value = value[:-2]
            out[name] = value.decode("utf-8", errors="replace").strip()
        return out

    return {}


def _split_lines(text: str) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]    

# def post_watch_save(req: Request) -> Response:
#     form = _parse_post_form(req)

#     # These field names are typical. If yours differ, we can adjust quickly.
#     sites_text = form.get("sites_text") or form.get("sites") or ""
#     topics_text = form.get("topics_text") or form.get("topics") or ""

#     sites = _split_lines(sites_text)
#     topics = _split_lines(topics_text)

#     # Save using whatever API watch_store exposes (robust fallback)
#     try:
#         if hasattr(watch_store, "save_watch"):
#             # could be save_watch(cfg) or save_watch(sites, topics)
#             try:
#                 cfg = watch_store.load_watch()
#                 cfg.sites = sites
#                 cfg.topics = topics
#                 watch_store.save_watch(cfg)
#             except TypeError:
#                 watch_store.save_watch(sites, topics)
#         elif hasattr(watch_store, "save"):
#             watch_store.save({"sites": sites, "topics": topics})
#         else:
#             return Response.bad_request("watch_store has no save function (expected save_watch/save).")
#     except Exception as e:
#         msg = str(e).replace(" ", "+")
#         return Response.redirect(f"/watch?status=Save+failed:+{msg}")

#     return Response.redirect("/watch?status=Saved")


def post_watch_save(req: Request) -> Response:
    form = _parse_post_form(req)

    # Adjust these keys if your HTML uses different names
    sites_text = form.get("sites_text") or form.get("sites") or ""
    topics_text = form.get("topics_text") or form.get("topics") or ""

    try:
        # preserve current settings unless you also post settings fields
        cfg = watch_store.load_watch()
        watch_store.save_watch_from_lines(sites_text, topics_text, settings=cfg.settings)
    except Exception as e:
        msg = str(e).replace(" ", "+")
        return Response.redirect(f"/watch?status=Save+failed:+{msg}")

    return Response.redirect("/watch?status=Saved")