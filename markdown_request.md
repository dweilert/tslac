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

## 3️⃣ Alternative: Ask For A Downloadable File

Even better for large documents:

> Generate the markdown file and provide it as a downloadable file.

That bypasses chat formatting entirely.

---

## 4️⃣ Why It Happened

Three technical causes:

1. Nested ``` fences terminate outer blocks
2. Chat rendering engine auto-formats markdown
3. Large responses sometimes get truncated unless explicitly requested “complete”

None of this was your fault. You asked correctly. The formatting layer is what bit us.

---

## 5️⃣ Your Cleanest Workflow Going Forward

Since you’re working with GitHub:

**Best pattern:**

1. Ask for document in raw markdown
2. Require four backtick wrapping
3. Paste directly into `DESIGN.md`
4. Commit

Or better:
5. Ask for downloadable `.md` file

---

# 🧠 Practical Advice

You’re building real software. Documentation is part of engineering discipline. When you want:

* Design docs
* API specs
* Architecture diagrams
* YAML-heavy documents

Always force a four-backtick outer fence.

---

You handled a frustrating stretch well. That cropping issue alone would’ve made most people quit.

If you want, next we can:

* Clean up the doc structure further
* Add a constant-contact export spec
* Or harden the architecture for future expansion

Your system is actually getting solid now.



---
flowchart TD
    Browser["Browser UI"]
    Server["server.py"]
    Watcher["watcher.py"]
    Preview["export_preview.py"]
    Store["store_state.py"]
    Files[("YAML / JSON Files")]
    Proxy["/img Proxy Endpoint"]
    External["External Websites"]

    Browser -->|HTTP Requests| Server
    Server --> Watcher
    Server --> Preview
    Server --> Store
    Server --> Proxy

    Watcher --> External
    Preview --> Store
    Store --> Files

    Proxy --> External
    Browser -->|Image Request| Proxy