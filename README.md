TSLAC Newsletter Helper – Project Context Header

Project Name: TSLAC Newsletter Helper
Repo: https://github.com/dweilert/tslac
Repo Branch: refactor/http-router

Runtime: Custom Python web app (custom web/router, not Flask/Django)
Python Version: 3.12
Architecture Style: Routes → Services → Storage → Templates
Rendering: Server-side templates (render() helper)
Data Storage: YAML + JSON files in local filesystem
 
-- Architecture Overview. --

Routing Layer
- web/router.py
- routes/candidates.py
- routes/curate_article.py
- routes/config.py
- routes/watch.py (being deprecated)

Services Layer
- services/candidates_service.py
- services/curate_article_service.py
- services/watch_service.py
- services/api_service.py

Storage Layer
- storage/collector_store.py
- storage/curation_store.py
- storage/selected_store.py
- watch_store.py

Scraping / Collection
- collect/collector.py
- ollect/rules.py
- watch/scan.py
- watch/fetch.py
- watch/parse.py
- watch/score.py

🎯 Current Long-Term Goals

1. Rewrite TSLAC scraping:
  - Homepage: Carousel + Featured News
  - /info page: last 90 days

2. Remove seen URL skipping

3. Fully unify article + doc curation

4. Add title + subtitle fields to curate + preview

5. Integrate TinyMCE editor (CDN, key stored in .env.local)

6. Make Refresh gather:
  - TSLAC
  - Watch sites
  - Local docs
  - GDrive docs

7. Remove legacy /watch page entirely

⚠️ Known Refactor State
- Watch results now appear in main candidate list.
- Image selection unified (set + clear working).
- Selected image indicator partially integrated on home page.
- Docs still partially using legacy curate path.
- Seen URL logic still active but planned for removal.


In this chat we are focusing on:
----------------------------------------------------------------------
Milestone 1: Rewrite TSLAC Scraper (Homepage + /info 90 Days)

Rewrite collect.collector.collect_candidates to:

Scrape homepage of tsl.texas.gov:

Carousel section is currently implemented 

Featured News section is not be scraped yet.  The information to be scraped in located in the section under this heading in the html: <h2>Featured News</h2> and when this is located the you are at the end of the featured news: 'See More News and Events' 


Scrape /info page: is not being scraped yet.  Each new item to be reviewed is started with this html: <time datetime= and the equivalent of the article topic is starts with: <div <a href="/node/????" hreflang=" and the topic is found in the portion that starts with: class="field-content">

Question marks in the /node/ are really a number that changes with each topic.  The date is in the format: “Thursday, February 12, 2026”

Include only articles that have occured in the last 90 days.


Normalize candidates with:

title
url
source = "tslac"
published date
Remove legacy scraping assumptions

Keys Files involved:

collect/collector.py
collect/rules.py
services/candidates_service.py



We are NOT working on other subsystems unless explicitly stated.

I will paste the relevant function(s) as needed.

















# tslac

Good. Let’s turn the pain into a repeatable solution so this never happens again.

The issue wasn’t markdown itself — it was **nested code fences colliding**. When you ask for “raw markdown” and that markdown itself contains triple backticks, the outer fence gets terminated early unless it’s handled correctly.

Here’s how to avoid that permanently.

---

# ✅ How To Avoid Markdown Fence Breakage

## 1️⃣ Always Specify the Fence Depth

When you want markdown that contains code blocks, say:

> “Wrap the entire document in FOUR backticks so inner triple backticks don’t break it.”

That forces a structure like:

````markdown
```mermaid
diagram here
```
````

Four outer backticks
Three inner backticks

No collision.

---

## 2️⃣ Use This Exact Phrase (Copy This)

When requesting documentation in the future, paste this:

> Provide the ENTIRE document in raw markdown wrapped in four backticks so inner triple backticks are preserved. Do not truncate any sections.

That sentence prevents:

* Partial output
* Broken fences
* Early termination
* Chat formatting interference

---


## Starting a new chat

### g-Drive
I’m working on a local newsletter helper app for tsl.texas.gov. The repo for the current code is in: https://github.com/dweilert/tslac Please read Design.md and Design2.md design documents. 

