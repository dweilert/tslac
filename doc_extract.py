from __future__ import annotations
import io
import os
from typing import Optional
from bs4 import BeautifulSoup
from striprtf.striprtf import rtf_to_text
from docx import Document
from pypdf import PdfReader


def _ext(filename: str) -> str:
    return os.path.splitext(filename.lower())[1]


def extract_text(filename: str, mime_type: Optional[str], data: bytes) -> str:
    ext = _ext(filename)

    # Plain text
    if ext in [".txt"]:
        return data.decode("utf-8", errors="replace")

    # HTML
    if ext in [".html", ".htm"] or (mime_type or "").startswith("text/html"):
        html = data.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text("\n", strip=True)

    # RTF
    if ext in [".rtf"] or (mime_type or "") in ["application/rtf", "text/rtf"]:
        text = data.decode("utf-8", errors="replace")
        return rtf_to_text(text)

    # DOCX
    if ext in [".docx"] or (mime_type or "") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(parts)

    # PDF
    if ext in [".pdf"] or (mime_type or "") == "application/pdf":
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for p in reader.pages:
            t = p.extract_text() or ""
            if t.strip():
                pages.append(t.strip())
        return "\n\n".join(pages)

    # Fallback: try utf-8 decode
    return data.decode("utf-8", errors="replace")