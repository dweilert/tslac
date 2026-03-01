from __future__ import annotations

from datetime import datetime
from typing import Any

import yaml

from config import CURATION_FILE
from util.urls import norm_url


def load_curation() -> dict[str, Any]:
    if not CURATION_FILE.exists():
        return {}
    try:
        data = yaml.safe_load(CURATION_FILE.read_text("utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_curation(cur: dict[str, Any]) -> None:
    CURATION_FILE.write_text(
        yaml.safe_dump(cur, sort_keys=False, allow_unicode=True),
        "utf-8",
    )


def _get_rec(cur: dict[str, Any], url: str) -> dict[str, Any]:
    url = norm_url(url)
    rec = cur.get(url)
    if not isinstance(rec, dict):
        rec = {}
        cur[url] = rec
    return rec


# ----------------------------
# Blurbs + excerpts
# ----------------------------
def get_curated_blurb(cur: dict[str, Any], url: str) -> str:
    rec = cur.get(norm_url(url))
    if isinstance(rec, dict):
        v = rec.get("final_blurb")
        if isinstance(v, str):
            return v
    return ""


def upsert_curated_blurb(url: str, final_blurb: str) -> None:
    cur = load_curation()
    rec = _get_rec(cur, url)
    rec["final_blurb"] = (final_blurb or "").strip()
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_curation(cur)


def get_curated_excerpts(cur: dict[str, Any], url: str) -> list[str]:
    rec = cur.get(norm_url(url))
    if isinstance(rec, dict):
        xs = rec.get("excerpts")
        if isinstance(xs, list):
            return [x.strip() for x in xs if isinstance(x, str) and x.strip()]
    return []


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


# ----------------------------
# Image crops (curation.yaml)
# ----------------------------
def get_curated_image_crops(cur: dict[str, Any], url: str) -> dict[str, Any]:
    """Return dict keyed by image src: {src: {x,y,w,h,iw,ih,cw,ch}}"""
    rec = cur.get(norm_url(url))
    if isinstance(rec, dict):
        v = rec.get("image_crops")
        if isinstance(v, dict):
            return v
    return {}


def upsert_curated_image_crop(url: str, img_src: str, crop: dict[str, Any]) -> None:
    """
    Stores a crop box for a given image src.
    crop should include:
      x,y,w,h (canvas coords)
      iw,ih (image natural size)
      cw,ch (canvas size)
    """
    url = norm_url(url)
    img_src = (img_src or "").strip()
    if not url or not img_src or not isinstance(crop, dict):
        return

    # basic validation
    for k in ("ix", "iy", "iw", "ih", "img_w", "img_h"):
        if k not in crop:
            return

    cur = load_curation()
    rec = cur.get(url)
    if not isinstance(rec, dict):
        rec = {}
        cur[url] = rec

    crops = rec.get("image_crops")
    if not isinstance(crops, dict):
        crops = {}
        rec["image_crops"] = crops

    crops[img_src] = crop
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
            return v.strip()
    return ""


def upsert_curated_selected_image(url: str, img_src: str) -> None:
    url = norm_url(url)
    img_src = (img_src or "").strip()
    if not url or not img_src:
        return

    cur = load_curation()
    rec = _get_rec(cur, url)
    rec["selected_image"] = img_src
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_curation(cur)


def clear_curated_selected_image(url: str) -> None:
    url = norm_url(url)
    if not url:
        return
    cur = load_curation()
    rec = cur.get(url)
    if not isinstance(rec, dict):
        return
    if "selected_image" in rec:
        rec.pop("selected_image", None)
        rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
        save_curation(cur)
