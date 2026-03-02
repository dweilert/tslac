# services/export_service.py
from __future__ import annotations

import constant_contact_exporter


def build_constant_contact_zip() -> tuple[bytes, str]:
    return constant_contact_exporter.build_constant_contact_zip()
