from __future__ import annotations
from http.server import ThreadingHTTPServer
from web.router import Router
from web.handler import RoutedHandler
from routes import preview, watch, api, curate_doc, curate_article, img_proxy
from routes import candidates, health, quit as quit_route, static_files
from web.handler import RoutedHandler


import os

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
    return r

def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))

    httpd = ThreadingHTTPServer((host, port), RoutedHandler)

    router = build_router(httpd)
    RoutedHandler.router = router

    print(f"Serving on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()