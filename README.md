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

