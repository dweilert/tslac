from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from typing import Callable

from web.request import build_request
from web.router import Router
from web.response import Response
from web.request import Request

class RoutedHandler(BaseHTTPRequestHandler):
    router: Router  # set by factory

    def log_message(self, format: str, *args) -> None:
        # Optional: keep the console quieter. Comment this out if you want default logging.
        return

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    # def do_GET(self):
    #     assert self.router is not None
    #     req = Request.from_handler(self)  # if you have this helper
    #     self.router.dispatch(req, self)

    # def do_POST(self):
    #     assert self.router is not None
    #     req = Request.from_handler(self)
    #     self.router.dispatch(req, self)


    def _handle(self, method: str) -> None:
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except Exception:
            length = 0

        body = self.rfile.read(length) if length > 0 else b""
        req = build_request(method=method, raw_path=self.path, headers=self.headers, body=body)

        try:
            resp = self.router.dispatch(req)
        except Exception as e:
            resp = Response.bad_request(f"Unhandled error: {e}")

        self.send_response(resp.status)
        for k, v in (resp.headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if resp.body:
            self.wfile.write(resp.body)


# def make_handler():
#     class Handler(BaseHTTPRequestHandler):
#         router = None

#         def do_GET(self):
#             self.router.dispatch(self)

#         def do_POST(self):
#             self.router.dispatch(self)

#     return Handler