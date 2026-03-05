# storage/content_id.py
from __future__ import annotations

from urllib.parse import urlparse, urlunparse

# --- Canonical prefixes (keep existing keys stable) ---
# NOTE: We keep "gdrive:" because your curation.yaml already has it.
#       You can *display* "Doc" in UI via Candidate.source, but the key stays gdrive:...
WEB_PREFIX = "web:"
GDRIVE_PREFIX = "gdrive:"
LOCAL_PREFIX = "local:"


def _strip(s: str) -> str:
    return (s or "").strip()


def _strip_fragment(url: str) -> str:
    """
    For http(s) URLs: remove #fragment so same page maps to same record.
    """
    u = _strip(url)
    if not u:
        return ""
    try:
        p = urlparse(u)
        if p.scheme in ("http", "https"):
            p2 = p._replace(fragment="")
            return urlunparse(p2)
    except Exception:
        pass
    return u


def canonical_content_id(*, source: str, raw: str) -> str:
    s = _strip(source).lower()
    r = _strip(raw)
    if not r:
        return ""

    # Already canonical?
    if r.startswith(WEB_PREFIX):
        return WEB_PREFIX + _strip_fragment(r[len(WEB_PREFIX):])
    if r.startswith(GDRIVE_PREFIX) or r.startswith("doc:"):
        # Accept "doc:" as an alias, store as gdrive:
        if r.startswith("doc:"):
            return GDRIVE_PREFIX + _strip(r[len("doc:"):])
        return GDRIVE_PREFIX + _strip(r[len(GDRIVE_PREFIX):])
    if r.startswith(LOCAL_PREFIX):
        return LOCAL_PREFIX + _strip(r[len(LOCAL_PREFIX):])

    # Not prefixed yet: decide by source
    if s in ("doc", "gdrive"):
        return GDRIVE_PREFIX + r
    if s in ("local",):
        return LOCAL_PREFIX + r

    # Default web
    return WEB_PREFIX + _strip_fragment(r)


def real_web_url(raw: str) -> str:
    r = _strip(raw)
    if r.startswith(WEB_PREFIX):
        return _strip_fragment(r[len(WEB_PREFIX):])
    return r


def candidate_keys_for_lookup(*, source: str, raw: str) -> list[str]:
    """
    Keys to try when reading curation:
      1) canonical key
      2) legacy raw key (normalized for fragments if it's http(s))
    This supports older entries you still have under raw URLs.
    """
    canon = canonical_content_id(source=source, raw=raw)
    legacy = _strip_fragment(_strip(raw))
    out: list[str] = []
    for k in (canon, legacy):
        if k and k not in out:
            out.append(k)
    return out
