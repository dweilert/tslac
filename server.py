from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

import cleaner

from collector import collect_candidates, load_candidates_file
from config import DEFAULT_SUBJECT, DEFAULT_INTRO
from state_store import (
    load_selected,
    save_selected,
    load_curation,
    get_curated_blurb,
    get_curated_excerpts,
    upsert_curated_blurb,
    add_curated_excerpt,
    pop_curated_excerpt,
    clear_curated_excerpts,
    upsert_curated_image_crop,
)
from templates import html_page, curate_page_html


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # ----------------------------
        # Refresh candidates
        # ----------------------------
        if self.path.startswith("/refresh"):
            try:
                collect_candidates()
                self.send_response(302)
                self.send_header("Location", "/?status=Refreshed+candidate+list")
                self.end_headers()
            except Exception as e:
                self.send_response(302)
                self.send_header("Location", f"/?status=Refresh+failed:+{str(e).replace(' ','+')}")
                self.end_headers()
            return

        # ----------------------------
        # API: clean
        # ----------------------------
        if self.path.startswith("/api/clean"):
            try:
                qs = ""
                if "?" in self.path:
                    _, qs = self.path.split("?", 1)
                qd = parse_qs(qs)
                url = (qd.get("url", [""])[0] or "").strip()
                if not url:
                    raise ValueError("Missing required query parameter: url")

                res = cleaner.clean_article(url)

                payload = {
                    "url": res.url,
                    "title": res.title,
                    "published_date": res.published_date,
                    "date_confidence": res.date_confidence,
                    "clean_html": res.clean_html,
                    "text_plain": res.text_plain,
                    "images": res.images,
                    "extraction_quality": res.extraction_quality,
                }

                body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                body = json.dumps({"error": str(e)}, indent=2).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return

        # ----------------------------
        # Curate: /curate/<index>
        # ----------------------------
        if self.path.startswith("/curate/"):
            try:
                path_only = self.path.split("?", 1)[0]
                idx_str = path_only[len("/curate/") :].strip("/")
                idx = int(idx_str)

                candidates = load_candidates_file()
                if not candidates:
                    raise ValueError("No candidates available. Go back and click Refresh candidates first.")
                if idx < 0 or idx >= len(candidates):
                    raise ValueError(f"Index out of range: {idx} (0..{len(candidates)-1})")

                status = ""
                if "?" in self.path:
                    _, qs = self.path.split("?", 1)
                    qd = parse_qs(qs)
                    status = (qd.get("status", [""])[0] or "")

                c = candidates[idx]
                res = cleaner.clean_article(c.url)
                cleaned = {
                    "title": res.title,
                    "published_date": res.published_date,
                    "date_confidence": res.date_confidence,
                    "clean_html": res.clean_html,
                    "text_plain": res.text_plain,
                    "images": res.images,
                    "extraction_quality": res.extraction_quality,
                }

                cur = load_curation()

                blurb = get_curated_blurb(cur, c.url)
                excerpts = get_curated_excerpts(cur, c.url)


                crops = {}  # key: src -> crop dict
                try:
                    from state_store import get_curated_image_crops
                    crops = get_curated_image_crops(cur, c.url)
                except Exception:
                    crops = {}


                body = curate_page_html(
                    idx,
                    len(candidates),
                    c,
                    cleaned,
                    final_blurb=blurb,
                    excerpts=excerpts,
                    status=status,
                )

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            except Exception:
                import traceback
                tb = traceback.format_exc()
                body = f"<pre>Curate error:\n{tb}</pre>".encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return

        # ----------------------------
        # Main page
        # ----------------------------
        qs = ""
        if "?" in self.path:
            _, qs = self.path.split("?", 1)

        status = ""
        if qs:
            qd = parse_qs(qs)
            status = (qd.get("status", [""])[0] or "")

        candidates = load_candidates_file()
        sel = load_selected()

        prechecked = set()
        if isinstance(sel, dict):
            for it in sel.get("items") or []:
                if isinstance(it, dict) and it.get("url"):
                    prechecked.add(it["url"])

        subject = sel.get("subject") if isinstance(sel, dict) and sel.get("subject") else DEFAULT_SUBJECT
        intro = sel.get("intro") if isinstance(sel, dict) and sel.get("intro") else DEFAULT_INTRO

        cur = load_curation()
        has_blurb_by_url = {c.url: bool(get_curated_blurb(cur, c.url)) for c in candidates}

        body = html_page(
            candidates=candidates,
            prechecked=prechecked,
            subject=subject,
            intro=intro,
            status=status,
            has_blurb_by_url=has_blurb_by_url,
        )

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        form = parse_qs(raw)

        # Save selection list
        if self.path == "/save":
            picked = form.get("picked", [])
            subject = (form.get("subject", [DEFAULT_SUBJECT])[0] or DEFAULT_SUBJECT)
            intro = (form.get("intro", [DEFAULT_INTRO])[0] or DEFAULT_INTRO)
            save_selected(subject, intro, picked)

            self.send_response(302)
            self.send_header("Location", f"/?status=Saved+{len(picked)}+item(s)+to+selected.yaml")
            self.end_headers()
            return

        # Save blurb
        if self.path == "/curate/save":
            idx_str = (form.get("index", ["0"])[0] or "0").strip()
            url = (form.get("url", [""])[0] or "").strip()
            final_blurb = (form.get("final_blurb", [""])[0] or "").strip()
            try:
                idx = int(idx_str)
            except Exception:
                idx = 0

            if url:
                upsert_curated_blurb(url, final_blurb)

            self.send_response(302)
            self.send_header("Location", f"/curate/{idx}?status=Saved+blurb")
            self.end_headers()
            return

        # Add excerpt
        if self.path == "/curate/add_excerpt":
            idx_str = (form.get("index", ["0"])[0] or "0").strip()
            url = (form.get("url", [""])[0] or "").strip()
            excerpt = (form.get("excerpt", [""])[0] or "").strip()
            try:
                idx = int(idx_str)
            except Exception:
                idx = 0

            if url and excerpt:
                add_curated_excerpt(url, excerpt)

            self.send_response(302)
            self.send_header("Location", f"/curate/{idx}?status=Added+excerpt")
            self.end_headers()
            return

        # Pop excerpt
        if self.path == "/curate/pop_excerpt":
            idx_str = (form.get("index", ["0"])[0] or "0").strip()
            url = (form.get("url", [""])[0] or "").strip()
            try:
                idx = int(idx_str)
            except Exception:
                idx = 0

            if url:
                pop_curated_excerpt(url)

            self.send_response(302)
            self.send_header("Location", f"/curate/{idx}?status=Removed+last+excerpt")
            self.end_headers()
            return

        # ----------------------------
        # Save image crop (curate)
        # ----------------------------
        if self.path == "/curate/save_crop":
            idx_str = (form.get("index", ["0"])[0] or "0").strip()
            url = (form.get("url", [""])[0] or "").strip()
            img_src = (form.get("img_src", [""])[0] or "").strip()
            crop_json = (form.get("crop", [""])[0] or "").strip()

            try:
                idx = int(idx_str)
            except Exception:
                idx = 0

            try:
                crop = json.loads(crop_json) if crop_json else {}
            except Exception:
                crop = {}

            if url and img_src and crop:
                upsert_curated_image_crop(url, img_src, crop)

            self.send_response(302)
            self.send_header("Location", f"/curate/{idx}?status=Saved+image+crop")
            self.end_headers()
            return

        # Clear excerpts
        if self.path == "/curate/clear_excerpts":
            idx_str = (form.get("index", ["0"])[0] or "0").strip()
            url = (form.get("url", [""])[0] or "").strip()
            try:
                idx = int(idx_str)
            except Exception:
                idx = 0

            if url:
                clear_curated_excerpts(url)

            self.send_response(302)
            self.send_header("Location", f"/curate/{idx}?status=Cleared+excerpts")
            self.end_headers()
            return

        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Not found")

    def log_message(self, fmt, *args):
        return