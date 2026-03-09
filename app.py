from __future__ import annotations

import os
from http.server import ThreadingHTTPServer

from routes import (
    api,
    candidates,
    crop,
    curate_article,
    export as export_routes,
    health,
    img_proxy,
    preview,
    quit as quit_route,
    static_files,
    watch,
)

# import config_ui
from setup import config_ui
from util.logutil import info
from web.handler import RoutedHandler
from web.router import Router
from setup import config_ui, secrets_env


def build_router(server) -> Router:
    r = Router()
    api.register(r)
    candidates.register(r)
    config_ui.register(r)
    crop.register(r)
    curate_article.register(r)
    export_routes.register(r)
    health.register(r)
    img_proxy.register(r)
    preview.register(r)
    quit_route.register(r, server)
    static_files.register(r)
    watch.register(r)

    return r


def main() -> None:
    secrets_env.load_env()
    
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))

    httpd = ThreadingHTTPServer((host, port), RoutedHandler)

    router = build_router(httpd)
    RoutedHandler.router = router

    info(f"Serving on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
