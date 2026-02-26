from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse, unquote, urljoin, quote

import cleaner
import export_preview
import watcher
import watch_store
import templates
import os
import export_cc

from pathlib import Path
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
    get_curated_selected_image, 
    upsert_curated_selected_image, 
    clear_curated_selected_image
)

from templates import html_page, curate_page_html
from doc_archive import archive_docs

from collector import (
    collect_candidates, 
    load_candidates_file, 
    load_doc_candidates_file, 
    load_doc_candidates_file  
)

doc_candidates = load_doc_candidates_file()
from logutil import info

def _is_http_url(u: str) -> bool:
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False



class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # ----------------------------
        # Refresh candidates
        # ----------------------------
        if self.path.startswith("/refresh"):
            try:
                collect_candidates()
                doc_cnt = len(load_doc_candidates_file())
                self.send_response(302)
                self.send_header("Location", f"/?status=Refreshed+candidate+list+(docs:{doc_cnt})")
                self.end_headers()
            except Exception as e:
                self.send_response(302)
                self.send_header("Location", f"/?status=Refresh+failed:+{str(e).replace(' ','+')}")
                self.end_headers()
            return


        # ----------------------------
        # Watch: /watch
        # ----------------------------

        if self.path.startswith("/watch/status"):
            st = watcher.get_watch_status()
            body = json.dumps(st, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path.startswith("/watch/scan"):
            try:
                started = watcher.start_watch_scan_async()
                self.send_response(302)
                self.send_header("Location", "/watch?status=" + ("Scan+started" if started else "Scan+already+running"))
                self.end_headers()
                return
            except Exception as e:
                msg = str(e).replace(" ", "+")
                self.send_response(302)
                self.send_header("Location", f"/watch?status=Scan+failed:+{msg}")
                self.end_headers()
            return
        
        if self.path.startswith("/watch/cancel"):
            watcher.cancel_watch_scan()
            self.send_response(302)
            self.send_header("Location", "/watch?status=Cancel+requested")
            self.end_headers()
            return

        if self.path.startswith("/watch"):
            try:
                qs = ""
                if "?" in self.path:
                    _, qs = self.path.split("?", 1)
                status = ""
                if qs:
                    qd = parse_qs(qs)
                    status = (qd.get("status", [""])[0] or "")

                cfg = watch_store.load_watch()
                latest = watcher.load_latest_results()

                sites_text = "\n".join(cfg.sites or [])
                topics_text = "\n".join(cfg.topics or [])

                body = templates.watch_page_html(
                    sites_text=sites_text,
                    topics_text=topics_text,
                    status=status,
                    latest=latest,
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                import traceback
                tb = traceback.format_exc()
                body = f"<pre>Watch error:\n{tb}</pre>".encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return


        # ----------------------------
        # Preview page: /preview
        # ----------------------------
        if self.path.startswith("/preview"):
            try:
                # IMPORTANT: return HTML directly, do NOT redirect to /preview
                html_bytes = export_preview.build_preview_html()  # <-- whatever your function is named
                if isinstance(html_bytes, str):
                    html_bytes = html_bytes.encode("utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html_bytes)))
                self.end_headers()
                self.wfile.write(html_bytes)
            except Exception as e:
                # On error, redirect BACK TO LIST PAGE (not /preview)
                msg = str(e).replace(" ", "+")
                self.send_response(302)
                self.send_header("Location", f"/?status=Preview+failed:+{msg}")
                self.end_headers()
            return



        if self.path.startswith("/preview/file"):
            try:
                p = (Path(__file__).resolve().parent / "output" / "preview" / "index.html")
                html = p.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
            except Exception as e:
                body = f"<pre>Preview file error: {e}</pre>".encode("utf-8")
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return

        if self.path.startswith("/preview/images/"):
            # serve cached images
            try:
                rel = self.path[len("/preview/"):]  # 'images/xxx.jpg'
                img_path = (Path(__file__).resolve().parent / "output" / "preview" / rel).resolve()
                base = (Path(__file__).resolve().parent / "output" / "preview").resolve()
                if not str(img_path).startswith(str(base)):
                    raise ValueError("Invalid image path")
                data = img_path.read_bytes()

                # naive content-type
                ct = "image/jpeg"
                if img_path.suffix.lower() == ".png":
                    ct = "image/png"
                elif img_path.suffix.lower() == ".webp":
                    ct = "image/webp"

                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                body = f"Not found: {e}".encode("utf-8")
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
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
                selected_image = get_curated_selected_image(cur, c.url)

                crops = {}  # key: src -> crop dict

                # Add this to the JSON object
                cleaned["image_crops"] = crops

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
                    selected_image=selected_image,
                    status=status,
                    crops=crops,
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
        # Image proxy: /img?u=<url>
        # ----------------------------
        if self.path.startswith("/img"):
            try:
                qs = ""
                if "?" in self.path:
                    _, qs = self.path.split("?", 1)
                qd = parse_qs(qs)

                # read params
                u = (qd.get("u", [""])[0] or "").strip()
                base = (qd.get("base", [""])[0] or "").strip()

                # allow either raw or urlencoded
                u = unquote(u)
                base = unquote(base)

                # --- NEW: resolve relative URL against base ---
                # If u is "/sites/..." and base is "https://www.tsl.texas.gov/some/page",
                # urljoin will produce "https://www.tsl.texas.gov/sites/..."
                if base:
                    try:
                        u = urljoin(base, u)
                    except Exception:
                        pass

                # --- NEW: percent-encode unsafe characters (spaces etc.) ---
                # urllib will reject URLs containing raw spaces/control chars
                p = urlparse(u)
                if p.scheme in ("http", "https") and p.netloc:
                    safe_path = quote(p.path, safe="/%")
                    safe_query = quote(p.query, safe="=&?/%")
                    u = p._replace(path=safe_path, query=safe_query).geturl()

                # validate final URL
                if not _is_http_url(u):
                    body = f"Bad image url: {u}".encode("utf-8")
                    self.send_response(400)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                import urllib.request

                # --- NEW: send Referer (helps with some hotlink protection) ---
                referer = ""
                try:
                    pp = urlparse(u)
                    referer = f"{pp.scheme}://{pp.netloc}/"
                except Exception:
                    referer = ""

                req = urllib.request.Request(
                    u,
                    headers={
                        "User-Agent": "tslac-newsletter-helper/1.0",
                        "Accept": "image/*,*/*;q=0.8",
                        **({"Referer": referer} if referer else {}),
                    },
                )

                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                    ctype = resp.headers.get("Content-Type") or "application/octet-stream"

                # --- OPTIONAL: if upstream isn't an image, return error (helps debugging) ---
                if not (ctype or "").lower().startswith("image/"):
                    snippet = data[:300].decode("utf-8", errors="replace")
                    body = (
                        f"Upstream did not return an image.\n"
                        f"Content-Type: {ctype}\n"
                        f"URL: {u}\n"
                        f"---\n{snippet}"
                    ).encode("utf-8")
                    self.send_response(502)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()
                self.wfile.write(data)
                return

            except Exception as e:
                body = f"Image proxy error: {e}".encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return


        # ----------------------------
        # Constant Contact Export: /export/cc
        # ----------------------------
        if self.path.startswith("/export/cc"):
            try:
                data, fname = export_cc.build_constant_contact_zip()

                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                msg = str(e).replace(" ", "+")
                self.send_response(302)
                self.send_header("Location", f"/?status=Export+failed:+{msg}")
                self.end_headers()
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

        doc_candidates = load_doc_candidates_file()
        has_blurb_by_docid = {
            d["id"]: bool(get_curated_blurb(cur, d["id"]))
            for d in (doc_candidates or [])
            if isinstance(d, dict) and d.get("id")
        }

        debug(f"UI: web candidates={len(candidates)} doc candidates={len(doc_candidates)}")


        body = html_page(
            candidates=candidates,
            doc_candidates=doc_candidates,
            prechecked=prechecked,
            subject=subject,
            intro=intro,
            status=status,
            has_blurb_by_url=has_blurb_by_url,
            has_blurb_by_docid=has_blurb_by_docid,
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

        # Save watch config
        if self.path == "/watch/save":
            sites_text = (form.get("sites", [""])[0] or "")
            topics_text = (form.get("topics", [""])[0] or "")
            try:
                watch_store.save_watch_from_lines(sites_text, topics_text)
                self.send_response(302)
                self.send_header("Location", "/watch?status=Saved+watch.yaml")
                self.end_headers()
            except Exception as e:
                msg = str(e).replace(" ", "+")
                self.send_response(302)
                self.send_header("Location", f"/watch?status=Save+failed:+{msg}")
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


        # ----------------------------
        # Select image for newsletter
        # ----------------------------
        if self.path == "/curate/select_image":
            idx_str = (form.get("index", ["0"])[0] or "0").strip()
            url = (form.get("url", [""])[0] or "").strip()
            img_src = (form.get("img_src", [""])[0] or "").strip()

            try:
                idx = int(idx_str)
            except Exception:
                idx = 0

            # Basic safety: only allow http(s)
            if img_src and not (img_src.startswith("http://") or img_src.startswith("https://")):
                img_src = ""

            if url and img_src:
                upsert_curated_selected_image(url, img_src)

            self.send_response(302)
            self.send_header("Location", f"/curate/{idx}?status=Selected+image")
            self.end_headers()
            return


        # ----------------------------
        # Archive documents (Drive or Local)
        # ----------------------------
        if self.path == "/archive_docs":
            try:
                moved = archive_docs()
                self.send_response(302)
                self.send_header("Location", f"/?status=Archived+{moved}+document(s)")
                self.end_headers()
            except Exception as e:
                msg = str(e).replace(" ", "+")
                self.send_response(302)
                self.send_header("Location", f"/?status=Archive+failed:+{msg}")
                self.end_headers()
            return


        # ----------------------------
        # Clear selected image
        # ----------------------------
        if self.path == "/curate/clear_selected_image":
            idx_str = (form.get("index", ["0"])[0] or "0").strip()
            url = (form.get("url", [""])[0] or "").strip()

            try:
                idx = int(idx_str)
            except Exception:
                idx = 0

            if url:
                clear_curated_selected_image(url)

            self.send_response(302)
            self.send_header("Location", f"/curate/{idx}?status=Cleared+selected+image")
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
    
