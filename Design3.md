````markdown
# Newsletter System — Document Source Integration Design
## Google Drive + Local File Support

**Project:** TSLAC Newsletter Builder  
**Feature:** Document Candidates from Google Drive and Local Folders  
**Author:** System Design Documentation  
**Status:** Implemented / Stabilizing  
**Last Updated:** 2026

---

# 1. Overview

The Newsletter Builder originally supported **web article sources only**.  
This feature extends the system to support **document-based newsletter content** originating from:

1. Google Drive folders
2. Local filesystem folders

Documents are automatically:

- Discovered
- Extracted
- Summarized using OpenAI
- Added to the Candidate Review UI
- Curated by an editor
- Included in newsletter preview and export

The system treats documents similarly to articles while preserving differences in storage and access behavior.

---

# 2. Goals

## Primary Goals

- Allow non-technical users to drop files into a folder.
- Automatically ingest documents into newsletter workflow.
- Support both cloud and offline workflows.
- Reuse existing curation pipeline.
- Maintain compatibility with existing article system.

## Secondary Goals

- Unified UI experience.
- Minimal schema changes.
- Fail-safe processing.
- Debuggable pipeline.

---

# 3. High-Level Architecture

```
Document Source
      │
      ▼
DocumentSource Interface
      │
      ▼
doc_pipeline.py
(Text Extraction + Summarization)
      │
      ▼
doc_store.py
(Persist Candidates)
      │
      ▼
Server UI
Candidate Review Page
      │
      ▼
Curate Document
      │
      ▼
state_store.py (curation.yaml)
      │
      ▼
Preview Builder
```

---

# 4. Core Concept: Document Sources

A **Document Source** abstracts where documents originate.

Supported sources:

| Source | Prefix | Example |
|------|------|------|
| Google Drive | `gdrive:` | `gdrive:1abcXYZ` |
| Local Folder | `local:` | `local:/docs/file.docx` |

These identifiers behave similarly to URLs in the rest of the system.

---

# 5. DocumentSource Interface

Located conceptually in:

```
document_source.py
```

```
class DocumentSource(ABC):

    def list_docs(self) -> list[DocRef]:
        """
        Discover documents available for processing.
        """

    def fetch_bytes(self, doc: DocRef) -> Tuple[bytes, str]:
        """
        Retrieve raw document bytes and mime type.
        """

    def archive_all(self) -> int:
        """
        Move processed documents to archive location.
        """
```

---

# 6. Implementations

## 6.1 Google Drive Source

File:
```
gdrive_source.py
```

Responsibilities:

- Authenticate using OAuth token.json
- Locate configured folders
- Enumerate files
- Download/export documents

### Folder Layout

```
Google Drive
 ├── tslac_input
 └── tslac_saved
```

Processing Flow:

```
tslac_input
   ↓
summarized
   ↓
tslac_saved
```

Supported MIME Types:

| Type | Handling |
|------|---------|
| Google Docs | export text |
| Word | direct download |
| Text | direct read |
| PDF | optional extraction |

---

## 6.2 Local Folder Source

File:
```
local_source.py
```

Example configuration:

```
DOC_SOURCE_MODE=local
DOC_INPUT_DIR=/Users/bob/tslac/input_docs
DOC_ARCHIVE_DIR=/Users/bob/tslac/archive_docs
```

Workflow mirrors Google Drive behavior.

---

# 7. Document Pipeline

File:
```
doc_pipeline.py
```

Pipeline stages:

## Stage 1 — Discovery

```
source.list_docs()
```

Produces:

```
DocRef
 ├── id
 ├── display_name
 ├── source
 └── metadata
```

---

## Stage 2 — Fetch

```
bytes, mime = fetch_bytes(doc)
```

---

## Stage 3 — Text Extraction

Extractor selected by MIME type.

Examples:

- TXT → direct decode
- DOCX → python-docx
- Google Docs → export text

---

## Stage 4 — Summarization

```
summary = summarize_document(text)
```

OpenAI produces editorial summary.

---

## Stage 5 — Candidate Creation

Stored as:

```
{
  "id": "gdrive:FILEID",
  "title": "...",
  "summary": "...",
  "source": "gdrive"
}
```

Saved via:

```
doc_store.save_doc_candidates()
```

---

# 8. Candidate Storage

File:
```
doc_store.py
```

Purpose:

Persistent cache separating discovery from UI rendering.

Functions:

```
load_doc_candidates()
save_doc_candidates()
clear_doc_candidates()
```

