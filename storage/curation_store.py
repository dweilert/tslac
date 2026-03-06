# storage/curation_store.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import yaml

from setup.config import CURATION_FILE

print(CURATION_FILE)


# ----------------------------
# Helpers
# ----------------------------
def _as_dict(x: Any) -> dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """
    Atomic file write:
      write to sibling temp file, fsync, then Path.replace().
    Works well on macOS/Linux/Windows on the same filesystem.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")

    with tmp.open("w", encoding=encoding, newline="\n") as f:
        f.write(text)
        f.flush()
        try:
            import os

            os.fsync(f.fileno())
        except Exception:
            # fsync may fail on some filesystems; replace is the core safety mechanism
            pass

    tmp.replace(path)


def _normalize_http_url(url: str) -> str:
    """
    Normalize http(s) URLs for stable keys:
      - strip whitespace
      - remove fragment (#...)
    """
    u = (url or "").strip()
    if not u:
        return ""
    try:
        p = urlparse(u)
        if p.scheme in ("http", "https"):
            p = p._replace(fragment="")
            return urlunparse(p)
    except Exception:
        pass
    return u


def norm_key(key: str) -> str:
    """
    Normalize keys used in curation.yaml.

    Supports both:
      - legacy keys: raw http(s) urls (normalized)
      - new canonical ids: web:<url>, gdrive:<id>, local:<id>

    Rules:
      - If key starts with "web:", normalize the URL part and keep the prefix.
      - If key is a raw http(s) URL, normalize it as legacy.
      - Otherwise, strip whitespace (for doc ids / local ids).
    """
    k = (key or "").strip()
    if not k:
        return ""

    if k.startswith("web:"):
        url_part = k[4:]
        return "web:" + _normalize_http_url(url_part)

    # Legacy raw URL key (kept for backward compatibility)
    if "://" in k:
        return _normalize_http_url(k)

    return k


def legacy_key_for(candidate_id: str) -> str:
    """
    Backward-compat key lookup for previously saved web curations.

    If candidate_id is web:<url>, return the normalized URL (no prefix)
    which is what older curations used as the key.
    """
    cid = (candidate_id or "").strip()
    if cid.startswith("web:"):
        return _normalize_http_url(cid[4:])
    return ""


def _touch(rec: dict[str, Any]) -> None:
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")


def _get_rec(cur: dict[str, Any], key: str) -> dict[str, Any]:
    k = norm_key(key)
    rec = cur.get(k)
    if not isinstance(rec, dict):
        rec = {}
        cur[k] = rec
    return rec


def _get_rec_with_fallback(cur: dict[str, Any], key: str) -> dict[str, Any] | None:
    """
    Read helper:
      1) try normalized key
      2) if key is web:<url>, also try legacy normalized url key
    """
    k = norm_key(key)
    rec = cur.get(k)
    if isinstance(rec, dict):
        return rec

    legacy = legacy_key_for(key)
    if legacy:
        rec2 = cur.get(legacy)
        if isinstance(rec2, dict):
            return rec2

    return None


def _is_valid_crop(crop: dict[str, Any]) -> bool:
    required = ("ix", "iy", "iw", "ih")
    for k in required:
        if k not in crop:
            return False
    try:
        iw = int(crop.get("iw", 0))
        ih = int(crop.get("ih", 0))
        return iw > 0 and ih > 0
    except Exception:
        return False


# ----------------------------
# Load / Save (YAML)
# ----------------------------
def load_curation() -> dict[str, Any]:
    """
    Load curation.yaml.

    Always returns a dict. If missing or invalid YAML, returns {}.
    """
    if not CURATION_FILE.exists():
        return {}

    try:
        data = yaml.safe_load(CURATION_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return _as_dict(data)


def save_curation(cur: dict[str, Any]) -> None:
    """
    Save curation.yaml atomically.
    """
    text = yaml.safe_dump(cur, sort_keys=False, allow_unicode=True)
    _atomic_write_text(CURATION_FILE, text, encoding="utf-8")


# ----------------------------
# Blurb + excerpts (curation.yaml)
# ----------------------------
def get_curated_blurb(cur: dict[str, Any], key: str) -> str:
    rec = _get_rec_with_fallback(cur, key)
    if isinstance(rec, dict):
        v = rec.get("final_blurb")
        if isinstance(v, str):
            return v
    return ""


def get_curated_excerpts(cur: dict[str, Any], key: str) -> list[str]:
    rec = _get_rec_with_fallback(cur, key)
    if isinstance(rec, dict):
        xs = rec.get("excerpts")
        if isinstance(xs, list):
            return [x.strip() for x in xs if isinstance(x, str) and x.strip()]
    return []


def upsert_curated_blurb(key: str, final_blurb: str) -> None:
    cur = load_curation()
    rec = _get_rec(cur, key)
    rec["final_blurb"] = (final_blurb or "").strip()
    _touch(rec)
    save_curation(cur)


def add_curated_excerpt(key: str, excerpt: str) -> None:
    excerpt = (excerpt or "").strip()
    if not excerpt:
        return

    cur = load_curation()
    rec = _get_rec(cur, key)

    xs = rec.get("excerpts")
    if not isinstance(xs, list):
        xs = []
        rec["excerpts"] = xs

    if excerpt not in xs:
        xs.append(excerpt)

    _touch(rec)
    save_curation(cur)


def pop_curated_excerpt(key: str) -> None:
    cur = load_curation()
    rec = _get_rec_with_fallback(cur, key)
    if not isinstance(rec, dict):
        return

    xs = rec.get("excerpts")
    if isinstance(xs, list) and xs:
        xs.pop()
        _touch(rec)
        save_curation(cur)


def clear_curated_excerpts(key: str) -> None:
    cur = load_curation()
    rec = _get_rec(cur, key)
    rec["excerpts"] = []
    _touch(rec)
    save_curation(cur)


def delete_curated_excerpt(key: str, idx: int) -> None:
    cur = load_curation()
    rec = _get_rec_with_fallback(cur, key)
    if not isinstance(rec, dict):
        return

    xs = rec.get("excerpts")
    if not isinstance(xs, list):
        return

    try:
        i = int(idx)
    except Exception:
        return

    if i < 0 or i >= len(xs):
        return

    xs.pop(i)
    _touch(rec)
    save_curation(cur)


def move_curated_excerpt(key: str, idx: int, direction: str) -> None:
    cur = load_curation()
    rec = _get_rec_with_fallback(cur, key)
    if not isinstance(rec, dict):
        return

    xs = rec.get("excerpts")
    if not isinstance(xs, list):
        return

    try:
        i = int(idx)
    except Exception:
        return

    if i < 0 or i >= len(xs):
        return

    dir_norm = (direction or "").strip().lower()
    j = i - 1 if dir_norm == "up" else i + 1 if dir_norm == "down" else None
    if j is None or j < 0 or j >= len(xs):
        return

    xs[i], xs[j] = xs[j], xs[i]
    _touch(rec)
    save_curation(cur)


# ----------------------------
# Image crops (curation.yaml)
# ----------------------------
def get_curated_image_crops(cur: dict[str, Any], key: str) -> dict[str, Any]:
    rec = _get_rec_with_fallback(cur, key)
    if isinstance(rec, dict):
        v = rec.get("image_crops")
        if isinstance(v, dict):
            return v
    return {}


def upsert_curated_image_crop(key: str, img_src: str, crop: dict[str, Any]) -> None:
    if not isinstance(crop, dict) or not _is_valid_crop(crop):
        return

    img_key = (img_src or "").strip()
    if not img_key:
        return

    cur = load_curation()
    rec = _get_rec(cur, key)

    crops = rec.get("image_crops")
    if not isinstance(crops, dict):
        crops = {}
        rec["image_crops"] = crops

    crops[img_key] = crop
    _touch(rec)
    save_curation(cur)


# ----------------------------
# Selected image (curation.yaml)
# ----------------------------
def get_curated_selected_image(cur: dict[str, Any], key: str) -> str:
    rec = _get_rec_with_fallback(cur, key)
    if isinstance(rec, dict):
        v = rec.get("selected_image")
        if isinstance(v, str):
            return v
    return ""


def clear_curated_selected_image(key: str) -> None:
    """
    Remove the stored selected image for this key/content_id.
    """
    cur = load_curation()
    rec = _get_rec(cur, key)

    for f in ("selected_image", "img_src", "image", "hero_image"):
        if f in rec:
            rec.pop(f, None)

    _touch(rec)
    save_curation(cur)


def upsert_curated_selected_image(key: str, img_src: str) -> None:
    cur = load_curation()
    rec = _get_rec(cur, key)
    rec["selected_image"] = (img_src or "").strip()
    _touch(rec)
    save_curation(cur)


def norm_url(url: str) -> str:
    # Backward-compatible alias for older callers.
    return norm_key(url)


# ----------------------------
# Title / Subtitle (curation.yaml)
# ----------------------------


def get_curated_title(cur: dict[str, Any], url: str) -> str:
    rec = cur.get(norm_url(url))
    if isinstance(rec, dict):
        v = rec.get("title")
        if isinstance(v, str):
            return v
    return ""


def get_curated_subtitle(cur: dict[str, Any], url: str) -> str:
    rec = cur.get(norm_url(url))
    if isinstance(rec, dict):
        v = rec.get("subtitle")
        if isinstance(v, str):
            return v
    return ""


def upsert_curated_title(url: str, title: str) -> None:
    cur = load_curation()
    rec = _get_rec(cur, url)
    rec["title"] = (title or "").strip()
    _touch(rec)
    save_curation(cur)


def upsert_curated_subtitle(url: str, subtitle: str) -> None:
    cur = load_curation()
    rec = _get_rec(cur, url)
    rec["subtitle"] = (subtitle or "").strip()
    _touch(rec)
    save_curation(cur)
