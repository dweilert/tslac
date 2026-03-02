# services/export_service.py
from __future__ import annotations

import export_cc


def build_constant_contact_zip() -> tuple[bytes, str]:
    return export_cc.build_constant_contact_zip()
