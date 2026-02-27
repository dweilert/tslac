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
