"""build_index.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pipeline orchestrator that glues the individual stages together:

1. **URL crawl** – `get_document_urls()` fetches up to *N* landing‑page links
   from a pre‑defined SSOAR search results page.
2. **Metadata enrichment** – `enrich_metadata()` scrapes Dublin‑Core meta‑
   data, extracts country mentions with an LLM, creates a 1‑2‑sentence
   abstract summary, and discovers the best PDF download URL.
3. **PDF text extraction** – `extract_pdf_text()` downloads the PDF and pulls
   its plain text (PyPDF2).  Saved for future dense‑vector indexing, but **not
   used by the current demo UI**.
4. **Persistence** – writes two artefacts per document:
   * `data/final/<doc_id>.json` – enriched metadata (ready for Elasticsearch)
   * `data/raw/<doc_id>.txt`   – raw full‑text (optional)

The script also emits progress to both **STDOUT** (via tqdm) and a rotating
log file `logs/build_index.log` so you can inspect failures later.

Run once before `index_to_es.py`:
>>> python backend/build_index.py
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from tqdm import tqdm

from indexer.scrape_documents import BASE_SEARCH_URL, get_document_urls
from indexer.enrich_metadata   import enrich_metadata
from indexer.pdf_parser        import extract_pdf_text

# ── I/O folders ----------------------------------------------------------
FINAL_DIR = Path("data/final")   # enriched JSON one‑file‑per‑doc
RAW_DIR   = Path("data/raw")    # extracted PDF text (optional)
LOG_DIR   = Path("logs")
for d in (FINAL_DIR, RAW_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── Logging --------------------------------------------------------------
logging.basicConfig(
    filename=LOG_DIR / "build_index.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ── Helper ---------------------------------------------------------------

def _doc_id_from(url: str) -> str:
    """Return trailing segment of `/handle/document/<id>` URL."""
    return url.rstrip("/").split("/")[-1]


# ── Main pipeline --------------------------------------------------------

def build_index(limit: int = 10) -> None:
    """Crawl `limit` docs → enrich → save JSON & txt."""
    logger.info("Starting build_index – limit=%s", limit)
    print("[INFO] Fetching document links…")

    # 1) Crawl landing‑page URLs
    doc_urls = get_document_urls(BASE_SEARCH_URL, limit=limit)
    logger.info("%d document URLs fetched", len(doc_urls))

    # 2) Loop through each URL
    for url in tqdm(doc_urls, desc="Processing documents"):
        doc_id = _doc_id_from(url)
        pdf_url: str | None = None

        # 2a. Metadata enrichment
        try:
            metadata, pdf_url = enrich_metadata(url)
            out_json = FINAL_DIR / f"{doc_id}.json"
            out_json.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("Metadata saved → %s", out_json)
        except Exception as exc:  # pragma: no cover – broad catch is fine for pipeline
            logger.exception("Metadata enrichment failed for %s: %s", doc_id, exc)
            continue

        # 2b. PDF full‑text extraction (optional)
        try:
            if pdf_url:
                txt = extract_pdf_text(pdf_url)
                (RAW_DIR / f"{doc_id}.txt").write_text(txt, encoding="utf-8")
                logger.info("Raw text saved for %s (%d chars)", doc_id, len(txt))
        except Exception as exc:
            logger.exception("PDF extraction failed for %s: %s", doc_id, exc)

    print("\n[✓] Done – see logs/build_index.log for details")
    logger.info("Indexing complete")


# ── CLI ------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Crawl + enrich + extract PDF text")
    parser.add_argument("--limit", type=int, default=10, help="Number of docs to process (default: 10)")
    args = parser.parse_args()

    build_index(limit=args.limit)