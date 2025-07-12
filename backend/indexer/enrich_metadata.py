"""enrich_metadata.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Part of the *Demo* pipeline.  Given the landing‐page URL of a document on
SSOAR, this module extracts structured metadata, enriches it with light NLP
(LLM‑based country extraction + 1‑2 sentence abstract summary) and returns a
Python dict ready for indexing or serialisation.

Main entry points
-----------------
>>> metadata, pdf_url = extract_metadata_from_page(url)
    • Used programmatically by *build_index.py*

$ python enrich_metadata.py <document_url>
    • CLI helper: writes the resulting JSON file to backend/data/final/

Key enrichments
~~~~~~~~~~~~~~~
* **Location extraction** – Calls ``geo_locator.extract_locations_from_text``
  which delegates to an OpenAI chat model to return country‑level mentions with
  lat/lon.
* **Abstract summary** – Calls ``summarizer.summarize_text`` for a concise
  1‑2 sentence overview suitable for search result snippets.
* **PDF link resolution** – Robust helper ``get_pdf_download_link`` handles
  redirects and icon links to find a usable *.pdf* URL.

Dependencies: requests · beautifulsoup4 · openai (transitively via helpers)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import sys
import json
import re
from typing import Tuple, Dict, Any, List, Optional

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .geo_locator import extract_locations_from_text
from .summarizer import summarize_text

###############################################################################
# Constants & HTTP headers                                                    #
###############################################################################

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SSOAR-Metadata-Enricher/1.0)"
}
BASE_DOMAIN = "https://www.ssoar.info"

###############################################################################
# Helper: robust PDF link discovery                                           #
###############################################################################

def get_pdf_download_link(soup: BeautifulSoup) -> Optional[str]:
    """Return the absolute URL of the *first* PDF link found on an SSOAR
    landing page *or* on its outgoing redirect page.

    Strategy
    --------
    1. Look for an ``<a>`` whose visible text contains *Download full text*.
    2. If that anchor points directly to *.pdf* → return it.
    3. Else fetch the anchor's target page, search there for a *.pdf* link.
    4. Fallback: find the legacy PDF icon  ``<img alt="Download PDF">``.
    5. Return *None* if nothing is found or any network error occurs.
    """
    # 1. Primary anchor with visible text
    anchor = soup.find(
        "a",
        string=lambda t: t and re.search(r"download\s+full\s+text", t, re.I)
    )
    if anchor and anchor.has_attr("href"):
        href = anchor["href"]
        if not href.startswith("http"):
            href = f"{BASE_DOMAIN}{href}"

        # Direct PDF
        if href.lower().endswith(".pdf"):
            return href

        # Otherwise follow the intermediate HTML page once (robust but cheap)
        try:
            redirected_page = requests.get(href, timeout=10)
            redirected_soup = BeautifulSoup(redirected_page.content, "html.parser")
            pdf_link = redirected_soup.find("a", href=re.compile(r"\.pdf$", re.I))
            if pdf_link and pdf_link.has_attr("href"):
                pdf_href = pdf_link["href"]
                return pdf_href if pdf_href.startswith("http") else urljoin(href, pdf_href)
        except requests.RequestException as exc:
            print(f"[WARN] Could not resolve intermediate PDF link: {exc}")

    # 2. Legacy icon path
    img_tag = soup.find("img", alt=re.compile(r"download pdf", re.I))
    if img_tag and img_tag.parent.name == "a" and img_tag.parent.has_attr("href"):
        href = img_tag.parent["href"]
        return href if href.startswith("http") else f"{BASE_DOMAIN}{href}"

    return None

###############################################################################
# Core scraping / enrichment routine                                          #
###############################################################################

def extract_metadata_from_page(url: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """Fetch *url*, scrape raw metadata, enrich with LLM helpers and return.

    Returns
    -------
    metadata : dict
        All structured fields ready for JSON serialisation or ES indexing.
    pdf_url : str | None
        Resolved PDF download URL (also included inside *metadata* for
        convenience).
    """
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    metadata: Dict[str, Any] = {"source_url": url}

    # ---- Basic Dublin Core meta tags -----------------------------------
    metadata["title"]    = soup.find("meta", {"name": "DC.title"})["content"]
    metadata["authors"]  = [m["content"] for m in soup.find_all("meta", {"name": "DC.creator"})]
    metadata["year"]     = soup.find("meta", {"name": "DCTERMS.issued"})["content"]
    metadata["abstract"] = soup.find("meta", {"name": "DCTERMS.abstract"})["content"]
    metadata["language"] = soup.find("meta", {"name": "DC.language"})["content"]

    metadata.update({
        "doi": None,
        "keywords": [],
        "pdf_url": None,
        "locations": [],
        "summary": None,
    })

    # ---- Keywords table (HTML) -----------------------------------------
    for label_span in soup.select("span.resourceDetailTableCellLabel"):
        if label_span.get_text(strip=True).lower() == "keywords":
            value_span = label_span.find_next("span", class_="resourceDetailTableCellValue")
            if value_span:
                metadata["keywords"] = [a.get_text(strip=True) for a in value_span.find_all("a")]
            break

    # ---- DOI -----------------------------------------------------------
    doi_tag = soup.find("a", href=True, string=lambda t: t and "doi.org" in t)
    if doi_tag:
        metadata["doi"] = doi_tag["href"]

    # ---- PDF link -------------------------------------------------------
    metadata["pdf_url"] = get_pdf_download_link(soup)

    # ---- Enrichments (LLM helpers) --------------------------------------
    if metadata["abstract"]:
        metadata["locations"] = extract_locations_from_text(metadata["abstract"])
        metadata["summary"]   = summarize_text(metadata["abstract"])

    return metadata, metadata["pdf_url"]

###############################################################################
# Public helper for importers                                                 #
###############################################################################

def enrich_metadata(url: str) -> Dict[str, Any]:
    """Thin wrapper that discards the *pdf_url* convenience return value."""
    return extract_metadata_from_page(url)[0]

###############################################################################
# CLI usage: python enrich_metadata.py <document_url>                          #
###############################################################################

if __name__ == "__main__":
    from pathlib import Path

    if len(sys.argv) != 2:
        print("Usage: python enrich_metadata.py <document_url>")
        sys.exit(1)

    FINAL_DIR = Path("backend/data/final")
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    url = sys.argv[1]
    metadata, _ = extract_metadata_from_page(url)
    doc_id = url.rstrip("/").split("/")[-1]
    out_path = FINAL_DIR / f"{doc_id}.json"

    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, ensure_ascii=False, indent=2)
    print(f"✅  Metadata saved → {out_path}")