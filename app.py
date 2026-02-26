from __future__ import annotations

import os
from http.server import ThreadingHTTPServer

from web.router import Router
from web.handler import make_handler
from routes import preview, home
from routes import home, preview, watch, api, curate_doc, curate_article, img_proxy


def build_router() -> Router:
    r = Router()
    # Register per-feature routes here:
    home.register(r)
    preview.register(r)
    watch.register(r)
    api.register(r)
    curate_doc.register(r)
    curate_article.register(r)
    img_proxy.register(r)
    return r


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))

    router = build_router()
    handler_cls = make_handler(router)

    httpd = ThreadingHTTPServer((host, port), handler_cls)
    print(f"Serving on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()