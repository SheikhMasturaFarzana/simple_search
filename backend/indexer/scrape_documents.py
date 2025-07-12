"""scrape_documents.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tiny web‑scraper that collects a list of SSOAR document landing‑page URLs from
a pre‑defined search results page (10 by default).  Acts as the first stage of
the demo pipeline: downstream modules fetch metadata & PDFs from each URL.

Public helper
-------------
>>> get_document_urls(BASE_SEARCH_URL, limit=10) -> List[str]

The script can also be run standalone from the shell to print the discovered
links.
"""

from typing import List
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE_SEARCH_URL = (
    "https://www.ssoar.info/ssoar/discover?scope=%2F&query=democracy+germany+migrant"
)
BASE_DOMAIN = "https://www.ssoar.info"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Demo-Scraper/1.0)"
}

# ---------------------------------------------------------------------------
# Core scraper
# ---------------------------------------------------------------------------

def get_document_urls(base_search_url: str, limit: int = 10) -> List[str]:
    """Return up to *limit* unique landing‑page URLs from the SSOAR search.

    Parameters
    ----------
    base_search_url : str
        A fully assembled search‑results URL on ssoar.info.
    limit : int, optional
        Max number of unique document URLs to return (default 10).
    """
    resp = requests.get(base_search_url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    doc_urls: List[str] = []
    for a in soup.select("a[href^='/ssoar/handle/document/']"):
        full_url = urljoin(BASE_DOMAIN, a["href"])
        if full_url not in doc_urls:
            doc_urls.append(full_url)
        if len(doc_urls) >= limit:
            break
    return doc_urls

# ---------------------------------------------------------------------------
# CLI helper
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    urls = get_document_urls(BASE_SEARCH_URL)
    print("\nDiscovered document URLs:\n")
    for url in urls:
        print("-", url)
    print(f"\nTotal: {len(urls)} document URLs found.")