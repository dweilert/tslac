# constant_contact_exporter.py
from __future__ import annotations

import html
import io
import json
import urllib.request
import zipfile
from contextlib import suppress
from datetime import datetime
from typing import Any
from urllib.parse import quote, unquote, urljoin, urlparse

from PIL import Image

from storage.curation_store import load_curation, norm_key, norm_url
from storage.selected_store import load_selected


# -----------------------------
# Helpers
# -----------------------------
def _esc(s: object) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def _content_id_from_selected_item(it: dict[str, Any]) -> str:
    """
    Selected items may be:
      - {"id": "web:<url>", "url": "<url>"}  (new)
      - {"url": "<url>"}                    (old)
    """
    cid = (it.get("id") or "").strip()
    if cid:
        return cid
    url = (it.get("url") or "").strip()
    return f"web:{url}" if url else ""


def _safe_url(url: object) -> str:
    """Allow only http(s) (and optionally site-relative). Return '#' if unsafe."""
    if not url:
        return "#"
    u = str(url).strip()
    p = urlparse(u)

    if p.scheme in ("http", "https"):
        return _esc(u)

    if p.scheme == "" and u.startswith("/"):
        return _esc(u)

    return "#"


def _is_http_url(u: str) -> bool:
    try:
        p = urlparse((u or "").strip())
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def _normalize_url_for_fetch(u: str, base: str = "") -> str:
    """
    - Allows relative u by resolving against base
    - Percent-encodes path/query to avoid spaces/control chars
    """
    u = (u or "").strip()
    base = (base or "").strip()

    if base:
        with suppress(Exception):
            u = urljoin(base, u)

    u = unquote(u)
    p = urlparse(u)

    if not (p.scheme in ("http", "https") and p.netloc):
        return u

    safe_path = quote(p.path, safe="/%")
    safe_query = quote(p.query, safe="=&?/%")
    return p._replace(path=safe_path, query=safe_query).geturl()


def _norm_img_key(u: str) -> str:
    return _normalize_url_for_fetch(u, base="")


def _fetch_bytes(url: str, timeout: int = 20) -> tuple[bytes, str]:
    url = (url or "").strip()
    if not _is_http_url(url):
        raise ValueError(f"Not an http(s) url: {url}")

    referer = ""
    with suppress(Exception):
        pp = urlparse(url)
        referer = f"{pp.scheme}://{pp.netloc}/"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "tslac-newsletter-helper/1.0",
            "Accept": "image/*,*/*;q=0.8",
            **({"Referer": referer} if referer else {}),
        },
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        ctype = resp.headers.get("Content-Type") or "application/octet-stream"
    return data, ctype


def _crop_image_to_png(image_bytes: bytes, crop: dict[str, Any]) -> bytes:
    """
    Crop using pixel coordinates saved in curation.yaml:
      ix, iy, iw, ih
    Optional: img_w, img_h
    Output: PNG bytes.
    """
    with Image.open(io.BytesIO(image_bytes)) as im:
        im = im.convert("RGBA")
        W, H = im.size

        ix = int(crop.get("ix", 0))
        iy = int(crop.get("iy", 0))
        iw = int(crop.get("iw", 0))
        ih = int(crop.get("ih", 0))

        if iw <= 0 or ih <= 0:
            raise ValueError("Invalid crop dimensions")

        left = max(0, min(ix, W - 1))
        top = max(0, min(iy, H - 1))
        right = max(left + 1, min(ix + iw, W))
        bottom = max(top + 1, min(iy + ih, H))

        cropped = im.crop((left, top, right, bottom))

        out = io.BytesIO()
        cropped.save(out, format="PNG", optimize=True)
        return out.getvalue()


def _pick_item_title(url: str, rec: dict[str, Any] | None) -> str:
    if isinstance(rec, dict):
        t = (rec.get("title") or "").strip()
        if t:
            return t
    return url


def _pick_item_blurb(rec: dict[str, Any] | None) -> tuple[str, str]:
    """
    Returns (blurb, source) where source is:
      final_blurb | excerpts | none
    """
    if isinstance(rec, dict):
        fb = (rec.get("final_blurb") or "").strip()
        if fb:
            return fb, "final_blurb"

        ex = rec.get("excerpts")
        if isinstance(ex, list):
            ex2 = [x.strip() for x in ex if isinstance(x, str) and x.strip()]
            if ex2:
                return " ".join(ex2), "excerpts"

    return "", "none"


