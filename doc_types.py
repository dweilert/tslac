from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass(frozen=True)
class DocRef:
    doc_id: str                 # "gdrive:<fileId>" or "local:<abs_path>"
    display_name: str           # filename for UI
    source: str                 # "gdrive" or "local"
    mime_type: Optional[str]    # may be None for local
    modified_ts: Optional[str]  # ISO string
    size: Optional[int]
    extra: Dict[str, str]       # file_id, path, parents, etc.    