from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

APP_DIR = Path(__file__).resolve().parent.parent
CURATION_FILE = APP_DIR / "curation.yaml"


def norm_url(url: str) -> str:
    return (url or "").strip()


def load_curation() -> dict[str, Any]:
    if not CURATION_FILE.exists():
        return {}
    try:
        return yaml.safe_load(CURATION_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def save_curation(cur: dict[str, Any]) -> None:
    CURATION_FILE.write_text(yaml.safe_dump(cur, sort_keys=False), encoding="utf-8")


def _get_rec(cur: dict[str, Any], url: str) -> dict[str, Any]:
    k = norm_url(url)
    rec = cur.get(k)
    if not isinstance(rec, dict):
        rec = {}
        cur[k] = rec
    return rec


# ----------------------------
# Blurb + excerpts (curation.yaml)
# ----------------------------
def get_curated_blurb(cur: dict[str, Any], url: str) -> str:
    rec = cur.get(norm_url(url))
    if isinstance(rec, dict):
        v = rec.get("final_blurb")
        if isinstance(v, str):
            return v
    return ""


def get_curated_excerpts(cur: dict[str, Any], url: str) -> list[str]:
    rec = cur.get(norm_url(url))
    if isinstance(rec, dict):
        xs = rec.get("excerpts")
        if isinstance(xs, list):
            return [x.strip() for x in xs if isinstance(x, str) and x.strip()]
    return []


def upsert_curated_blurb(url: str, final_blurb: str) -> None:
    cur = load_curation()
    rec = _get_rec(cur, url)
    rec["final_blurb"] = (final_blurb or "").strip()
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_curation(cur)


def add_curated_excerpt(url: str, excerpt: str) -> None:
    excerpt = (excerpt or "").strip()
    if not excerpt:
        return
    cur = load_curation()
    rec = _get_rec(cur, url)
    xs = rec.get("excerpts")
    if not isinstance(xs, list):
        xs = []
        rec["excerpts"] = xs
    if excerpt not in xs:
        xs.append(excerpt)
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_curation(cur)


def pop_curated_excerpt(url: str) -> None:
    cur = load_curation()
    rec = cur.get(norm_url(url))
    if not isinstance(rec, dict):
        return
    xs = rec.get("excerpts")
    if isinstance(xs, list) and xs:
        xs.pop()
        rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
        save_curation(cur)


def clear_curated_excerpts(url: str) -> None:
    cur = load_curation()
    rec = _get_rec(cur, url)
    rec["excerpts"] = []
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_curation(cur)


def delete_curated_excerpt(url: str, idx: int) -> None:
    """Delete a specific excerpt by 0-based index."""
    cur = load_curation()
    rec = cur.get(norm_url(url))
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
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_curation(cur)


def move_curated_excerpt(url: str, idx: int, direction: str) -> None:
    """Move excerpt up/down by swapping with neighbor."""
    cur = load_curation()
    rec = cur.get(norm_url(url))
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
    if dir_norm == "up":
        j = i - 1
    elif dir_norm == "down":
        j = i + 1
    else:
        return

    if j < 0 or j >= len(xs):
        return

    xs[i], xs[j] = xs[j], xs[i]
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_curation(cur)


# ----------------------------
# Image crops (curation.yaml)
# ----------------------------
def get_curated_image_crops(cur: dict[str, Any], url: str) -> dict[str, Any]:
    """image_crops: {src: {x,y,w,h,iw,ih,cw,ch}}"""
    rec = cur.get(norm_url(url))
    if isinstance(rec, dict):
        v = rec.get("image_crops")
        if isinstance(v, dict):
            return v
    return {}


def upsert_curated_image_crop(url: str, img_src: str, crop: dict[str, Any]) -> None:
    cur = load_curation()
    rec = _get_rec(cur, url)
    crops = rec.get("image_crops")
    if not isinstance(crops, dict):
        crops = {}
        rec["image_crops"] = crops
    crops[(img_src or "").strip()] = crop
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_curation(cur)


# ----------------------------
# Selected image (curation.yaml)
# ----------------------------
def get_curated_selected_image(cur: dict[str, Any], url: str) -> str:
    rec = cur.get(norm_url(url))
    if isinstance(rec, dict):
        v = rec.get("selected_image")
        if isinstance(v, str):
            return v
    return ""


def upsert_curated_selected_image(url: str, img_src: str) -> None:
    cur = load_curation()
    rec = _get_rec(cur, url)
    rec["selected_image"] = (img_src or "").strip()
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_curation(cur)


def clear_curated_selected_image(url: str) -> None:
    cur = load_curation()
    rec = _get_rec(cur, url)
    rec["selected_image"] = ""
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_curation(cur)