def _pick_item_image(rec: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
    """
    Returns (img_url, crops_dict).
    Image selection rules:
      1) selected_image
      2) first crop key (sorted)
      3) none
    """
    img = ""
    crops: dict[str, Any] = {}

    if isinstance(rec, dict):
        img = (rec.get("selected_image") or "").strip()
        v = rec.get("image_crops")
        if isinstance(v, dict):
            crops = v

    if not img and crops:
        keys = sorted([k for k in crops if isinstance(k, str) and k.strip()])
        if keys:
            img = keys[0]

    return img, crops


# -----------------------------
# Public API
# -----------------------------
def build_constant_contact_zip() -> tuple[bytes, str]:
    sel = load_selected()
    cur = load_curation()

    subject = (
        sel.get("subject") or ""
    ).strip() or "Monthly Update — New from the Texas State Library"
    intro = (sel.get("intro") or "").strip() or (
        "Hello everyone—here are highlights and resources recently published by the Texas State Library "
        "and Archives Commission."
    )

    items = sel.get("items") or []
    if not isinstance(items, list):
        items = []

    now = datetime.now()
    stamp = now.strftime("%Y-%m-%d_%H%M")
    zip_name = f"tslac_constant_contact_export_{stamp}.zip"

    manifest: dict[str, Any] = {
        "generated_at": now.isoformat(timespec="seconds"),
        "subject": subject,
        "intro": intro,
        "items": [],
    }

    html_blocks: list[str] = []
    txt_blocks: list[str] = []
    image_files: list[tuple[str, bytes]] = []

    item_num = 0
    for it in items:
        if not isinstance(it, dict):
            continue

        url = (it.get("url") or "").strip()
        if not url:
            continue

        if not _is_http_url(url):
            # For now: skip non-article keys in the CC export (keeps scope tight)
            # You can add doc exports later.
            continue

        rec = None
        if isinstance(cur, dict):
            # Prefer canonical id key first (Milestone 2), then fall back to legacy url key.
            rec = cur.get(norm_key(f"web:{url}")) or cur.get(norm_url(url))

        title = _pick_item_title(url, rec)
        blurb, blurb_source = _pick_item_blurb(rec)
        img_url, crops = _pick_item_image(rec)

        item_num += 1
        hero_rel = ""
        img_entry: dict[str, Any] = {"present": False}

        if img_url:
            img_fetch = _normalize_url_for_fetch(img_url, base=url)

            crop = None
            if isinstance(crops, dict):
                crop = (
                    crops.get(img_url)
                    or crops.get(_norm_img_key(img_url))
                    or crops.get(img_fetch)
                    or crops.get(_norm_img_key(img_fetch))
                )

            try:
                raw, _ctype = _fetch_bytes(img_fetch, timeout=25)

                if isinstance(crop, dict) and all(k in crop for k in ("ix", "iy", "iw", "ih")):
                    out_png = _crop_image_to_png(raw, crop)
                    hero_rel = f"images/item{item_num:02d}_hero.png"
                    image_files.append((hero_rel, out_png))
                    img_entry = {
                        "present": True,
                        "source_url": img_fetch,
                        "crop_used": True,
                        "crop": crop,
                        "output_file": hero_rel,
                        "output_type": "image/png",
                    }
                else:
                    with Image.open(io.BytesIO(raw)) as im:
                        im = im.convert("RGBA")
                        out = io.BytesIO()
                        im.save(out, format="PNG", optimize=True)
                        out_png = out.getvalue()

                    hero_rel = f"images/item{item_num:02d}_hero.png"
                    image_files.append((hero_rel, out_png))
                    img_entry = {
                        "present": True,
                        "source_url": img_fetch,
                        "crop_used": False,
                        "crop": None,
                        "output_file": hero_rel,
                        "output_type": "image/png",
                    }

            except Exception as e:
                img_entry = {"present": False, "source_url": img_url, "error": str(e)}
                hero_rel = ""

        hero_html = ""
        if hero_rel:
            hero_html = (
                f'<img src="{_esc(hero_rel)}" alt="" '
                f'style="width:100%;height:auto;border:0;margin:0 0 10px 0;" />'
            )

        safe_blurb = _esc(blurb) if blurb else '<em style="color:#6b7280;">No blurb saved yet.</em>'

        html_blocks.append(f"""
<div style="border-top:1px solid #eee;padding-top:14px;margin-top:14px;">
  {hero_html}
  <div style="font-size:12px;color:#6b7280;margin-bottom:6px;">Texas State Library and Archives Commission</div>
  <div style="font-size:18px;font-weight:650;margin-bottom:6px;color:#111827;">{_esc(title)}</div>
  <div style="color:#374151;line-height:1.45;">{safe_blurb}</div>
  <div style="margin-top:10px;">
    <a href="{_safe_url(url)}" style="color:#0b57d0;text-decoration:none;">Read more</a>
  </div>
</div>
""".strip())

        txt_blocks.append(f"{item_num}) {title}\n{blurb}\n{url}\n")

        manifest["items"].append(
            {"url": url, "title": title, "blurb_source": blurb_source, "image": img_entry}
        )

    html_doc = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{_esc(subject)}</title>
</head>
<body style="margin:0;background:#f3f4f6;">
  <div style="max-width:720px;margin:0 auto;padding:18px;">
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:18px;">
      <div style="font-size:22px;font-weight:700;margin:0 0 10px 0;">{_esc(subject)}</div>
      <div style="color:#374151;margin:0 0 14px 0;line-height:1.4;">{_esc(intro)}</div>
      {''.join(html_blocks) if html_blocks else '<div style="color:#6b7280;">No selected items found in selected.yaml.</div>'}
      <div style="margin-top:14px;font-size:12px;color:#6b7280;">
        Import into Constant Contact using “New Email from .ZIP”.
      </div>
    </div>
  </div>
</body>
</html>
"""

    plain = f"SUBJECT: {subject}\n\n{intro}\n\n" + (
        "\n".join(txt_blocks) if txt_blocks else "(No items)\n"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("index.html", html_doc.encode("utf-8"))
        z.writestr("plain.txt", plain.encode("utf-8"))
        z.writestr(
            "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
        )
        for rel, data in image_files:
            z.writestr(rel, data)

    return buf.getvalue(), zip_name