I'd like to add a new feature that allows me to retrieve information from a Google g-drive that contains a folder with one or more documents. These documents can be created with many different products including Microsoft Word, Google Docs, RTF, plain text, html, and PDF files. I need to review each document and provide a summary of what each is suggesting. The results need to be incorporated into the primary / first page of the application where the Candidate Review List is created. I should be able to select the document via a check box and have the ability to Curate like the other documents. 

Please let me know what else I need to provide. Also, do I need to modify this code base to start using Flask or FastAPI to support a more robust solution?

### Re-factor
I’m working on a local newsletter helper app for tsl.texas.gov. The repo for the current code is in: https://github.com/dweilert/tslac Please read Design.md, Design2.md and Design3.mddesign documents. 

I'd like to review the code and re-factor as many of the modules have gotten very large, some almost a 1000 lines of code.  I would like to separate the templates.py into separate html for each page, possibly separate the do_GET do_POST defs into individual modules these are in server.py right now. Along with a general review of the repository and other possible suggestions to improve how the code is maintained and tested.   

### Re-factor stage II

I’m working on a local newsletter helper app for tsl.texas.gov. The repo for the current code is in: https://github.com/dweilert/tslac Please read Design.md, Design2.md and Design3.md design documents. I'd like to review the code and re-factor as many of the modules have gotten very large, some almost a 1000 lines of code. 

I would like to continue the re-factoring. In a previous chat we focused on much of the HTML and the rending and routes.  Please review the code deeper and make suggestions.  Along with a general review of the repository and other possible suggestions to improve how the code is maintained and tested.


I’m working on a local newsletter helper app for tsl.texas.gov. The repo for the current code is in: https://github.com/dweilert/tslac. With the latest code base in the refactor/http-router not in the main branch, .I would like to continue the re-factoring. In a previous chats we have re-factor multiple facets of the code.  Please review the code deeper and make suggestions.  Along with a general review of the repository and other possible suggestions to improve how the code is maintained and tested.

I’m working on a local newsletter helper app for tsl.texas.gov. The repo for the current code is in: https://github.com/dweilert/tslac. With the latest code base in the refactor/http-router not in the main branch.  

Past efforts did significant re-factoring but I did not keep and eye on some of the changes and relize now that some of the core features of the app need to be modified and fixed to return to my original needs.  

I'd like you to review the code, ignoring the Design.md, Design2.md and Design3.md documents.  The current design has two distinct curate approaches: one for the web based located articles and another for the g-drive / local. I'd like to consolidate these into a single approach that can handle both sources of content.

When the curating is performed the final blurb content creation where the scrapped content is copied to create one or excerpts and then combined into a final blurb should be grouped together in a single area of the page; and the image selection should be grouped together as well. So making the image selection more of a separate fucntion from the blurb creation.  Also the button to combine the excerpts into the final blurb area seems to be missing.  

The cureate of the g-drive / local content needs to more aligned with the web based approach so that it can handle both sources in a single way.  I think an apparoach is the current content that summirizes the g-drive info could be placed in the final blurb area and edited there.  

On the main page there also needs to be a selection check box in front of each g-drive articale so that it can be selected for inclusion in the preview process.

There is alot of UI re-design that needs to be done.

### ----------------------


I’m working on a local newsletter helper app for tsl.texas.gov. 

With your help I've been re-factoring the code in this github repo: https://github.com/dweilert/tslac. With the latest code base in the refactor/http-router branch not in the main branch.  

Past efforts did significant re-factoring and I would like you to reivew the code and help me understand the architecture and design approaches used in the re-factoring.  Please ignore the information in the Design.md, Design2.md, and Design3.md documents as it is out of date.

I'd like new design documents that tell me what this application does along with interaction diagrams if possible. 

Some of what is confussing is the separation of code into different modules and how they interact.  Why is the services layer used in conjunction with other layers. Why leave all of the doc_* modules in the root and not move them to a separate directory / package, etc. 

### --------------------

With your help I've been re-factoring the code in this github repo: https://github.com/dweilert/tslac. With the latest code base in the refactor/http-router branch not in the main branch. 

Past efforts did significant re-factoring and I would like you to reivew the code and help me understand the architecture and design approaches used in the re-factoring. Please ignore the information in the Design.md, Design2.md, and Design3.md documents as it is out of date. 

