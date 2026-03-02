from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocRef:
    doc_id: str  # "gdrive:<fileId>" or "local:<abs_path>"
    display_name: str  # filename for UI
    source: str  # "gdrive" or "local"
    mime_type: str | None  # may be None for local
    modified_ts: str | None  # ISO string
    size: int | None
    extra: dict[str, str]  # file_id, path, parents, etc.
