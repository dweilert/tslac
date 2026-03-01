from web.response import Response


def test_redirect_sets_content_length_zero():
    resp = Response.redirect("/somewhere")
    assert resp.status == 302
    assert resp.headers["Location"] == "/somewhere"
    assert resp.headers["Content-Length"] == "0"
    assert resp.body == b""