There are two modules that have names that are confusing: `export_preview.py` and `export_cc.py`.  The export_preview.,py is not exporting anything it is a preview module that generates a preview of the selected candidate articles. The export_cc.py module exports the selected candidate article blurbs and images that were used to generate the preview.

There has been some confusion in the re-factoring efforts and I'd like to rename the export_preview to something more inline with its   functionality.  I'd like to rename it: preview_generator.py

Please help me accomplish this task.

### ---------------------



Question 1: Candidate ID strategy 
Answer: treat as new

Question 2: “Open doc” behavior for Google Drive
Answer: open in browser

Question 3: Doc text extraction scope
Answer: I'm OK with okay with “phase 1 = pdf + docx + gdoc, phase 2 = everything else”, implementation is much faster and more reliable.

Question 4: TSL info page filter
Answer: Articles on the 'info' page start with a date in this format:  Thursday, February 12, 2026 

Additional notes:
the current process of createing the 'seen' site and skipping those sites on the next refresh can be removed.  Show all candidates articles every time the refresh is run.

In the top portion of the Curate page can you provide a much more robust text editor for creating the final blurb. I'm hoping you can recommend a nice text editor for this feature.  The code to support the editor can be available via a CDN or if necessary downloaded and but in the repository.  I prefer just getting the code from a CDN.


Lets use TinyMCE, and plan on having a key.  With that said I'd like to have a new page that will allow me to edit the config.py file to help maintain the key and other needed parameters for the application.  Also move the web sties and key words currently entered in the watch screen to this file.  No need to have that current page.

When the refresh button is pressed it should also scrap the site or sites that are identidied in the 'watch' feature.  This makes the app scrap / search all locations or sources for candidate articles in a single action.  

Yes, use a web page to update information in the config.py is the correct approach.  Also lets keep watch keywords to remain part of scoring/filtering.

Before we get started I want to ask that we tackle one item at a time and not show me a list of 1 to ?? items to change or create.  It is just too hard to ensure the changes get done properly.  If there are logical breaks in the development that can be used as places to test what has been done to that point lets do the testing.  

I expect this to take some time and in the past I've run into the issue of our chats getting very, very, long and slow.  So please let me know if there is a good place to segement our work and keep the chats working without long wait times and you dropping context.

---

I sorry please convert the config.py to a JSON or YAML file and use a web a page to modify that newly created file.

---

#################
#################



TSLAC Newsletter Helper – Project Context Header

Project Name: TSLAC Newsletter Helper
Repo: https://github.com/dweilert/tslac
Repo Branch: refactor/http-router

Runtime: Custom Python web app (custom web/router, not Flask/Django)
Python Version: 3.12
Architecture Style: Routes → Services → Storage → Templates
Rendering: Server-side templates (render() helper)
Data Storage: YAML + JSON files in local filesystem
 
-- Architecture Overview. --

Routing Layer
- web/router.py
- routes/candidates.py
- routes/curate_article.py
- routes/config.py
- routes/watch.py (being deprecated)

Services Layer
- services/candidates_service.py
- services/curate_article_service.py
- services/watch_service.py
- services/api_service.py

Storage Layer
- storage/collector_store.py
- storage/curation_store.py
- storage/selected_store.py
- watch_store.py

Scraping / Collection
- collect/collector.py
- collect/rules.py
- watch/scan.py
- watch/fetch.py
- watch/parse.py
- watch/score.py


Milestone 2 Objectives:

Replace/remove the curate doc process and use the curate_article process instead.  This will provide a single process to curate the candidate article without respect of where the article information was obtained.  

This will require the reading of files found in the g-drive or local directory.  When an item from either the g-drive or local directory will need to be read. The content will need to be shown in the Curate screen, if possible, so portions of the content can be selected to create one or more excerpts.  If the document cannot be shown in the curate display area a second browser window should be opened for viewing if possible.  If neither action can be performed the user should be told how to view the document.  

Once a document is located and it can processed the located text can be shown in the display area if the actual document cannnot be shown.  The displaying of the document text should be performed if possible and override displaying the actual document in the display area.  So simply put, get the document text and show it in the display area if possible, otherwise show the document in the display area, and if unable to display there open a separate browser window and if unable there tell the user how to view the document.

On the curate screen the user will need to be able to enter a title and subtitle along with the final blurb and selected image.

