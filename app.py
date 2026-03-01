from __future__ import annotations

import os
from http.server import ThreadingHTTPServer

from logutil import info
from routes import (
    api,
    candidates,
    curate_article,
    curate_doc,
    health,
    img_proxy,
    preview,
    quit as quit_route,
    static_files,
    watch,
    crop,
)
from web.handler import RoutedHandler
from web.router import Router


def build_router(server) -> Router:
    r = Router()
    candidates.register(r)
    preview.register(r)
    watch.register(r)
    api.register(r)
    curate_doc.register(r)
    curate_article.register(r)
    img_proxy.register(r)
    health.register(r)
    quit_route.register(r, server)
    static_files.register(r)
    crop.register(r)
    return r


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))

    httpd = ThreadingHTTPServer((host, port), RoutedHandler)

    router = build_router(httpd)
    RoutedHandler.router = router

    info(f"Serving on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
