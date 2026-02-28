from templates import _esc

def test_esc_escapes_html():
    assert _esc('<script>alert("x")</script>') == "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"