A needed step is to modify the config screen to include the following parameters that need to be move from the .env file and into the config.yaml: 

# input mode
DOC_INPUT_MODE=gdrive         # gdrive | local

# Drive mode (name lookup first-time; cache IDs)
GDRIVE_INPUT_FOLDER_NAME=tslac_input
GDRIVE_ARCHIVE_FOLDER_NAME=tslac_saved

# Local mode
LOCAL_INPUT_DIR=/Users/bob/tslac_input_docs
LOCAL_ARCHIVE_DIR=/Users/bob/tslac_saved_docs

# Message level for logging (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=DEBUG

What else do you need to know to move forward?


Question 1: What is the canonical ID for a “document candidate”?
Answer: 
There is also code in the repository for Document Processing in these locations: 
- watch/scan.py
- watch/fetch.py
- watch/parse.py
- watch/score.py
Can yo review this code to aid in answering this question

Question 2: What’s the current shape of doc candidates on disk?
Answer: the current output from the doc scan is in output/assets/watch_results_latest.json

I'll provide the code once you prompt for the modules.

Question 3: What document types do you expect to support first?
Answer:
Pdf, Word, Google Docs, Plain text, Rich text

Question 4: Google Drive auth model
Answer: The current implementation uses OAuth2.0 with a file named credentials.json in the root

Question 5: “Show text first” rule: how strict is it?
Answer: It is necessary to create the excerpts and the final blurb.  Without text this will be hand entry of information.  The manual toggle on the curate page would be nice.

Question 6: Curate UI fields and persistence
Question 6a: Should title/subtitle be stored per-candidate in curation_store (same as blurb), and then exported to Constant Contact?
Answer 6a:
Yes for both.

Questin 6b: Do you want subtitle optional? (assume yes)
Answer:
Yes

Question 6c: What’s the “selected image” source: URL only, or allow uploading/local? (Most likely URL only right now.)
Answer: URL web and and for local files support file:// if possible


Question 7: Config screen: storage format + validation rules
Question 7a: Do you want the config screen to edit all these fields directly (radio + text inputs), or keep some hidden/advanced?
Answer 7a: 
Direct edit of the fields

Question 7b: For paths: should the app validate that local dirs exist and show a warning if not?
Answer 7b:
Yes validate and warn

Question 7c: Should LOG_LEVEL be applied immediately or only on restart?
Answer 7c: restart only

Question 8: How “unified” should routing be?
Answer 8: 
Use Option A. One curate route

Question 9: What should happen after curation?
Answer 9: There is a 'back to list' button on the curate screen. The user should stay on the curate screen until they are done with all content and then press the 'back to list' button.



===============================================================================

===============================================================================

===============================================================================

===============================================================================

Below is the **complete Milestone 2 plan**, but structured so we can execute it **one task at a time**. After the plan, I’ll tell you exactly what **Task 1** is (the smallest, safest change that unlocks everything).

---

# Milestone 2 Complete Plan

## Goal

Replace/remove `curate_doc` and use the `curate_article` curation flow for **all** candidates (web + gdrive + local) via **one curate route**:

* `/curate?id=<candidate_id>`

and a single unified `store/candidates.json`.

---

## Data Model Decisions (locked)

### Candidate record (in `store/candidates.json`)

Keep existing fields and add:

* `id` (canonical)
* `origin` (`web|gdrive|local`)
* optional `doc` metadata

Source rules:

* web keeps existing `source` (e.g., Carousel)
* gdrive uses `source="Doc"`
* local uses `source="Local"`

Canonical IDs:

* `web:<url>`
* `gdrive:<file_id>`
* `local:<sha1(abs_path)>` and store `doc.local_path`

### Curation data (in `store/curation*.json` wherever you store it)

Key by `id`. For backward compatibility, when `origin=web`, fall back to `url` if old data exists.

Curation fields to persist:

