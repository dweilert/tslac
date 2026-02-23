from __future__ import annotations

from string import Template
from typing import Any

from config import CANDIDATES_FILE, SELECTED_FILE, CURATION_FILE
from models import Candidate


def _esc(s: str) -> str:
    s = s or ""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


def html_page(
    candidates: list[Candidate],
    prechecked: set[str],
    subject: str,
    intro: str,
    status: str,
    has_blurb_by_url: dict[str, bool],
) -> bytes:
    cards = []
    for i, c in enumerate(candidates):
        chk = "checked" if c.url in prechecked else ""
        blurb_badge = '<span class="badge">blurb</span>' if has_blurb_by_url.get(c.url) else ""

        cards.append(f"""
        <div class="card" data-title="{_esc(c.title.lower())}" data-source="{_esc(c.source.lower())}">
          <div class="row">
            <input type="checkbox" name="picked" value="{_esc(c.url)}" onchange="updateCount()" {chk}/>
            <div style="flex:1;">
              <div class="title">{_esc(c.title)} {blurb_badge}</div>
              <div class="small">
                <span>Source: <code>{_esc(c.source)}</code></span>
                &nbsp;•&nbsp;
                <a href="{_esc(c.url)}" target="_blank" rel="noopener">Open article</a>
                &nbsp;•&nbsp;
                <a href="/curate/{i}">Curate</a>
              </div>
              <div class="small"><code>{_esc(c.url)}</code></div>
            </div>
            <div style="display:flex; gap:8px; align-items:flex-start;">
              <a class="btn" href="/curate/{i}">Curate</a>
            </div>
          </div>
        </div>
        """)

    msg = f'<div class="msg">{_esc(status)}</div>' if status else ""

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>TSL Candidate Review</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif; margin: 24px; }}
    .wrap {{ max-width: 980px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
    .meta {{ color: #555; margin-bottom: 16px; }}
    .toolbar {{ display:flex; gap:12px; align-items:center; margin:16px 0; flex-wrap:wrap; }}
    .btn {{ padding:8px 12px; border:1px solid #ccc; background:#f7f7f7; border-radius:8px; cursor:pointer; text-decoration:none; color:#111; display:inline-block; }}
    .btn:hover {{ background:#eee; }}
    .field {{ width:100%; padding:10px; border-radius:8px; border:1px solid #ccc; font-size:14px; }}
    .cards {{ display:flex; flex-direction:column; gap:10px; }}
    .card {{ border:1px solid #ddd; border-radius:12px; padding:12px; background:#fff; }}
    .row {{ display:flex; align-items:flex-start; gap:10px; }}
    .title {{ font-weight:600; margin-bottom:6px; }}
    .small {{ color:#666; font-size:12px; }}
    a {{ color:#0b57d0; text-decoration:none; }}
    a:hover {{ text-decoration:underline; }}
    .msg {{ background:#e7f3ff; border:1px solid #b6daff; padding:10px; border-radius:10px; margin:12px 0; }}
    .muted {{ color:#777; }}
    code {{ background:#f3f3f3; padding:2px 4px; border-radius:6px; }}
    .badge {{ font-size: 11px; padding: 2px 6px; border: 1px solid #ccc; border-radius: 999px; margin-left: 6px; color:#444; background:#fafafa; }}
  </style>
</head>
<body>
<div class="wrap">
  <h1>TSL Candidate Review</h1>
  <div class="meta">
    Candidates file: <code>{_esc(str(CANDIDATES_FILE))}</code><br/>
    Selection file: <code>{_esc(str(SELECTED_FILE))}</code><br/>
    Curation file: <code>{_esc(str(CURATION_FILE))}</code>
  </div>
  {msg}

  <div class="toolbar">
    <button class="btn" type="button" onclick="location.href='/refresh'">Refresh candidates</button>
    <button class="btn" type="button" onclick="location.href='/preview'">Preview newsletter</button>
    <button class="btn" type="button" onclick="selectAll(true)">Select all</button>
    <button class="btn" type="button" onclick="selectAll(false)">Select none</button>
    <input class="field" type="text" id="q" placeholder="Search titles / sources..." onkeypress="if(event.key==='Enter'){{event.preventDefault();applySearch();}}" />
    <button class="btn" type="button" onclick="applySearch()">Filter</button>
  </div>

  {"<p class='muted'>No candidates yet. Click <b>Refresh candidates</b> to collect from TSL.</p>" if not candidates else ""}

  <form method="POST" action="/save" id="form">
    <div style="margin: 16px 0;">
      <div class="small">Subject</div>
      <input class="field" type="text" name="subject" value="{_esc(subject)}" />
    </div>

    <div style="margin: 16px 0;">
      <div class="small">Intro</div>
      <textarea class="field" name="intro" rows="4">{_esc(intro)}</textarea>
    </div>

    <div class="toolbar">
      <button class="btn" type="submit">Save Selection</button>
      <span class="small">Selected: <span id="selCount">0</span></span>
    </div>

    <div class="cards" id="cards">
      {''.join(cards)}
    </div>
  </form>
</div>

<script>
function selectAll(val) {{
  document.querySelectorAll('input[type="checkbox"][name="picked"]').forEach(cb => cb.checked = val);
  updateCount();
}}
function updateCount() {{
  const n = document.querySelectorAll('input[type="checkbox"][name="picked"]:checked').length;
  document.getElementById('selCount').textContent = n;
}}
function applySearch() {{
  const q = (document.getElementById('q').value || '').trim().toLowerCase();
  document.querySelectorAll('#cards .card').forEach(card => {{
    const t = card.getAttribute('data-title') || '';
    const s = card.getAttribute('data-source') || '';
    const ok = !q || t.includes(q) || s.includes(q);
    card.style.display = ok ? '' : 'none';
  }});
}}
updateCount();
</script>
</body>
</html>
"""
    return html.encode("utf-8")


_CURATE_TMPL = Template(r"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Curate: ${title_esc}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif; margin: 24px; }
    .wrap { max-width: 980px; margin: 0 auto; }
    .topbar { display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:12px; }
    .btn { padding:8px 12px; border:1px solid #ccc; background:#f7f7f7; border-radius:8px; cursor:pointer; text-decoration:none; color:#111; display:inline-block; }
    .btn:hover { background:#eee; }
    .meta { color:#555; font-size:13px; margin: 6px 0 16px; }
    .msg { background:#e7f3ff; border:1px solid #b6daff; padding:10px; border-radius:10px; margin:12px 0; }
    .panel { border:1px solid #ddd; border-radius:12px; padding:14px; background:#fff; }
    .article { margin-top: 14px; }
    .article h1,.article h2,.article h3 { margin-top: 18px; }
    .small { color:#666; font-size:12px; }
    .muted { color:#777; }
    code { background:#f3f3f3; padding:2px 4px; border-radius:6px; }
    hr { border:0; border-top:1px solid #eee; margin: 18px 0; }
    .imggrid { display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }
    .imgcard { border:1px solid #eee; border-radius:12px; padding:10px; background:#fafafa; }
    .imgcard img { width:100%; height:auto; display:block; border-radius:10px; }
    .field { width:100%; padding:10px; border-radius:8px; border:1px solid #ccc; font-size:14px; }
    .label { font-size:12px; color:#666; margin-bottom:6px; }

    .exlist { display:flex; flex-direction:column; gap:10px; margin-top:10px; }
    .exrow { border:1px solid #eee; border-radius:12px; padding:10px; background:#fafafa; display:flex; gap:10px; align-items:flex-start; }
    .extext { flex:1; white-space:pre-wrap; }
    .selbox { border:1px dashed #bbb; border-radius:12px; padding:10px; background:#fff; }
    .selpreview { white-space:pre-wrap; font-size:13px; color:#333; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .hidden { display:none !important; }
    .modalback { position:fixed; inset:0; background:rgba(0,0,0,0.5); display:none; align-items:center; justify-content:center; padding:20px; }
    .modal { background:#fff; border-radius:14px; max-width:920px; width:100%; padding:14px; border:1px solid #ddd; }
    .modalhead { display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap; }
    .canvaswrap { margin-top:12px; border:1px solid #ddd; border-radius:12px; padding:10px; background:#fafafa; }
    canvas { max-width:100%; height:auto; display:block; }  
    .badge { font-size: 11px; padding: 2px 6px; border: 1px solid #ccc; border-radius: 999px; margin-left: 6px; color:#444; background:#fafafa; }                                      
  </style>
</head>
<body>
<div class="wrap">

  <div class="topbar">
    <a class="btn" href="/">← Back to list</a>
    ${prev_link}
    ${next_link}
    <a class="btn" href="${url_esc}" target="_blank" rel="noopener">Open original ↗</a>
    <a class="btn" href="/api/clean?url=${url_esc}" target="_blank" rel="noopener">View JSON ↗</a>
  </div>

  <h1 style="margin:0 0 6px 0; font-size:22px;">${title_esc}</h1>
  <div class="meta">
    Item ${item_num} of ${total} &nbsp;•&nbsp;
    Source: <code>${source_esc}</code><br/>
    Date: <code>${pub_esc}</code> (confidence: <code>${conf_esc}</code>)
  </div>

  ${msg_html}

  <div class="panel">
    <form method="POST" action="/curate/save">
      <input type="hidden" name="index" value="${index}"/>
      <input type="hidden" name="url" value="${url_esc}"/>

      <div class="label">Final blurb (this is what you’ll paste into Constant Contact)</div>
      <textarea class="field" id="final_blurb" name="final_blurb" rows="5" placeholder="Write a short newsletter-ready blurb...">${final_blurb_esc}</textarea>

      <div class="topbar" style="margin-top:10px;">
        <button class="btn" type="submit">Save blurb</button>
        <button class="btn" type="button" onclick="joinExcerpts()">Join excerpts → blurb</button>
      </div>
    </form>

    <hr/>

    <div class="label">Excerpt capture (highlight text in the article below)</div>
    <div class="topbar">
        <button class="btn" type="button" onclick="captureSelection()">Preview selection</button>

        <button class="btn" id="btnAdd" type="button" onclick="addSelection()" disabled>Add Selected Text</button>
        <span class="small" id="selHint">Highlight text in the article to enable Add.</span>

        <button class="btn" type="button" onclick="removeLast()">Remove last excerpt</button>
        <button class="btn" type="button" onclick="clearAll()">Clear all excerpts</button>

        <button class="btn" id="btnToggleImages" type="button" onclick="toggleImages()">Hide images</button>
    </div>

    <div class="selbox">
      <div class="small">Selection preview</div>
      <div class="selpreview" id="selPreview">(nothing selected yet)</div>
    </div>

    <div style="margin-top:12px;">
      <div class="small">Saved excerpts</div>
      ${excerpts_html}
    </div>

    <hr/>

    <div id="imagesPanel">
      <div class="small">Detected images (click to open full size)</div>
      ${images_html}
      <hr/>
    </div>

    <div class="small">Cleaned article content (highlight text here)</div>
    <div class="article" id="articleBody">
      ${clean_html}
    </div>
  </div>

    <div class="modalback" id="cropBack">
        <div class="modal">
            <div class="modalhead">
            <div>
                <div style="font-weight:600;">Crop image</div>
                <div class="small" id="cropSrc">(no image)</div>
            </div>
                <div style="display:flex; gap:10px; flex-wrap:wrap;">
                    <button class="btn" type="button" onclick="resetCrop()">Reset</button>
                    <button class="btn" type="button" onclick="saveCrop()">Save crop</button>
                    <button class="btn" type="button" onclick="closeCrop()">Close</button>
                </div>
            </div>

            <div class="canvaswrap">
            <canvas id="cropCanvas"></canvas>
                <div class="small muted" style="margin-top:8px;">
                    Drag to draw a crop rectangle. Release to set it.
                </div>
            </div>
        </div>
    </div>                        

</div>

<script>
                        
// -----------------------------
// Image crop modal (canvas)
// -----------------------------
let __cropImg = null;
let __cropSrc = "";
let __cropRect = null; // {x,y,w,h} in canvas coords
let __drag = null;     // {sx,sy}

// Show modal and load image
function openCrop(src) {
  __cropSrc = src;
  __cropRect = null;
  __drag = null;

  const back = document.getElementById('cropBack');
  const label = document.getElementById('cropSrc');
  const canvas = document.getElementById('cropCanvas');
  const ctx = canvas.getContext('2d');

  if (label) label.textContent = src;
  if (back) back.style.display = 'flex';

  __cropImg = new Image();
  __cropImg.crossOrigin = "anonymous"; // best effort; may still be blocked by remote headers
  __cropImg.onload = () => {
    // Fit image to a reasonable canvas width
    const maxW = 860;
    const scale = (__cropImg.width > maxW) ? (maxW / __cropImg.width) : 1.0;
    canvas.width = Math.round(__cropImg.width * scale);
    canvas.height = Math.round(__cropImg.height * scale);
    drawCrop();
  };
  __cropImg.onerror = () => {
    alert('Could not load image for cropping (CORS or fetch issue). You can still open it in a new tab.');
    closeCrop();
  };
  __cropImg.src = src;
}

function closeCrop() {
  const back = document.getElementById('cropBack');
  if (back) back.style.display = 'none';
  __cropImg = null;
  __cropSrc = "";
  __cropRect = null;
  __drag = null;
}

function resetCrop() {
  __cropRect = null;
  drawCrop();
}

function drawCrop() {
  const canvas = document.getElementById('cropCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (__cropImg) {
    ctx.drawImage(__cropImg, 0, 0, canvas.width, canvas.height);
  }

  if (__cropRect) {
    const r = normalizeRect(__cropRect);
    // darken outside
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.35)';
    ctx.beginPath();
    ctx.rect(0,0,canvas.width,canvas.height);
    ctx.rect(r.x, r.y, r.w, r.h);
    ctx.fill('evenodd');
    ctx.restore();

    // border
    ctx.save();
    ctx.strokeStyle = 'rgba(255,255,255,0.95)';
    ctx.lineWidth = 2;
    ctx.strokeRect(r.x + 0.5, r.y + 0.5, r.w, r.h);
    ctx.restore();
  }
}

function normalizeRect(r) {
  let x = r.x, y = r.y, w = r.w, h = r.h;
  if (w < 0) { x = x + w; w = -w; }
  if (h < 0) { y = y + h; h = -h; }
  // clamp
  const canvas = document.getElementById('cropCanvas');
  x = Math.max(0, Math.min(x, canvas.width));
  y = Math.max(0, Math.min(y, canvas.height));
  w = Math.max(1, Math.min(w, canvas.width - x));
  h = Math.max(1, Math.min(h, canvas.height - y));
  return {x, y, w, h};
}

function canvasPos(evt) {
  const canvas = document.getElementById('cropCanvas');
  const r = canvas.getBoundingClientRect();
  const x = (evt.clientX - r.left) * (canvas.width / r.width);
  const y = (evt.clientY - r.top) * (canvas.height / r.height);
  return {x, y};
}

// mouse events
(function attachCropEvents() {
  const canvas = document.getElementById('cropCanvas');
  if (!canvas) return;

  canvas.addEventListener('mousedown', (e) => {
    if (!__cropImg) return;
    const p = canvasPos(e);
    __drag = {sx: p.x, sy: p.y};
    __cropRect = {x: p.x, y: p.y, w: 1, h: 1};
    drawCrop();
  });

  window.addEventListener('mousemove', (e) => {
    if (!__drag || !__cropRect) return;
    const p = canvasPos(e);
    __cropRect.w = p.x - __drag.sx;
    __cropRect.h = p.y - __drag.sy;
    drawCrop();
  });

  window.addEventListener('mouseup', () => {
    if (!__drag) return;
    __drag = null;
    if (__cropRect) __cropRect = normalizeRect(__cropRect);
    drawCrop();
  });
})();

async function saveCrop() {
  if (!__cropImg || !__cropSrc) return;
  if (!__cropRect) { alert('Draw a crop rectangle first.'); return; }

  const canvas = document.getElementById('cropCanvas');
  const r = normalizeRect(__cropRect);

  // Save crop metadata (not the pixels) so you can crop later in a tool
  const payload = {
    x: Math.round(r.x),
    y: Math.round(r.y),
    w: Math.round(r.w),
    h: Math.round(r.h),
    iw: __cropImg.width,
    ih: __cropImg.height,
    cw: canvas.width,
    ch: canvas.height
  };

  await postForm('/curate/save_crop', {
    index: '${index}',
    url: '${url_esc}',
    img_src: __cropSrc,
    crop: JSON.stringify(payload)
  });

  closeCrop();
  location.reload();
}

function copyText(t) {
  navigator.clipboard.writeText(t).then(() => {});
}

function getSelectedText() {
  const sel = window.getSelection();
  if (!sel) return '';
  return (sel.toString() || '').trim();
}

function updateSelectionUI() {
  const t = getSelectedText();
  const btn = document.getElementById('btnAdd');
  const hint = document.getElementById('selHint');
  if (!btn || !hint) return;

  if (!t || t.length < 2) {
    btn.disabled = true;
    hint.textContent = 'Highlight text in the article to enable Add.';
  } else {
    btn.disabled = false;
    hint.textContent = 'Selected ' + t.length + ' chars';
  }
}

document.addEventListener('selectionchange', () => {
  clearTimeout(window.__selTimer);
  window.__selTimer = setTimeout(updateSelectionUI, 80);
});

window.addEventListener('load', () => {
  updateSelectionUI();
});

function captureSelection() {
  const t = getSelectedText();
  const p = document.getElementById('selPreview');
  if (p) p.textContent = t || '(nothing selected)';
}

async function postForm(path, obj) {
  const body = new URLSearchParams(obj);
  return fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body
  });
}

async function addSelection() {
  const t = getSelectedText();
  if (!t) { alert('Select some text in the article first.'); return; }
  await postForm('/curate/add_excerpt', {
    index: '${index}',
    url: '${url_esc}',
    excerpt: t
  });
  location.reload();
}

async function removeLast() {
  await postForm('/curate/pop_excerpt', {
    index: '${index}',
    url: '${url_esc}'
  });
  location.reload();
}

async function clearAll() {
  if (!confirm('Clear all saved excerpts for this article?')) return;
  await postForm('/curate/clear_excerpts', {
    index: '${index}',
    url: '${url_esc}'
  });
  location.reload();
}

function joinExcerpts() {
  const ex = Array.from(document.querySelectorAll('.extext'))
    .map(e => (e.innerText || '').trim())
    .filter(Boolean);

  if (!ex.length) { alert('No excerpts to join yet.'); return; }
  const joined = ex.join(' ');
  const ta = document.getElementById('final_blurb');
  if (!ta) return;

  if (ta.value.trim()) ta.value = ta.value.trim() + "\n\n" + joined;
  else ta.value = joined;
}

function toggleImages() {
  const panel = document.getElementById('imagesPanel');
  const btn = document.getElementById('btnToggleImages');
  if (!panel || !btn) return;

  const isHidden = panel.classList.contains('hidden');
  if (isHidden) {
    panel.classList.remove('hidden');
    btn.textContent = 'Hide images';
  } else {
    panel.classList.add('hidden');
    btn.textContent = 'Show images';
  }
}
</script>

</body>
</html>
""")


def curate_page_html(
    index: int,
    total: int,
    c: Candidate,
    cleaned: dict[str, Any],
    final_blurb: str,
    excerpts: list[str],
    status: str,
) -> bytes:
    title = cleaned.get("title") or c.title
    pub = cleaned.get("published_date") or "n/a"
    conf = cleaned.get("date_confidence") or "n/a"
    imgs = cleaned.get("images") or []
    crops = cleaned.get("image_crops") or {}
    clean_html = cleaned.get("clean_html") or "<p><em>No cleaned HTML returned.</em></p>"

    msg_html = f'<div class="msg">{_esc(status)}</div>' if status else ""

    prev_idx = index - 1
    next_idx = index + 1
    prev_link = f"<a class='btn' href='/curate/{prev_idx}'>◀ Prev</a>" if prev_idx >= 0 else ""
    next_link = f"<a class='btn' href='/curate/{next_idx}'>Next ▶</a>" if next_idx < total else ""

    # images
    img_cards = []
    for im in imgs[:12]:
        src = _esc((im or {}).get("src") or "")
        alt = _esc((im or {}).get("alt") or "")
        score = _esc(str((im or {}).get("score") or ""))
        if not src:
            continue

        is_cropped = (im.get("src") in crops)  # compare with raw src, not escaped
        crop_badge = '<span class="badge">cropped</span>' if is_cropped else ""


        img_cards.append(f"""
          <div class="imgcard">
            <a href="{src}" target="_blank" rel="noopener">
              <img src="{src}" alt="{alt}" loading="lazy"/>
            </a>
            <div class="small">score: <code>{score}</code></div>
            <div style="margin-top:8px; display:flex; gap:8px; flex-wrap:wrap;">
              <button class="btn" type="button" onclick="openCrop('{src}')">Crop</button>
              <button class="btn" type="button" onclick="copyText('{src}')">Copy URL</button>
            </div>
          </div>
        """)

    images_html = (
        "<div class='muted'>No images detected for this page.</div>"
        if not img_cards
        else f"<div class='imggrid'>{''.join(img_cards)}</div>"
    )

    # excerpts list
    excerpt_rows = []
    for i, x in enumerate(excerpts or []):
        excerpt_rows.append(f"""
          <div class="exrow">
            <div class="extext" id="ex_{i}">{_esc(x)}</div>
            <button class="btn" type="button" onclick="copyText(document.getElementById('ex_{i}').innerText)">Copy</button>
          </div>
        """)
    excerpts_html = (
        "<div class='muted'>No excerpts saved yet. Highlight text in the article and click <b>Add Selected Text</b>.</div>"
        if not excerpt_rows
        else f"<div class='exlist'>{''.join(excerpt_rows)}</div>"
    )

    rendered = _CURATE_TMPL.safe_substitute(
        title_esc=_esc(title),
        index=str(index),
        item_num=str(index + 1),
        total=str(total),
        url_esc=_esc(c.url),
        source_esc=_esc(c.source),
        pub_esc=_esc(pub),
        conf_esc=_esc(conf),
        msg_html=msg_html,
        prev_link=prev_link,
        next_link=next_link,
        final_blurb_esc=_esc(final_blurb or ""),
        excerpts_html=excerpts_html,
        images_html=images_html,
        clean_html=clean_html,
    )
    return rendered.encode("utf-8")