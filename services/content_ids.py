# services/content_ids.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Origin = Literal["web", "gdrive", "local"]

@dataclass(frozen=True)
class ContentRef:
    content_id: str   # canonical: web:..., gdrive:..., local:...
    origin: Origin
    open_url: str     # real URL for opening in browser (or empty for local if not applicable)


def canonical_content_id(raw: str) -> str:
    """
    Canonicalize ANY incoming identifier:
      - http(s)://...         -> web:http(s)://...
      - web:http(s)://...     -> web:http(s)://...     (strip fragments)
      - gdrive:<id>           -> gdrive:<id>
      - doc:<id>              -> gdrive:<id>
      - local:<something>     -> local:<something>
    """
    s = (raw or "").strip()
    if not s:
        return ""

    # Convert doc: -> gdrive:
    if s.startswith("doc:"):
        s = "gdrive:" + s[len("doc:") :].strip()

    # Already canonical
    if s.startswith(("web:", "gdrive:", "local:")):
        if s.startswith("web:"):
            base = s[len("web:") :].split("#", 1)[0].strip()
            return f"web:{base}" if base else ""
        return s

    # Raw web URL
    if s.startswith(("http://", "https://")):
        base = s.split("#", 1)[0].strip()
        return f"web:{base}" if base else ""

    # Unknown: return as-is (caller may reject)
    return s


def split_content_id(content_id: str) -> ContentRef:
    """
    Turn canonical id into (origin, open_url).
    """
    cid = canonical_content_id(content_id)
    if not cid:
        return ContentRef("", "web", "")

    if cid.startswith("web:"):
        url = cid[len("web:") :].strip()
        return ContentRef(cid, "web", url)

    if cid.startswith("gdrive:"):
        doc_id = cid[len("gdrive:") :].strip()
        # choose the open URL format you want
        open_url = f"https://docs.google.com/document/d/{doc_id}/edit" if doc_id else ""
        return ContentRef(cid, "gdrive", open_url)

    if cid.startswith("local:"):
        return ContentRef(cid, "local", "")

    # fallback
    return ContentRef(cid, "web", "")