* `title`
* `subtitle` (optional)
* `blurb`
* `image_url` (supports http(s) and file://)

---

## UX / Curate Screen Behavior (locked)

Text-first workflow:

1. Attempt to extract text
2. If extracted text exists → show it in curate display area (default)
3. Offer toggle: “View extracted text” / “View original”
4. If cannot embed original → provide “Open in new tab” link
5. If cannot open → show instructions

User stays on curate page until they press “Back to list”.

---

## Config Changes (locked)

Move these into `config.yaml` (editable via config screen):

* `doc_input_mode` (`gdrive|local`)
* `gdrive_input_folder_name`
* `gdrive_archive_folder_name`
* `local_input_dir`
* `local_archive_dir`
* `gdrive_credentials_path`
* `gdrive_token_path`
* `log_level` (restart required)

Validation:

* gdrive credentials file exists (warn/error)
* local dirs exist (warn)
* log_level restart-only

---

# Task List (execute in order, one task at a time)

## Task 1 — Add `id` + `origin` support to candidates storage (safe foundation)

**Files:** `storage/collector_store.py` (+ any candidate model if you have one)

* When loading `candidates.json`, backfill:

  * `id="web:"+url` if missing
  * `origin="web"` if missing
* When saving, always include `id` and `origin`
* Keep old format readable

✅ No UI changes yet
✅ No route changes yet
✅ Low risk, easy to test

**Done when:** app runs and loads candidates list unchanged.

---

## Task 2 — Introduce unified candidate lookup by `id`

**Files:** wherever you load candidates for UI routes (likely `routes/candidates.py` and/or service)

* Add helper: `find_candidate_by_id(candidates, id)`

✅ Still no curate changes
✅ Enables `/curate?id=...` next

---

## Task 3 — Add the unified curate route `/curate`

**Files:** `routes/curate.py` (new) or modify existing `routes/curate_article.py`

* Route: `GET /curate?id=...`
* Find candidate by id
* For now, **only handle `origin=web`** and delegate to existing curate_article service/template

✅ Web curate still works
✅ Doesn’t touch doc processing yet
✅ Establishes the route contract

---

## Task 4 — Expand curation storage to persist title/subtitle/image_url keyed by `id`

**Files:** `storage/curation_store.py` (or your curation store module), curate service(s)

* Add fields to saved curation record
* Read-by-id, fallback-to-url for older web records
* Update the curate page to display/edit these fields

✅ Still works for web
✅ Prepares doc curation to reuse same storage

---

## Task 5 — Move/refactor gdrive service into services layer + config-driven paths

**Files:** move `gdrive_service.py` → `services/gdrive_client.py`

* `get_drive_service(credentials_path, token_path)`
* `find_folder_id(service, folder_name)`
* `list_files_in_folder(service, folder_id)`
* Add folder-id caching to `state/gdrive_folders.json` (optional in this task)

✅ Prepares for doc candidate ingestion
✅ No UI impact

---

## Task 6 — Build “doc candidate ingestion” and merge into the single candidates list

**Files:** new `services/doc_candidate_service.py` (or `services/inputs/*`)

* If `doc_input_mode=gdrive`:

  * list files in input folder
  * convert each into a Candidate record with:

    * `id="gdrive:<file_id>"`
    * `origin="gdrive"`
    * `source="Doc"`
    * `url=webViewLink` (needs extra fields on list call)
* If `doc_input_mode=local`:

  * scan directory for pdf/docx/rtf/txt
  * generate local candidates
* Merge doc candidates into existing web candidates
* Save unified `store/candidates.json`

✅ UI list now shows docs mixed in
✅ Curate route still only web until next task

---

## Task 7 — Implement document text extraction pipeline (text-first)

**Files:** new `services/doc_text_service.py`

* Input: Candidate
* Output:

  * `extracted_text` (string or None)
  * `viewer_url` (for open-new-tab)
  * `embed_url` (if possible)
  * `view_instructions` (fallback)

Support types (in priority order):

* Plain text
* RTF (via striprtf)
* DOCX (python-docx)
* PDF (pypdf or similar)
* Google Docs export as text
* (later) Google Drive “download” for PDF/DOCX stored in Drive

✅ Doesn’t require UI changes yet (but will be used next)

---

## Task 8 — Enable curate for `origin=gdrive|local` using same template

**Files:** `services/curate_article_service.py` (or unified curate service), template changes

* When candidate is doc/local:

  * call doc_text_service
  * show extracted text by default
  * show toggle + “Open original” link

✅ This is the milestone’s main “unification”

---

## Task 9 — Retire curate_doc routes and unify navigation

**Files:** remove/stop registering `routes/curate_doc.py`, clean up menu links

* Ensure all doc items go through `/curate?id=...`
* Remove duplicate code paths

✅ curate_doc process removed as requested

---

## Task 10 — Archive behavior for docs

**Files:** gdrive/local services + maybe storage state

* When user presses “Back to list” OR clicks an explicit “Archive” button (your call):

  * if gdrive: move file to archive folder
  * if local: move file to archive dir

(We can keep this optional if you want a safer first release.)

---

# What we do next (Task 1)

We start with **Task 1: update `storage/collector_store.py` to support `id` + `origin`**.

To keep this one-task-per-response, paste **just** your current `storage/collector_store.py` (or at least the parts with `load_candidates_file()` and `save_candidates_json()`), and I’ll return a drop-in replacement for that file (or a small patch) implementing Task 1 only.



=======================
=======================
=======================

Good time to pause and take stock. You’ve already done the **hard architectural shift**: moving from two parallel pipelines (web + doc) to a **single canonical candidate model**. That was the risky part. Now the remaining work is mostly **cleanup, consolidation, and a few functional gaps**.

Below is a clear checklist of what remains from the milestone we started.

---

# Milestone: Unified Candidate + Unified Curate Pipeline

Goal:
**One candidate list → one curate UI → one curation store → canonical IDs**

---

# ✅ Completed

These pieces are already working based on your last messages.

### 1. Canonical content IDs

You now use:

```
web:https://...
gdrive:<docid>
```

Used by:

* candidates list
* curate route
* curation.yaml

This eliminates the old `doc_id` vs `url` split.

---

### 2. Unified candidate list

Your UI now shows **web + doc candidates together**.

This required:

```
ui_from_web_candidate()
ui_from_doc_candidate()
```

Both produce:

```
UICandidate(
    url=content_id
    open_url=...
    title=...
    source=...
)
```

Correct.

---

### 3. Curate entry point unified

You now use:

```
/curate?id=<content_id>
```

instead of

```
/curate/<idx>
/curate_doc?doc_id=
```

This was the biggest routing change.

---

### 4. Canonical keys in curation.yaml

You confirmed entries like:

```
web:https://www.tsl.texas.gov/node/70520:
  final_blurb: ...
```

That’s exactly the correct direction.

---

### 5. UI cleanup

You fixed the layout so:

* One **Article Candidates card**
* Rows for each candidate

---

# ⚠️ Remaining Functional Work

These are the things still left to fully complete the milestone.

---

# 1. Finish `build_view_by_content_id()`

This service must fully replace:

```
build_view_by_index()
build_view_by_doc_id()
```

It should handle:

```
web:
   fetch + clean article
   build CurateView

gdrive:
   load doc candidate
   construct cleaned dict
   build CurateView
```

Right now this is partially implemented.

---

# 2. Remove `/curate/<idx>` route

If it still exists anywhere:

```
router.get("/curate/<idx>")
```

Remove it.

You want **only**:

```
/curate?id=<content_id>
```

---

# 3. Delete doc-curate pipeline

Once docs open successfully in the unified curate screen, delete:

```
routes/curate_doc.py
services/curate_doc_service.py
templates/curate_doc.html
```

and remove route registrations.

You already started this discussion.

---

# 4. Remove watcher shim

You asked about this earlier.

Delete:

```
watcher.py
```

and update imports to:

```
watch.runtime
watch.scan
```

---

# 5. Simplify `templates.html_page()`

Right now you temporarily added compatibility parameters.

Eventually remove:

```
doc_candidates
has_blurb_by_docid
has_image_by_docid
```

so it becomes:

```
html_page(
    candidates,
    prechecked,
    subject,
    intro,
    status,
    has_blurb_by_url,
    has_image_by_url,
    candidate_ids,
)
```

---

# 6. Normalize doc candidate IDs

You already hit this error:

```
Doc not found: 174V1bg...
```

The fix is to ensure:

```
docsys.store.load_doc_candidates()
```

returns **raw IDs only**, and canonicalization happens only in the UI/service layer.

---

# 7. Remove legacy candidate persistence

You earlier had two candidate files:

```
candidates.json
doc_candidates.json
```

Now you only want:

```
candidates_latest.json
```

Confirm that:

```
routes/candidates.py
services
collect
```

no longer reference doc candidates separately.

---

# 8. Clean up import graph

You started doing this.

Check for dead modules:

```
rg -n "curate_doc"
rg -n "doc_candidates"
rg -n "watcher"
```

Then remove them.

---

# 9. Verify POST actions work for docs

These routes must work for **both web and gdrive** IDs:

```
post_curate_add_excerpt
post_curate_pop_excerpt
post_curate_clear_excerpts
post_curate_compose_blurb
post_curate_save
```

All should store under:

```
content_id
```

not `doc_id`.

---

# 10. Remove index dependence in CurateView

Right now CurateView includes:

```
idx
total
```

Eventually navigation should be based on **content_id ordering**, not index.

This is optional for this milestone.

---

# Optional Improvements (recommended but not required)

These will simplify your codebase further.

### A. Move canonical ID helpers into dedicated module

```
services/content_ids.py
```

Functions:

```
canonical_content_id()
real_web_url()
is_web_id()
is_doc_id()
```

---

### B. Split candidates logic

Right now `routes/candidates.py` is getting big again.

Consider:

```
services/candidate_service.py
```

for:

```
load_persisted_candidates()
normalize_candidates()
merge_doc_candidates()
```

---

### C. Add type for candidates

Instead of `dict[str,Any]` everywhere.

```
@dataclass
class Candidate
```

---

# Rough Completion Estimate

| Area                          | Status |
| ----------------------------- | ------ |
| Canonical IDs                 | ✅      |
| Unified candidate list        | ✅      |
| Unified curate route          | ⚠️ 90% |
| Doc pipeline removal          | ⚠️     |
| Watcher shim removal          | ⚠️     |
| Legacy candidate code cleanup | ⚠️     |
| Import graph cleanup          | ⚠️     |

You're **about 80–85% through the milestone**.

---

# If you'd like, I can also show you

A **very effective next step** for this repo:

> **A 5-file cleanup that will remove ~600–900 lines of dead code immediately.**

It’s the fastest way to make the codebase dramatically easier to navigate before we move to the next milestone (watch scanning + scoring improvements).


==================
==================

TSLAC Newsletter Helper – Project Context Header

Project Name: TSLAC Newsletter Helper
Repo: https://github.com/dweilert/tslac
Repo Branch: refactor/http-router

Runtime: Custom Python web app (custom web/router, not Flask/Django)
Python Version: 3.12
Architecture Style: Routes → Services → Storage → Templates
Rendering: Server-side templates (render() helper)
Data Storage: YAML + JSON files in local filesystem
 
-- Architecture Overview. --

Routing Layer
- web/router.py
- routes/candidates.py
- routes/curate_article.py
- routes/config.py
- routes/watch.py (being deprecated)

Services Layer
- services/candidates_service.py
- services/curate_article_service.py
- services/watch_service.py
- services/api_service.py

Storage Layer
- storage/collector_store.py
- storage/curation_store.py
- storage/selected_store.py
- watch_store.py

Scraping / Collection
- collect/collector.py
- collect/rules.py
- watch/scan.py
- watch/fetch.py
- watch/parse.py
- watch/score.py


Milestone 2 Objectives:


These are the things still left to fully complete the milestone.

1. Finish build_view_by_content_id()

This service must fully replace:

build_view_by_index()
build_view_by_doc_id()

It should handle:

web:
   fetch + clean article
   build CurateView

gdrive:
   load doc candidate
   construct cleaned dict
   build CurateView

Right now this is partially implemented.

2. Remove /curate/<idx> route

If it still exists anywhere:

router.get("/curate/<idx>")

Remove it.

You want only:

/curate?id=<content_id>
3. Delete doc-curate pipeline

Once docs open successfully in the unified curate screen, delete:

routes/curate_doc.py
services/curate_doc_service.py
templates/curate_doc.html

and remove route registrations.

You already started this discussion.

4. Remove watcher shim

You asked about this earlier.

Delete:

watcher.py

and update imports to:

watch.runtime
watch.scan
5. Simplify templates.html_page()

Right now you temporarily added compatibility parameters.

Eventually remove:

doc_candidates
has_blurb_by_docid
has_image_by_docid

so it becomes:

html_page(
    candidates,
    prechecked,
    subject,
    intro,
    status,
    has_blurb_by_url,
    has_image_by_url,
    candidate_ids,
)
6. Normalize doc candidate IDs

You already hit this error:

Doc not found: 174V1bg...

The fix is to ensure:

docsys.store.load_doc_candidates()

returns raw IDs only, and canonicalization happens only in the UI/service layer.

7. Remove legacy candidate persistence

You earlier had two candidate files:

candidates.json
doc_candidates.json

Now you only want:

candidates_latest.json

Confirm that:

routes/candidates.py
services
collect

no longer reference doc candidates separately.

8. Clean up import graph

You started doing this.

Check for dead modules:

rg -n "curate_doc"
rg -n "doc_candidates"
rg -n "watcher"

Then remove them.

9. Verify POST actions work for docs

These routes must work for both web and gdrive IDs:

post_curate_add_excerpt
post_curate_pop_excerpt
post_curate_clear_excerpts
post_curate_compose_blurb
post_curate_save

All should store under:

content_id

not doc_id.

10. Remove index dependence in CurateView

Right now CurateView includes:

idx
total

Eventually navigation should be based on content_id ordering, not index.

This is optional for this milestone.

Optional Improvements (recommended but not required)

These will simplify your codebase further.

A. Move canonical ID helpers into dedicated module
services/content_ids.py

Functions:

canonical_content_id()
real_web_url()
is_web_id()
is_doc_id()
B. Split candidates logic

Right now routes/candidates.py is getting big again.

Consider:

services/candidate_service.py

for:

load_persisted_candidates()
normalize_candidates()
merge_doc_candidates()
C. Add type for candidates

Instead of dict[str,Any] everywhere.

@dataclass
class Candidate
Rough Completion Estimate
Area	Status
Canonical IDs	✅
Unified candidate list	✅
Unified curate route	⚠️ 90%
Doc pipeline removal	⚠️
Watcher shim removal	⚠️
Legacy candidate code cleanup	⚠️
Import graph cleanup	⚠️

You're about 80–85% through the milestone.


===============================
===============================


TSLAC Newsletter Helper – Project Context Header

Project Name: TSLAC Newsletter Helper
Repo: https://github.com/dweilert/tslac
Repo Branch: refactor/http-router

Runtime: Custom Python web app (custom web/router, not Flask/Django)
Python Version: 3.12
Architecture Style: Routes → Services → Storage → Templates
Rendering: Server-side templates (render() helper)
Data Storage: YAML + JSON files in local filesystem
 
-- Architecture Overview. --

Routing Layer
- web/router.py
- routes/candidates.py
- routes/curate_article.py
- routes/config.py
- routes/watch.py (being deprecated)

Services Layer
- services/candidates_service.py
- services/curate_article_service.py
- services/watch_service.py
- services/api_service.py

Storage Layer
- storage/collector_store.py
- storage/curation_store.py
- storage/selected_store.py
- watch_store.py

Scraping / Collection
- collect/collector.py
- collect/rules.py
- watch/scan.py
- watch/fetch.py
- watch/parse.py
- watch/score.py

Milestone 3:

Ensure that when the Refresh button in the Main page is pressed the application is accessing the defined g-drive and updating any locally stored information.  This process would compare the application stored information with the latest information in the defined g-drive.  If new information is located the local storage should be updated with the latest information.

One of the main goals for this project is to improve the user interface focus on implementing enhancements and changes in the UI. 
Changes to include:

Main/Home page

- Separate each source category into separate cards that provides a visual grouping or box for each category.

- Add Source Category labels to each card.

- Replace DOC badge with GDRIVE and LOCAL badges as appropriate.

- Repair hide/show of source cateagories when the associated checkbox is toggled.

Curate page

- Replace existing Article content area with TinyMCE editor

- Add a review button that will show the content and the selected image, if selected.  Use of a modal for this would be a preferred method to display the preview.  If this is significant change, please consider opening a new tab for the preview.

- If the source of selected candidate article being curated is from gdrive or local the content from the document should be shown in the curate 'Source content' area.  Images located should be shown in the 'Detected images' section


- Lets clarify that when the Refresh button is pressed it checks web and gdrive/doc sources not just one or the other.
- TinyMCE from CDN is fine.
- Processing of documents from gdrive needs to support PDF, Word, Plan text, and G-Documents at a minimum.
- Saving of content that is in the TinyMCE edit area can be saved as html, but must be saved in the file that contains the information about the article for later use.