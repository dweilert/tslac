# routes/export.py
from __future__ import annotations

from typing import Any

from services import export_service
from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router) -> None:
    router.get("/export/constant-contact.zip", get_constant_contact_zip)


def get_constant_contact_zip(
    req: Request,
    params: dict[str, Any] | None = None,
) -> Response:
    data, filename = export_service.build_constant_contact_zip()

    # Use the new helper
    return Response.download(
        data,
        filename=filename,
        content_type="application/zip",
    )
