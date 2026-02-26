from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Pattern

from .request import Request
from .response import Response


HandlerFn = Callable[[Request], Response]


@dataclass(frozen=True)
class _Route:
    method: str
    kind: str  # "exact" | "regex"
    pattern: str
    regex: Pattern[str] | None
    handler: HandlerFn


class Router:
    def __init__(self) -> None:
        self._routes: list[_Route] = []

    # --- Registration helpers ---
    def get(self, path: str, handler: HandlerFn) -> None:
        self._routes.append(_Route("GET", "exact", path, None, handler))

    def post(self, path: str, handler: HandlerFn) -> None:
        self._routes.append(_Route("POST", "exact", path, None, handler))

    def route_regex(self, method: str, pattern: str, handler: HandlerFn) -> None:
        self._routes.append(_Route(method.upper(), "regex", pattern, re.compile(pattern), handler))

    # --- Dispatch ---
    def dispatch(self, req: Request) -> Response:
        for r in self._routes:
            if r.method != req.method:
                continue

            if r.kind == "exact":
                if req.path == r.pattern:
                    return r.handler(req)

            elif r.kind == "regex":
                assert r.regex is not None
                if r.regex.match(req.path):
                    return r.handler(req)

        return Response.not_found(f"No route for {req.method} {req.path}")