Why this exists:

- Avoid repeated OpenAI calls
- Improve UI responsiveness
- Enable debugging

---

# 9. UI Integration

## Candidate Review Page

Documents appear under:

```
Document Candidates
```

Each card includes:

- Title
- Summary
- Source
- Open Document
- Curate Button
- Selection Checkbox

Example ID:

```
gdrive:1VICkJFCZ0KjJ7FpW4laX_KD8xkpBP7J8
```

---

# 10. Document Curation

Route:

```
/curate_doc?doc_id=...
```

Template:

```
templates.curate_doc_page_html()
```

Editor may modify:

```
final_blurb
```

Submitted via:

```
POST /curate_doc/save
```

---

# 11. Curation Storage Model

Stored in:

```
curation.yaml
```

Structure:

```
gdrive:FILEID:
  final_blurb: Edited summary
  updated_at: timestamp
```

Managed by:

```
state_store.py
```

Key API:

```
upsert_curated_blurb()
get_curated_blurb()
```

---

# 12. Selection Model

Documents reuse existing schema.

```
selected.yaml
```

Example:

```
items:
  - url: https://example.com/article
  - url: gdrive:FILEID
```

No schema migration required.

---

# 13. Preview Rendering

File:
```
export_preview.py
```

Preview logic detects item type.

### Article
```
https://...
```

### Document
```
gdrive:
local:
```

Behavior differences:

| Feature | Article | Document |
|---|---|---|
| Image | Yes | Usually No |
| Crop | Yes | No |
| Read More | URL | Open Document |
| Source | Web | Drive/Local |

---

# 14. Document Opening

Route:

```
/doc/open?doc_id=
```

Responsibilities:

- Resolve source
- Stream file
- Redirect or download

Implementation varies by source.

---

# 15. Archiving

Button:

```
Archive Document Candidates
```

Calls:

```
DocumentSource.archive_all()
```

Moves processed docs out of intake folder.

Prevents duplication.

---

# 16. Debug Strategy

Recommended debug points:

### Discovery
```
Docs: building candidates
```

### Source Load
```
GDrive: found N files
```

### Extraction
```
Docs: extracted chars
```

### OpenAI
```
OpenAI: summarizing
```

### Save
```
DOC SAVE: doc_id=...
```

---

# 17. Configuration

Environment variables:

```
DOC_SOURCE_MODE=gdrive|local
OPENAI_API_KEY=
OPENAI_SUMMARY_MODEL=
```

Google Drive requires:

```
credentials.json
token.json
```

---

# 18. Failure Handling

System intentionally fails open.

| Failure | Behavior |
|---|---|
| OpenAI failure | placeholder summary |
| Extraction failure | skip doc |
| Missing doc | warning only |
| UI failure | redirect with status |

---

# 19. Data Flow Summary

```
Drop File
   ↓
Source Detect
   ↓
Fetch
   ↓
Extract Text
   ↓
OpenAI Summary
   ↓
Candidate Store
   ↓
UI Review
   ↓
Curate
   ↓
Save YAML
   ↓
Preview
   ↓
Export
```

---

# 20. Design Decisions

## Why IDs Instead of URLs
Documents lack public URLs.

Prefix system avoids schema changes.

---

## Why Cache Candidates
Prevents repeated AI cost.

---

## Why YAML Persistence
Human editable
Git friendly
Debuggable

---

# 21. Known Limitations

- Large PDFs may require streaming extraction
- No document image detection yet
- Archive operation not transactional
- Preview assumes curated summary exists

---

# 22. Future Enhancements

Planned improvements:

### Auto image extraction from documents
### Background ingestion worker
### Async summarization queue
### Multi-folder monitoring
### Duplicate detection
### Metadata tagging
### Incremental refresh

---

# 23. Recommended Next Evolution

Best architectural upgrade:

```
collector/
   sources/
      gdrive.py
      local.py
```

with plugin registration.

---

# 24. Operational Workflow

Editor workflow:

1. Drop files into Drive/local folder
2. Click Refresh Candidates
3. Review summaries
4. Click Curate
5. Edit summary
6. Save
7. Select item
8. Preview newsletter
9. Export

---

# 25. System Outcome

The newsletter system now supports:

✅ Web intelligence sources  
✅ Internal institutional documents  
✅ Cloud workflows  
✅ Offline workflows  
✅ AI-assisted editorial pipeline  

without changing the core newsletter architecture.

---

# END OF DOCUMENT
````
