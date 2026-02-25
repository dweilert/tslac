from __future__ import annotations

import html
from pathlib import Path
from turtle import width
from typing import Any
from urllib.parse import quote, unquote

import yaml

APP_DIR = Path(__file__).resolve().parent
SELECTED_FILE = APP_DIR / "selected.yaml"
CURATION_FILE = APP_DIR / "curation.yaml"

DEFAULT_SUBJECT = "Monthly Update — New from the Texas State Library"
DEFAULT_INTRO = (
    "Hello everyone—here are highlights and resources recently published by the Texas State Library "
    "and Archives Commission."
)

def _norm_img_key(s: str) -> str:
    return (s or "").strip()

def _load_yaml(p: Path) -> dict[str, Any]:
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text("utf-8")) or {}
    return data if isinstance(data, dict) else {}

def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)

def _img_proxy(u: str) -> str:
    # Use your local proxy so hotlink/CORS policies don’t matter
    return "/img?u=" + quote(u or "", safe="")



def _crop_style(crop: dict[str, Any]) -> str:
    """
    Responsive crop for <img class="heroCropImg"> inside .heroCrop.

    Uses:
      width/height as % so it scales with container
      left/top as % of container (reliable)
    Crop format (image px):
      ix, iy, iw, ih, img_w, img_h
    """
    try:
        ix = float(crop["ix"])
        iy = float(crop["iy"])
        cw = float(crop["iw"])
        ch = float(crop["ih"])
        img_w = float(crop["img_w"])
        img_h = float(crop["img_h"])

        if cw <= 0 or ch <= 0 or img_w <= 0 or img_h <= 0:
            return ""

        # scale image so crop fills container
        w_pct = (img_w / cw) * 100.0
        h_pct = (img_h / ch) * 100.0

        # shift image so crop origin aligns with container origin
        left_pct = -(ix / cw) * 100.0
        top_pct  = -(iy / ch) * 100.0

        return (
            f"width:{w_pct:.3f}%;"
            f"height:{h_pct:.3f}%;"
            f"left:{left_pct:.3f}%;"
            f"top:{top_pct:.3f}%;"
        )
    except Exception:
        return ""



