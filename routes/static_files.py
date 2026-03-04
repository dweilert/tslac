from __future__ import annotations

from pathlib import Path

from web.request import Request
from web.response import Response
from web.router import Router

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
IMAGES_DIR = Path(__file__).resolve().parents[1] / "images"


def register(router: Router) -> None:
    # serve /static/... (css, js)
    router.route_regex("GET", r"^/static/.*$", get_static)

    # serve /images/... (logo, etc.)
    router.route_regex("GET", r"^/images/.*$", get_images)


def get_static(req: Request, _params: dict | None = None) -> Response:
    rel = req.path[len("/static/") :]  # "css/app.css"
    return _serve_from(STATIC_DIR, rel)


def get_images(req: Request, _params: dict | None = None) -> Response:
    rel = req.path[len("/images/") :]  # "logo_no_name.png"
    return _serve_from(IMAGES_DIR, rel)


def _serve_from(base_dir: Path, rel: str) -> Response:
    # basic traversal protection
    if not rel or ".." in rel or rel.startswith("/"):
        return Response.not_found("Not found")

    base = base_dir.resolve()
    fpath = (base_dir / rel).resolve()

    if not str(fpath).startswith(str(base)):
        return Response.not_found("Not found")

    if not fpath.exists() or not fpath.is_file():
        return Response.not_found("Not found")

    data = fpath.read_bytes()
    ctype = _content_type(fpath.suffix.lower())

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
