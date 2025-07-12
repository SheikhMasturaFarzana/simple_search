"""elastic_index.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Bulk‑index the enriched JSON files in *data/final* into an Elasticsearch index.
Only abstract‑level text is indexed for this demo; full PDF text is ignored for
now but could be added as another `text` field later.

Usage
-----
(web_app) python backend/elastic_index.py

Prerequisites: Elasticsearch running on localhost:9200 (security disabled for
local dev) and `pip install elasticsearch tqdm`.
"""

from pathlib import Path
import json
import re
import requests
from tqdm import tqdm
from elasticsearch import Elasticsearch, helpers

# ── 1.  Connect ──────────────────────────────────────────────────────────
ES_HOST = "http://localhost:9200"  # adjust if needed
INDEX    = "app_demo"              # index name used by the UI

es = Elasticsearch(ES_HOST)

# ── 2.  Create index & mapping (runs once) ───────────────────────────────
if not es.indices.exists(index=INDEX):
    es.indices.create(
        index=INDEX,
        body={
            "mappings": {
                "properties": {
                    "title":    {"type": "text"},
                    "abstract": {"type": "text"},
                    "summary":  {"type": "text"},
                    "keywords": {"type": "keyword"},
                    "year":     {"type": "keyword"},
                    "language": {"type": "keyword"},
                    "authors":  {"type": "keyword"},
                    "country":  {"type": "keyword"},  # list of country codes
                    "pdf_url":  {"type": "keyword"},
                }
            }
        },
    )
    print(f"✅  Created index {INDEX}")
else:
    print(f"ℹ️  Index {INDEX} already exists")

# ── 3.  Helper to resolve PDF URL if not already in JSON ────────────────
PDF_LINK_RE = re.compile(r"\.pdf$", re.I)

def resolve_pdf_url(meta: dict) -> str:
    """Return `meta['pdf_url']` if present; otherwise scrape landing page once."""
    if meta.get("pdf_url"):
        return meta["pdf_url"]

    try:
        resp = requests.get(meta["source_url"], timeout=8)
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.content, "html.parser")
        a = soup.find("a", href=PDF_LINK_RE)
        if a and a.has_attr("href"):
            href = a["href"]
            return href if href.startswith("http") else f"https://www.ssoar.info{href}"
    except Exception:
        pass
    return meta["source_url"]  # fallback to landing page

# ── 4.  Build bulk actions ------------------------------------------------
FINAL_DIR = Path("data/final")
actions = []

for path in tqdm(list(FINAL_DIR.glob("*.json")), desc="Collecting docs"):
    meta = json.loads(path.read_text(encoding="utf-8"))
    actions.append({
        "_index": INDEX,
        "_id":    path.stem,
        "_source": {
            "title":    meta.get("title"),
            "abstract": meta.get("abstract"),
            "summary":  meta.get("summary"),
            "keywords": meta.get("keywords", []),
            "year":     meta.get("year"),
            "language": meta.get("language"),
            "authors":  meta.get("authors", []),
            "country":  [loc.get("location", "") for loc in meta.get("locations", [])],
            "pdf_url":  resolve_pdf_url(meta),
        }
    })

# ── 5.  Bulk index --------------------------------------------------------
helpers.bulk(es, actions)
print(f"✅  Indexed {len(actions)} documents into {INDEX}")