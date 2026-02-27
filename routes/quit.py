from __future__ import annotations

import threading
import time

from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router, server_ref) -> None:
    router.post("/quit", lambda req: quit_server(req, server_ref))


def quit_server(_: Request, server) -> Response:
    """
    Return response first, then shutdown server shortly after.
    """

    def shutdown():
        time.sleep(0.5)   # allow browser to receive response
        server.shutdown()

    threading.Thread(target=shutdown, daemon=True).start()

    html = """
    <html>
      <head>
        <title>Server stopped</title>
      </head>
      <body style="font-family:sans-serif;margin:40px;">
        <h2>Newsletter helper has stopped.</h2>
        <p>You may close this browser tab.</p>
      </body>
    </html>
    """

    return Response.html(html)