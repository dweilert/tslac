from __future__ import annotations

from pathlib import Path

from web.request import Request
from web.response import Response
from web.router import Router


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def register(router: Router) -> None:
    # serve /static/... (css, js, images)
    router.route_regex("GET", r"^/static/.*$", get_static)


def get_static(req: Request) -> Response:
    # req.path is like "/static/css/app.css"
    rel = req.path[len("/static/"):]  # "css/app.css"
    # basic traversal protection
    if ".." in rel or rel.startswith("/"):
        return Response.not_found("Not found")

    fpath = (STATIC_DIR / rel).resolve()
    if not str(fpath).startswith(str(STATIC_DIR.resolve())):
        return Response.not_found("Not found")

    if not fpath.exists() or not fpath.is_file():
        return Response.not_found("Not found")

    data = fpath.read_bytes()
    ctype = _content_type(fpath.suffix.lower())

    # Cache-busting can come later; keep caching modest for now
    headers = {
        "Content-Type": ctype,
        "Content-Length": str(len(data)),
        "Cache-Control": "no-cache",
    }
    return Response(status=200, headers=headers, body=data)


def _content_type(ext: str) -> str:
    return {
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
    }.get(ext, "application/octet-stream")