from web.request import build_request
from web.response import Response
from web.router import Router


def _ok(_: object) -> Response:
    return Response.text("ok")


def test_router_returns_405_when_path_matches_but_method_does_not():
    r = Router()
    r.post("/save", _ok)  # POST-only route

    req = build_request(method="GET", raw_path="/save", headers={}, body=b"")
    resp = r.dispatch(req)

    assert resp.status == 405
    assert resp.headers.get("Allow") == "POST"
