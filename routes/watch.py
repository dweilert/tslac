from __future__ import annotations

from urllib.parse import parse_qs, urlencode

from services import watch_service
from util.logutil import error
from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router) -> None:
    router.get("/watch/status", get_watch_status)
    router.get("/watch/scan", get_watch_scan)
    router.get("/watch/cancel", get_watch_cancel)
    router.get("/watch", get_watch_redirect)


def _redir_watch_status(status: str) -> Response:
    qs = urlencode({"status": status}, doseq=False)
    return Response.redirect(f"/watch?{qs}")


def get_watch_status(_: Request) -> Response:
    st = watch_service.get_status()
    return Response.json(st)


def get_watch_scan(_: Request) -> Response:
    try:
        started = watch_service.start_scan()
        return _redir_watch_status("Scan started" if started else "Scan already running")
    except Exception as e:
        # Log server-side; keep user message short
        error("Watch scan failed", exc_info=True)
        return _redir_watch_status(f"Scan failed: {e}")


def get_watch_cancel(_: Request) -> Response:
    try:
        watch_service.cancel_scan()
        return _redir_watch_status("Cancel requested")
    except Exception:
        error("Watch cancel failed", exc_info=True)
        return _redir_watch_status("Cancel failed")


def get_watch_redirect(_: Request, _params: dict | None = None) -> Response:
    # Watch configuration is now managed in /config.
    return Response.redirect("/config")


def _parse_post_form(req: Request) -> dict[str, str]:
    """
    Parse typical HTML form posts. Supports:
      - application/x-www-form-urlencoded
      - multipart/form-data (best-effort minimal parsing if your templates use it)

    Returns first value for each key.
    """
    ctype = (req.headers.get("Content-Type") or "").lower()

    if "application/x-www-form-urlencoded" in ctype or ctype == "":
        raw = req.body.decode("utf-8", errors="replace")
        q = parse_qs(raw, keep_blank_values=True)
        return {k: (v[0] if v else "") for k, v in q.items()}

    if "multipart/form-data" in ctype:
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
            if b"Content-Disposition:" not in chunk:
                continue
            try:
                header_blob, value_blob = chunk.split(b"\r\n\r\n", 1)
            except ValueError:
                continue

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
            if value.endswith(b"--"):
                value = value[:-2]
            out[name] = value.decode("utf-8", errors="replace").strip()

        return out

    return {}
