from __future__ import annotations

from urllib.parse import quote, unquote

from render import render
from storage.curation_store import get_curated_image_crops, load_curation
from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router) -> None:
    router.get("/crop", get_crop)


def get_crop(req: Request) -> Response:
    q = req.query_first
    img = (q.get("img") or "").strip()
    page = (q.get("page") or "").strip()
    index = (q.get("index") or "0").strip()

    try:
        img = unquote(img)
        page = unquote(page)
    except Exception:
        pass

    # Build same-origin proxy URL for display to avoid CORS/hotlink issues.
    img_proxy = ""
    if img:
        img_proxy = "/img?u={}&base={}".format(quote(img, safe=""), quote(page, safe=""))

    # Load any saved crop for (page_url, img_src)
    saved_crop: dict = {}
    try:
        cur = load_curation()
        crops = get_curated_image_crops(cur, page)  # dict keyed by img src
        v = crops.get(img)
        if isinstance(v, dict):
            saved_crop = v
    except Exception:
        saved_crop = {}

    html_text = render(
        "crop.html",
        title="Crop image",
        img_url=img,           # original image URL (used when saving crop)
        img_proxy=img_proxy,   # proxied image URL (used for loading/display)
        page_url=page,
        index=index,
        saved_crop=saved_crop, # dict with ix,iy,iw,ih,img_w,img_h (if present)
    )
    return Response.html(html_text)