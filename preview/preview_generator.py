from __future__ import annotations

import html
from typing import Any
from urllib.parse import quote, unquote

from storage.collector_store import load_candidates_file
from storage.curation_store import get_curated_blurb, load_curation
from storage.selected_store import load_selected

DEFAULT_SUBJECT = "Monthly Update — New from the Texas State Library"
DEFAULT_INTRO = (
    "Hello everyone—here are highlights and resources recently published by the Texas State Library "
    "and Archives Commission."
)


def _norm_img_key(s: str) -> str:
    return (s or "").strip()


def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)


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

        w_pct = (img_w / cw) * 100.0
        h_pct = (img_h / ch) * 100.0
        left_pct = -(ix / cw) * 100.0
        top_pct = -(iy / ch) * 100.0

        return (
            f"width:{w_pct:.3f}%;"
            f"height:{h_pct:.3f}%;"
            f"left:{left_pct:.3f}%;"
            f"top:{top_pct:.3f}%;"
        )
    except Exception:
        return ""


def _is_doc_id(u: str) -> bool:
    return (u or "").startswith(("gdrive:", "local:"))


def _is_http_url(u: str) -> bool:
    return (u or "").startswith(("http://", "https://"))


def _normalize_selected_key(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""

    # Repair accidental double-wraps like web:web:https://...
    while s.startswith("web:web:"):
        s = "web:" + s[len("web:web:") :]

    # Repair accidental web:gdrive:... / web:local:...
    if s.startswith("web:gdrive:"):
        s = s[len("web:") :]
    if s.startswith("web:local:"):
        s = s[len("web:") :]

    return s


def _web_url_from_key(s: str) -> str:
    s = _normalize_selected_key(s)
    if s.startswith("web:"):
        return s[len("web:") :].strip()
    return s if _is_http_url(s) else ""


def _gdrive_open_url(key: str) -> str:
    s = (key or "").strip()
    if not s.startswith("gdrive:"):
        return "#"
    file_id = s[len("gdrive:") :].strip()
    if not file_id:
        return "#"
    return f"https://drive.google.com/open?id={file_id}"


def _local_open_url(key: str) -> str:
    # Browser generally cannot open arbitrary local filesystem paths directly.
    # Keep placeholder until/if a local-serving route is added.
    _ = key
    return "#"


def _candidate_attr(c: Any, name: str, default: str = "") -> str:
    try:
        v = getattr(c, name, default)
    except Exception:
        v = default
    return "" if v is None else str(v)


def build_preview_html() -> bytes:
    sel = load_selected()
    cur = load_curation()

    # Unified candidate lookup from persisted candidates.json
    candidates = load_candidates_file() or []
    cand_by_id: dict[str, Any] = {}

    for c in candidates:
        cid = _candidate_attr(c, "url").strip()
        if not cid:
            continue
        cand_by_id[cid] = c

    # subject = (sel.get("subject") or "").strip() or DEFAULT_SUBJECT

    items = sel.get("items") or []
    if not isinstance(items, list):
        items = []

    blocks: list[str] = []

    for it in items:
        if not isinstance(it, dict):
            continue

        raw_key = (it.get("url") or it.get("id") or "").strip()
        key = _normalize_selected_key(raw_key)
        if not key:
            continue

        rec = cur.get(key) if isinstance(cur, dict) else None
        c = cand_by_id.get(key)

        # ----------------------------
        # DOCUMENT ITEM (gdrive:/local:)
        # ----------------------------
        if _is_doc_id(key):
            title = ""
            subtitle = ""
            blurb_html = ""
            summary_fallback = ""

            if c is not None:
                title = _candidate_attr(c, "title").strip()
                summary_fallback = _candidate_attr(c, "summary").strip()

            if isinstance(rec, dict):
                title = (rec.get("title") or "").strip() or title
                subtitle = (rec.get("subtitle") or rec.get("curated_subtitle") or "").strip()
                blurb_html = get_curated_blurb(cur, key).strip()

            if not title:
                title = key

            if not blurb_html and summary_fallback:
                blurb_html = f"<p>{_esc(summary_fallback)}</p>"

            img_html = ""

            if key.startswith("gdrive:"):
                doc_href = _gdrive_open_url(key)
            elif key.startswith("local:"):
                doc_href = _local_open_url(key)
            else:
                doc_href = "#"

            subtitle_html = (
                f'<div style="font-size:13px; color:#555; margin: 0 0 6px 0;">{_esc(subtitle)}</div>'
                if subtitle
                else ""
            )

            blocks.append(f"""
              <tr>
                <td style="padding: 0 18px 18px 18px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;">
                  {img_html}
                  <div style="font-size:16px; font-weight:700; color:#111; margin: 0 0 6px 0;">{_esc(title)}</div>
                  {subtitle_html}
                  <div style="font-size:14px; color:#333; line-height:1.45;">
                    {(blurb_html if blurb_html else "<em style='color:#777;'>No blurb saved yet. Use Curate to write one.</em>")}
                  </div>
                  <div style="margin-top:10px; font-size:14px;">
                    <a href="{_esc(doc_href)}" target="_blank" rel="noopener" style="color:#0b57d0; text-decoration:none;">Open document</a>
                  </div>
                </td>
              </tr>
              <tr><td><hr style="border:0; border-bottom:1px solid #666; margin:10px 18px 10px 18px;"></td></tr>
            """)
            continue

        # ----------------------------
        # ARTICLE ITEM (web:/http/https)
        # ----------------------------
        url = _web_url_from_key(key)
        if not url:
            continue

        title = ""
        subtitle = ""
        blurb_html = ""
        img = ""
        crops: dict[str, Any] = {}

        if c is not None:
            title = _candidate_attr(c, "title").strip()

        if isinstance(rec, dict):
            title = (rec.get("title") or rec.get("curated_title") or "").strip() or title
            subtitle = (rec.get("subtitle") or rec.get("curated_subtitle") or "").strip()
            blurb_html = (rec.get("final_blurb") or "").strip()
            img = (rec.get("selected_image") or "").strip()
            crops = rec.get("image_crops") if isinstance(rec.get("image_crops"), dict) else {}

        if not img and isinstance(crops, dict) and crops:
            img = sorted([k for k in crops if isinstance(k, str) and k.strip()])[0]

        if not title:
            title = url

        if not blurb_html and isinstance(rec, dict):
            ex = rec.get("excerpts")
            if isinstance(ex, list):
                ex2 = [x.strip() for x in ex if isinstance(x, str) and x.strip()]
                if ex2:
                    blurb_html = f"<p>{_esc(' '.join(ex2))}</p>"

        if not blurb_html and c is not None:
            summary_fallback = _candidate_attr(c, "summary").strip()
            if summary_fallback:
                blurb_html = f"<p>{_esc(summary_fallback)}</p>"

        crop = None
        if isinstance(crops, dict) and img:
            crop = crops.get(img) or crops.get(_norm_img_key(img)) or crops.get(unquote(img))

        img_html = ""
        if img:
            img_src = "/img?u=" + quote(img, safe=":/%?=&")
            if isinstance(crop, dict) and all(
                k in crop for k in ("ix", "iy", "iw", "ih", "img_w", "img_h")
            ):
                try:
                    pad = (float(crop["ih"]) / float(crop["iw"])) * 100.0
                    if pad <= 0 or pad > 300:
                        pad = 56.25
                except Exception:
                    pad = 56.25

                style = _crop_style(crop)
                img_html = (
                    f'<div class="heroCrop" style="padding-top:{pad:.3f}%;">'
                    f'  <img class="heroCropImg" src="{_esc(img_src)}" alt="" style="{style}" />'
                    f"</div>"
                )
            else:
                img_html = f'<img class="hero" src="{_esc(img_src)}" alt="" />'

        subtitle_html = subtitle

        blocks.append(f"""
          <tr>
            <td style="padding: 0 18px 18px 18px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;">
              {img_html}

              <p style="text-align: center; margin: 0;" align="center">
                <span style="font-size: 36px; color: rgb(40, 79, 161);
                font-weight: bold;
                font-family: Georgia, &quot;Times New Roman&quot;, Times, serif;">
                {_esc(title)}
                </span>
              </p>
              <p style="text-align: center; margin: 0;" align="center">
                <span style="font-size: 23px; color: rgb(40, 79, 161);
                font-weight: bold;
                font-family: Georgia, &quot;Times New Roman&quot;, Times, serif; font-style: italic; text-decoration: underline;">
                {subtitle_html}
                </span>
              </p>
              <p style="margin 0;">
                <span style="font-size: 16px; color: rgb(0, 0, 0);
                font-family: Georgia, &quot;Times New Roman&quot;, Times, serif;">
                {(blurb_html if blurb_html else "<em style='color:#777;'>No blurb saved yet. Use Curate to write one.</em>")}
                &nbsp;</span>
              </p>


              <div style="margin-top:10px; font-size:14px;">
                <a href="{_esc(url)}" target="_blank" rel="noopener" style="color:#0b57d0; text-decoration:none;">Read more</a>
              </div>
            </td>
          </tr>
          <tr><td><hr style="border:0; border-bottom:1px solid #666; margin:10px 18px 10px 18px;"></td></tr>
        """)

    if not blocks:
        blocks_html = "<p class='muted'>No selected items found.</p>"
    else:
        blocks_html = "\n".join(blocks)

    PREHEADER_TEXT = "Donate to Texas Library and Archives Foundation today!"
    HEADER_LOGO_URL = (
        "https://files.constantcontact.com/d9aacb82801/f364e9d2-e7dd-4a1b-bee9-59bc4186acc6.png"
    )
    HEADER_BANNER_URL = (
        "https://files.constantcontact.com/d9aacb82801/08d6a7b0-f1ab-4e9e-807e-6662fcad75ba.png"
    )

    html_doc = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Preview</title>

  <style>
    img {{ display:block; height:auto; max-width:100%; border:0; outline:none; text-decoration:none; }}
    table {{ border-collapse:collapse; }}
    .shell_width-row {{ width: 622px; }}
    @media only screen and (max-width: 660px) {{
      .shell_width-row {{ width: 100% !important; }}
      .scale {{ width: 100% !important; }}
      .stack {{ display:block !important; width:100% !important; }}
      .pad10 {{ padding-left:10px !important; padding-right:10px !important; }}
    }}

    .hero {{ width:100%; height:auto; margin: 0 0 10px 0; }}
    .heroCrop {{ position: relative; width:100%; overflow:hidden; margin: 0 0 10px 0; }}
    .heroCropImg {{ position:absolute; left:0; top:0; }}

    .heroCropImg {{
      max-width: none !important;
      max-height: none !important;
    }}
  </style>
</head>

<body class="body template template--en-US"
  data-template-version="1.41.0"
  data-canonical-name="CPE-PT1001"
  lang="en-US"
  align="center"
  style="-ms-text-size-adjust:100%; -webkit-text-size-adjust:100%; min-width:100%; width:100%; margin:0; padding:0;">

  <div id="preheader"
    style="color:transparent; display:none; font-size:1px; line-height:1px; max-height:0; max-width:0; opacity:0; overflow:hidden;">
    <span data-entity-ref="preheader">{_esc(PREHEADER_TEXT)}</span>
  </div>

  <div id="tracking-image"
    style="color:transparent; display:none; font-size:1px; line-height:1px; max-height:0; max-width:0; opacity:0; overflow:hidden;">
  </div>

  <div class="shell" lang="en-US" style="background-color:#e6e6e6;">
    <table class="shell_panel-row" width="100%" border="0" cellpadding="0" cellspacing="0"
      style="background-color:#e6e6e6;" bgcolor="#e6e6e6">
      <tbody>
        <tr>
          <td class="shell_panel-cell" align="center" valign="top">
            <table class="shell_width-row scale" style="width:622px;" align="center" border="0" cellpadding="0" cellspacing="0">
              <tbody>
                <tr>
                  <td class="shell_width-cell pad10" style="padding:15px 10px;" align="center" valign="top">

                    <table class="shell_content-row" width="100%" align="center" border="0" cellpadding="0" cellspacing="0">
                      <tbody>
                        <tr>
                          <td class="shell_content-cell"
                            style="border-radius:0; background-color:#ffffff; padding:0; border:1px solid #869198;"
                            align="center" valign="top" bgcolor="#ffffff">

                            <table width="100%" border="0" cellpadding="0" cellspacing="0">
                              <tbody>
                                <tr>
                                  <td align="center" valign="top" style="padding-top:10px; padding-bottom:10px;">
                                    <div style="position:relative; display:inline-block; max-width:100%;">
                                      <img width="447"
                                          src="{_esc(HEADER_LOGO_URL)}"
                                          alt=""
                                          style="display:block; height:auto; max-width:100%;" />

                                      <div style="
                                          position:absolute;
                                          top:50%;
                                          left:50%;
                                          transform:translate(-50%, -50%);
                                          font-family:Arial, sans-serif;
                                          font-weight:900;
                                          font-size:96px;
                                          color: rgba(255,0,0, 0.5);
                                          letter-spacing:3px;
                                          opacity:0.85;
                                          pointer-events:none;
                                      ">
                                        DRAFT
                                      </div>
                                    </div>
                                  </td>
                                </tr>
                              </tbody>
                            </table>

                            <table class="image image--mobile-scale image--mobile-center" width="100%" border="0" cellpadding="0" cellspacing="0">
                              <tbody>
                                <tr>
                                  <td class="image_container" align="center" valign="top">
                                    <img class="image_content" width="600" src="{_esc(HEADER_BANNER_URL)}" alt=""
                                      style="display:block; height:auto; max-width:100%;" />
                                  </td>
                                </tr>
                              </tbody>
                            </table>

                            <table width="100%" border="0" cellpadding="0" cellspacing="0">
                              <tbody><tr><td style="line-height:22px; height:22px;">&nbsp;</td></tr></tbody>
                            </table>

                            <table class="layout layout--1-column" style="table-layout:fixed;" width="100%" border="0" cellpadding="0" cellspacing="0">
                              <tbody>
                                <tr>
                                  <td class="column column--1 scale stack" style="width:100%;" align="center" valign="top">

                                    <table width="100%" border="0" cellpadding="0" cellspacing="0">
                                      <tbody>
                                        {blocks_html if blocks_html else "<tr><td style='padding: 0 18px 18px 18px; color:#666; font-family:Arial,sans-serif;'>No selected items found.</td></tr>"}
                                      </tbody>
                                    </table>

                                    <table width="100%" border="0" cellpadding="0" cellspacing="0">
                                      <tbody>
                                        <tr>
                                          <td style="padding: 12px 18px 18px 18px; font-family:Arial,sans-serif; font-size:12px; 
                                          color:#fff; background-color: #000; text-align: center;">
                                            This is a DRAFT Preview only (styled close to Constant Contact).
                                          </td>
                                        </tr>
                                      </tbody>
                                    </table>

                                  </td>
                                </tr>
                              </tbody>
                            </table>

                          </td>
                        </tr>
                      </tbody>
                    </table>

                  </td>
                </tr>
              </tbody>
            </table>

          </td>
        </tr>
      </tbody>
    </table>
  </div>
</body>
</html>
"""
    return html_doc.encode("utf-8")
