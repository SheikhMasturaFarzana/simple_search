**Note:** This demo was developed as part of an interview assignment. It meets all specified requirements. For more details, please refer to the attached PowerPoint slide. The entire implementation was completed in approximately four hours of programming time.
## Demo – End-to-End Document Search

A lightweight pipeline that

1. **Crawls** 10 social-science papers from SSOAR  
2. **Enriches** each record with  
   * Dublin-Core metadata  
   * country-level geo-tags (OpenAI)  
   * a 1-2-sentence abstract summary (OpenAI)  
3. **Stores** per-document JSON in `data/final/` and (optionally) raw PDF text in `data/raw/`  
4. **Indexes** the enriched JSON into **Elasticsearch** (`app_demo` index)  
5. **Serves** a blue-accented **Streamlit** UI with query + facet filters  

---
## Folder layout
```
backend/
│
├─ indexer/                  # single-purpose helpers
│   ├─ scrape\_documents.py       ← collect landing-page URLs
│   ├─ enrich\_metadata.py        ← scrape meta + geo + summary
│   ├─ geo\_locator.py            ← LLM location (country) extractor
│   ├─ summarizer.py             ← LLM 2-line summariser
│   └─ pdf\_parser.py             ← download/parse PDF (optional)
│
├─ build\_index.py            # crawl ➜ enrich ➜ save JSON/TXT
└─ elastic\_index.py          # bulk-load JSON → Elasticsearch
ui/
└─ app.py                    # Streamlit front-end
data/
├─ final/                    # <docid>.json  (enriched)
└─ raw/                      # <docid>.txt   (optional full text)
logs/
└─ build\_index.log           # pipeline log
requirements.txt
README.md
````
## Quick start

```bash
# 1️⃣  environment
conda create -n web_app python=3.11 -y
conda activate web_app
pip install -r requirements.txt

# 2️⃣  crawl + enrich 10 docs → data/final/
python backend/build_index.py

# 3️⃣  Elasticsearch 8.x (dev, no security)
cd elasticsearch\bin 
.\elasticsearch.bat
# starts elasticsearch

# 4️⃣  bulk-index JSON → ES
python backend/elastic_index.py            `
# creates index 'app_demo'

# 5️⃣  launch UI
streamlit run ui/app.py
````
````
Open **[http://localhost:8501](http://localhost:8501)** → type a query such as **“migration Germany”**, refine with sidebar facets (Year / Language / Author / Country), click a title to open the PDF.
````

---

## How it works

| Stage                   | Script                | Notes                                                                                                 |
| ----------------------- | --------------------- | ----------------------------------------------------------------------------------------------------- |
| **Crawl**               | `scrape_documents.py` | Pulls first 10 landing-page URLs from a fixed SSOAR search results page.                              |
| **Enrich**              | `enrich_metadata.py`  | BeautifulSoup + OpenAI → title, authors, year, abstract, keywords, PDF-URL, `locations[]`, `summary`. |
| **Raw text (optional)** | `pdf_parser.py`       | Downloads the PDF and extracts text with PyPDF2.                                                      |
| **Persist**             | `build_index.py`      | Writes `data/final/<id>.json` and `data/raw/<id>.txt`.                                                |
| **Index**               | `elastic_index.py`    | Creates `app_demo` mapping and bulk-loads JSON.                                                       |
| **UI**                  | `ui/app.py`           | Streamlit; boosts `abstract^3` (BM25), shows top-5 hits and keyword chips with filters.               |

---

## Requirements

* **Python ≥ 3.9**
  `beautifulsoup4  requests  tqdm  PyPDF2  openai  elasticsearch  streamlit`
* **Elasticsearch 8.x** (single-node is fine; security disabled for local dev)
* **OpenAI API key** in `OPENAI_API_KEY` env-var for geo-tagging & summarization.

---

## Limitations & roadmap

* **PDF parsing** is best-effort; scanned/complex PDFs may yield no text. The quality of raw text parsed from pdf is not of good quality and needs considerable effort to clean.
* Search covers **title, abstract, summary** only – full text stored but ignored at the moment.
* OpenAI calls can be swapped for local models (e.g. Mistral-7B via LM Studio).
* Fixed 10-document crawl – expandable with pagination + scheduler.
* Future: Enchance flexibility, metadata extraction from PDF, Knowledge Graph plus RAG, result summary.
---
