# export_cc.py
from __future__ import annotations

import html
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, urljoin, unquote, quote

import yaml

# Pillow is required for server-side crop rendering
from PIL import Image
import urllib.request


APP_DIR = Path(__file__).resolve().parent
SELECTED_FILE = APP_DIR / "selected.yaml"
CURATION_FILE = APP_DIR / "curation.yaml"


def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def _load_yaml(p: Path) -> dict[str, Any]:
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text("utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _is_http_url(u: str) -> bool:
    try:
        p = urlparse(u)
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

    # resolve relative if needed
    if base:
        try:
            u = urljoin(base, u)
        except Exception:
            pass

    u = unquote(u)  # normalize any % encodings for consistent quoting
    p = urlparse(u)

    if not (p.scheme in ("http", "https") and p.netloc):
        return u

    safe_path = quote(p.path, safe="/%")
    safe_query = quote(p.query, safe="=&?/%")
    return p._replace(path=safe_path, query=safe_query).geturl()


def _norm_img_key(u: str) -> str:
    """
    Key normalization so crop dict lookup is stable even if
    you stored encoded vs decoded variants.
    """
    return _normalize_url_for_fetch(u, base="")


def _fetch_bytes(url: str, timeout: int = 20) -> tuple[bytes, str]:
    """
    Fetch remote bytes with friendly headers.
    Returns (data, content_type).
    """
    url = (url or "").strip()
    if not _is_http_url(url):
        raise ValueError(f"Not an http(s) url: {url}")

    # Referer helps for some hotlink protection
    referer = ""
    try:
        pp = urlparse(url)
        referer = f"{pp.scheme}://{pp.netloc}/"
    except Exception:
        referer = ""

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

      ix, iy, iw, ih, img_w, img_h

    Crop is clamped to the actual loaded image dimensions.
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


def _pick_item_title(url: str, rec: Optional[dict[str, Any]]) -> str:
    # If you later store curated title, use it; otherwise fallback to URL
    if isinstance(rec, dict):
        t = (rec.get("title") or "").strip()
        if t:
            return t
    return url


def _pick_item_blurb(url: str, rec: Optional[dict[str, Any]]) -> tuple[str, str]:
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


def _pick_item_image(url: str, rec: Optional[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
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
        keys = sorted([k for k in crops.keys() if isinstance(k, str) and k.strip()])
        if keys:
            img = keys[0]

    return img, crops


def build_constant_contact_zip() -> tuple[bytes, str]:
    sel = _load_yaml(SELECTED_FILE)
    cur = _load_yaml(CURATION_FILE)

    subject = (sel.get("subject") or "").strip() or "Monthly Update — New from the Texas State Library"
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

    # Build HTML blocks + plain text blocks
    html_blocks: list[str] = []
    txt_blocks: list[str] = []

    # Collected image outputs: zip_path -> bytes
    image_files: list[tuple[str, bytes]] = []

    item_num = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        url = (it.get("url") or "").strip()
        if not url:
            continue

        rec = cur.get(url) if isinstance(cur, dict) else None

        title = _pick_item_title(url, rec)
        blurb, blurb_source = _pick_item_blurb(url, rec)
        img_url, crops = _pick_item_image(url, rec)

        item_num += 1
        hero_rel = ""  # relative path inside zip, like images/item01_hero.png

        img_entry: dict[str, Any] = {"present": False}

        # Build/emit image if we have one
        if img_url:
            # Normalize image URL (handles spaces etc.)
            img_fetch = _normalize_url_for_fetch(img_url, base=url)

            crop = None
            if isinstance(crops, dict):
                # Try multiple lookup keys defensively
                crop = (
                    crops.get(img_url)
                    or crops.get(_norm_img_key(img_url))
                    or crops.get(img_fetch)
                    or crops.get(_norm_img_key(img_fetch))
                )

            # Fetch source image
            try:
                raw, ctype = _fetch_bytes(img_fetch, timeout=25)

                # Crop if crop dict present
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
                    # No crop: still include as PNG (normalize formats for email import)
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
                # Do not fail the whole export—just omit the hero
                img_entry = {
                    "present": False,
                    "source_url": img_url,
                    "error": str(e),
                }
                hero_rel = ""

        # HTML
        hero_html = ""
        if hero_rel:
            hero_html = (
                f'<img src="{_esc(hero_rel)}" alt="" '
                f'style="width:100%;height:auto;border-radius:12px;border:1px solid #eee;margin:0 0 10px 0;" />'
            )

        safe_blurb = _esc(blurb) if blurb else '<em style="color:#6b7280;">No blurb saved yet. Use Curate to write one.</em>'

        html_blocks.append(f"""
          <div style="border-top:1px solid #eee;padding-top:14px;margin-top:14px;">
            {hero_html}
            <div style="font-size:12px;color:#6b7280;margin-bottom:6px;">Texas State Library and Archives Commission</div>
            <div style="font-size:18px;font-weight:650;margin-bottom:6px;color:#111827;">{_esc(title)}</div>
            <div style="color:#374151;line-height:1.45;">{safe_blurb}</div>
            <div style="margin-top:10px;">
              <a href="{_esc(url)}" style="color:#0b57d0;text-decoration:none;">Read more</a>
            </div>
          </div>
        """)

        # Plain text
        txt_blocks.append(
            f"{item_num}) {title}\n"
            f"{blurb}\n"
            f"{url}\n"
        )

        manifest["items"].append(
            {
                "url": url,
                "title": title,
                "blurb_source": blurb_source,
                "image": img_entry,
            }
        )

    # index.html (email HTML)
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
        Export generated by tslac-newsletter-helper. Import into Constant Contact using “New Email from .ZIP”.
      </div>
    </div>
  </div>
</body>
</html>
"""

    # plain.txt
    plain = f"SUBJECT: {subject}\n\n{intro}\n\n" + ("\n".join(txt_blocks) if txt_blocks else "(No items)\n")

    # Build ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("index.html", html_doc.encode("utf-8"))
        z.writestr("plain.txt", plain.encode("utf-8"))
        z.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"))

        # images
        for rel, data in image_files:
            z.writestr(rel, data)

    return buf.getvalue(), zip_name