def build_preview_html() -> bytes:
    sel = _load_yaml(SELECTED_FILE)
    cur = _load_yaml(CURATION_FILE)

    subject = (sel.get("subject") or "").strip() or DEFAULT_SUBJECT
    intro = (sel.get("intro") or "").strip() or DEFAULT_INTRO
    items = sel.get("items") or []
    if not isinstance(items, list):
        items = []

    # Build sections
    blocks = []
    for it in items:
        if not isinstance(it, dict):
            continue
        url = (it.get("url") or "").strip()
        if not url:
            continue

        rec = cur.get(url) if isinstance(cur, dict) else None
        title = ""
        blurb = ""

        img = ""
        crops = {}

        if isinstance(rec, dict):
            title = (rec.get("title") or "").strip()
            blurb = (rec.get("final_blurb") or "").strip()

            img = (rec.get("selected_image") or "").strip()

            crops = rec.get("image_crops") if isinstance(rec.get("image_crops"), dict) else {}

        # If no selected_image, but we have crops saved, use the first cropped image as the image
        if not img and isinstance(crops, dict) and crops:
            # choose the first key deterministically
            img = sorted([k for k in crops.keys() if isinstance(k, str) and k.strip()])[0]


        # fallbacks if title not stored
        if not title:
            title = url

        # if no blurb, show excerpts as fallback
        if not blurb and isinstance(rec, dict):
            ex = rec.get("excerpts")
            if isinstance(ex, list):
                ex2 = [x.strip() for x in ex if isinstance(x, str) and x.strip()]
                if ex2:
                    blurb = " ".join(ex2)


        # --- Pick crop record for the chosen image (IMPORTANT) ---
        crop = None
        if isinstance(crops, dict) and img:
            crop = crops.get(img) or crops.get(_norm_img_key(img)) or crops.get(unquote(img))    


        img_html = ""
        if img:
            # Use proxy so image always loads locally
            # img_src = "/img?u=" + quote(img, safe=":/%?=&")
            img_src = "/img?u=" + quote(img, safe=":/%?=&")
            if isinstance(crop, dict) and all(k in crop for k in ("ix", "iy", "iw", "ih", "img_w", "img_h")):
                style = _crop_style(crop)

                # Aspect ratio box based on crop
                try:
                    pad = (float(crop["ih"]) / float(crop["iw"])) * 100.0
                    if pad <= 0 or pad > 300:
                        pad = 56.25
                except Exception:
                    pad = 56.25

                # compute style as before
                style = _crop_style(crop)

                img_html = (
                    f'<div class="heroCrop" style="padding-top:{pad:.3f}%;">'
                    f'  <img class="heroCropImg" src="{_esc(img_src)}" alt="" style="{style}" />'
                    f'</div>'
                )
            else:
                # no crop saved for this image, show full image
                img_html = f'<img class="hero" src="{_esc(img_src)}" alt="" />'


        blocks.append(f"""
          <div class="item">
            {img_html}
            <div class="kicker">Texas State Library and Archives Commission</div>
            <div class="title">{_esc(title)}</div>
            <div class="body">{_esc(blurb) if blurb else '<em class="muted">No blurb saved yet. Use Curate to write one.</em>'}</div>
            <div class="link"><a href="{_esc(url)}" target="_blank" rel="noopener">Read more</a></div>
          </div>
        """)

    if not blocks:
        blocks_html = "<p class='muted'>No selected items found in selected.yaml.</p>"
    else:
        blocks_html = "\n".join(blocks)

    html_doc = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{_esc(subject)}</title>
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif; margin: 0; background:#f3f4f6; }}
    .wrap {{ max-width: 720px; margin: 0 auto; padding: 18px; }}
    .card {{ background:#fff; border:1px solid #e5e7eb; border-radius: 14px; padding: 18px; }}
    h1 {{ margin: 0 0 10px; font-size: 22px; }}
    .intro {{ color:#374151; margin: 0 0 14px; line-height: 1.4; }}
    .item {{ border-top: 1px solid #eee; padding-top: 14px; margin-top: 14px; }}
    .item:first-of-type {{ border-top: none; padding-top: 0; margin-top: 0; }}
    .kicker {{ font-size: 12px; color:#6b7280; margin-bottom: 6px; }}
    .title {{ font-size: 18px; font-weight: 650; margin-bottom: 6px; color:#111827; }}
    .body {{ color:#374151; line-height: 1.45; }}
    .muted {{ color:#6b7280; }}
    .link a {{ display:inline-block; margin-top: 10px; color:#0b57d0; text-decoration:none; }}
    .link a:hover {{ text-decoration:underline; }}
    .hero {{ width: 100%; height: auto; border-radius: 12px; border: 1px solid #eee; margin-bottom: 10px; }}
    .note {{ margin-top: 14px; font-size: 12px; color:#6b7280; }}


.heroCrop{{
  position: relative;
  width: 100%;
  border-radius: 12px;
  border: 1px solid #eee;
  margin-bottom: 10px;
  overflow: hidden;
  background: #f3f4f6;
}}

.heroCropImg{{
  position: absolute;
  left: 0;
  top: 0;
  transform-origin: top left;
  display: block;
}}

.heroCrop{{
  outline: 2px solid red;
}}
.heroCropImg{{
  outline: 2px solid blue;
}}


.heroCrop {{ position: relative; overflow: hidden; }}
.heroCropImg {{ position: absolute; display: block; }}

</style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>{_esc(subject)}</h1>
      <p class="intro">{_esc(intro)}</p>
      {blocks_html}
      <div class="note">
        Preview only. Next step: add “Copy block” buttons and Constant Contact-ready HTML snippets.
      </div>
    </div>
  </div>
</body>
</html>
"""
    return html_doc.encode("utf-8")
