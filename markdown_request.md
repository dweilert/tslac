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
