# TSLAC Newsletter Helper — Design Document

## 1. Purpose

Build a local, single-user application that helps produce a monthly newsletter based on content published on:

https://www.tsl.texas.gov

The application supports:

- Collecting candidate articles
- Reviewing and curating article content
- Selecting text excerpts
- Writing a final newsletter blurb
- Selecting and (later) cropping images
- Generating a Constant Contact–ready preview/export

This is a local-only tool. No authentication, no database, no multi-user collaboration.

---

## 2. High-Level Workflow

### Step A — Collect Candidates

1. User clicks **Refresh candidates**
2. App fetches:
   - Homepage Carousel
   - Homepage Featured News
   - `/info` page for recent `/node` articles (last ~3 months)
3. App writes:
   - `output/candidates_latest.json`
4. Previously seen URLs tracked in:
   - `state/seen_urls.json`

---

### Step B — Candidate Selection (Main UI)

URL:
http://127.0.0.1:5055/

User can:

- View grouped candidates
- Search/filter
- Check/uncheck items
- Save selection → `selected.yaml`
- Click **Curate** to review a specific item

---

### Step C — Curate Individual Article

URL:
`/curate/<index>`

Backend:

- Fetches article
- Runs `cleaner.clean_article(url)`
- Displays:
  - Cleaned article HTML
  - Excerpt capture tools
  - Image panel
  - Final blurb editor

User can:

- Highlight text
- Add excerpt
- Remove last excerpt
- Clear excerpts
- Join excerpts → blurb
- Save final blurb

Data saved in:
`curation.yaml`

---

### Step D — Export Preview (Constant Contact Pack)

URL:
`/preview`

App reads:

- `selected.yaml`
- `curation.yaml`

App generates:

- Newsletter preview HTML
- Copy-ready blocks for Constant Contact

---

## 3. Project Structure

### Entry Point

#### `newsletter_bot.py`

Responsibilities:

- Starts HTTP server
- Imports `Handler` from `server.py`
- Ensures output/state directories exist
- Applies macOS truststore fix

---

### Routing Layer

#### `server.py`

Handles:

- `/refresh` → fetch candidates
- `/` → list page
- `/curate/<index>` → curate page
- `/api/clean?url=` → JSON cleaner output
- `/preview` → preview/export page

Handles POST routes:

- `/save` → save selected.yaml
- `/curate/add_excerpt`
- `/curate/pop_excerpt`
- `/curate/clear_excerpts`
- `/curate/save` → save final blurb

---

### Cleaning Logic

#### `cleaner.py`

Returns structured object:

- `title`
- `published_date`
- `date_confidence`
- `clean_html`
- `text_plain`
- `images[]`
- `extraction_quality`

Responsible for:

- Removing navigation/footer
- Identifying main content region
- Detecting and scoring images

---

### Template Rendering

#### `templates.py` (or inline functions)

Functions:

- `html_page(...)`
- `curate_page_html(...)`

Responsibilities:

- Render candidate list
- Render curate UI
- Display excerpts
- Show image panel

---

### Export Logic

#### `export_preview.py`

Responsibilities:

- Read `selected.yaml`
- Read `curation.yaml`
- Build preview HTML
- Generate copy-ready blocks
- (Future) Download and crop images

---

## 4. Data Files

| File | Purpose |
|------|---------|
| `output/candidates_latest.json` | Current candidate snapshot |
| `state/seen_urls.json` | Previously seen URLs |
| `selected.yaml` | Newsletter issue selection |
| `curation.yaml` | Per-URL curation data |

---

## 5. Candidate Extraction Rules

### Carousel (Homepage)

Extract:

- URL from:
  `div.views-field-field-image a[href]`
- Title from:
  `div.views-field-title-1 span.field-content`

Filter out:

- `/contact`
- `/visit`
- Non-article links
- Explicit excluded titles

---

### Featured News

Extract from homepage Featured News section.

Filters:

- Remove excluded paths
- Prefer `/node` links
- Remove generic navigation links

---

### `/info` Page

Include:

- URLs containing `/node`
- Only items with parseable dates
- Only items within last 3 months

Display format:

Title (Mon DD, YYYY)

---

## 6. Curation Model

`curation.yaml` structure:

```yaml
https://www.tsl.texas.gov/node/1234:
  final_blurb: "Short newsletter summary..."
  excerpts:
    - "Excerpt text one..."
    - "Excerpt text two..."
  updated_at: "2026-02-23T10:15:00"
```

Planned additions:

```yaml
  selected_image: "https://..."
  image_crop:
    x: 100
    y: 50
    w: 600
    h: 400
```

---

## 7. UX Features Implemented

- Next/Prev navigation in curate view
- Excerpt preview before saving
- Join excerpts → blurb
- Toggle images panel
- Clean HTML rendered by backend
- Blurb stored separately from excerpts

---

## 8. Export Goals (Next Phase)

Constant Contact support:

- Copy block buttons:
  - Copy Title
  - Copy Subtitle
  - Copy Blurb
  - Copy Read More link
- Structured preview layout
- Optional folder export:

```
export/
  preview.html
  blocks/
  images/
```

---

## 9. Known Challenges Encountered

- macOS SSL validation issues → resolved via truststore
- Cleaner capturing footer content → refined stripping logic
- Excerpts saved but not shown → missing load wiring fixed
- JS inside Python f-strings causing syntax errors → careful escaping required
- Redirect loops in preview route → resolved by ensuring 200 response

---

## 10. Current Status

Working:

- Candidate collection
- Selection UI
- Curation UI
- Excerpt persistence
- Final blurb persistence
- Cleaner JSON endpoint
- Basic preview route (in progress)

Next focus:

- Polished Constant Contact export pack
- Image selection + crop storage
- Copy-block UX improvements