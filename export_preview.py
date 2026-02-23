# export_preview.py
from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import yaml

APP_DIR = Path(__file__).resolve().parent
SELECTED_FILE = APP_DIR / "selected.yaml"
CURATION_FILE = APP_DIR / "curation.yaml"

DEFAULT_SUBJECT = "Monthly Update — New from the Texas State Library"
DEFAULT_INTRO = (
    "Hello everyone—here are highlights and resources recently published by the Texas State Library "
    "and Archives Commission."
)

def _load_yaml(p: Path) -> dict[str, Any]:
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text("utf-8")) or {}
    return data if isinstance(data, dict) else {}

def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)

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

        if isinstance(rec, dict):
            title = (rec.get("title") or "").strip()
            blurb = (rec.get("final_blurb") or "").strip()

            # optional: if you store selected image in curation.yaml later
            img = (rec.get("selected_image") or "").strip()

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

        img_html = f'<img class="hero" src="{_esc(img)}" alt="" />' if img else ""

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