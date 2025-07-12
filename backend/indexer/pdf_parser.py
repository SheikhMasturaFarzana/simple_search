"""pdf_parser.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Utility for turning a remote PDF (given by its direct URL) into plain text
using **PyPDF2**.  The module purposefully stays minimal: we keep no local
cache and do not try OCR.  If PyPDF2 fails (scanned PDFs, complex layout) we
simply return an empty string; the caller can decide whether to fall back to a
more heavyweight parser later (PDFMiner, Tika, OCR).

Public helpers
--------------
>>> text = extract_pdf_text(pdf_url)
    # 1. Download → temp‑file
    # 2. PyPDF2 to extract all pages

*   Both helper functions return `""` when anything goes wrong; the pipeline
    can safely continue.
"""

from __future__ import annotations

import os
import re
import tempfile
from typing import Optional

import requests
import PyPDF2

__all__ = [
    "download_and_parse_pdf",
    "extract_pdf_text",
]


# ─────────────────────────────────────────────────────────────
# Core helpers
# ─────────────────────────────────────────────────────────────

def download_and_parse_pdf(pdf_url: str) -> str:
    """Download *pdf_url* into a temporary file and return its text.

    Parameters
    ----------
    pdf_url : str
        Direct link to a **.pdf** file.  The function performs a GET request,
        writes the bytes to an OS‑managed temp file, and then streams all pages
        via :pyclass:`PyPDF2.PdfReader`.

    Returns
    -------
    str
        Concatenated text of all pages, separated by newline, or an empty
        string on any failure (network error, invalid PDF, PyPDF2 extraction
        error).
    """
    try:
        response = requests.get(pdf_url, timeout=20)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        full_text: list[str] = []
        with open(tmp_path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            for page in reader.pages:
                page_txt = page.extract_text() or ""
                full_text.append(page_txt)

        os.remove(tmp_path)
        return "\n".join(full_text).strip()

    except Exception as exc:  # noqa: BLE001 – broad on purpose for pipeline
        print(f"[ERROR] Could not download or parse PDF: {exc}")
        return ""


def extract_pdf_text(pdf_url: str) -> str:
    """Validate *pdf_url* and delegate to :func:`download_and_parse_pdf`."""
    if not pdf_url:
        print("[WARN] Empty PDF URL provided – skipping.")
        return ""

    if not re.search(r"\.pdf$", pdf_url, re.I):
        print(f"[WARN] URL does not look like a PDF: {pdf_url}")
        # We still try; maybe it redirects to a PDF.

    return download_and_parse_pdf(pdf_url)