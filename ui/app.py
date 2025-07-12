"""app.py (Streamlit front‑end)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Minimal search UI for the demo pipeline.  Connects to an Elasticsearch index
(`app_demo` by default), lets users query abstracts and refine results with
sidebar facets.  Shows at most five hits with the title linking directly to the
PDF, a two‑sentence summary, and any author‑supplied keywords.

Run locally with:
    (web_app) streamlit run ui/app.py

Elasticsearch must be running on ES_HOST and already contain documents (see
`backend/elastic_index.py`).

Key design notes
----------------
* Uses a **smaller h2** for the page title and **h4** for the result count to
  keep the layout compact.
* Facet values are cached for 5 minutes (`@st.cache_data`) to avoid hitting ES
  on every keystroke.
* Results are only requested when the user enters a query or selects at least
  one filter so the page loads blank.
* Abstract field is boosted 3×, title 1.5× in the BM25 query so relevance is
  driven primarily by the abstract.
"""
import streamlit as st
from elasticsearch import Elasticsearch

# ── Config ─────────────────────────────────────────────────
ES_HOST = "http://localhost:9200"
INDEX   = "app_demo"      # change if needed

es = Elasticsearch(ES_HOST)

st.set_page_config(page_title="Demo", page_icon="🔍", layout="wide")
PRIMARY_COLOR = "#0077b6"

st.markdown(f"<style>:root {{ --primary-color: {PRIMARY_COLOR}; }}</style>", unsafe_allow_html=True)

# Smaller title (h2) ------------------------------------------------------
st.markdown("<h2 style='color:#0077b6; margin-top:0'>Social Science Search</h2>", unsafe_allow_html=True)
query_text = st.text_input("Search the abstracts (e.g. 'migration Germany')", "")

# Helper to fetch facet values (always match_all to populate options)
@st.cache_data(ttl=300)
def fetch_facets():
    body = {
        "size": 0,
        "query": {"match_all": {}},
        "aggs": {
            "year":     {"terms": {"field": "year", "size": 50, "order": {"_key": "desc"}}},
            "language": {"terms": {"field": "language", "size": 20}},
            "author":   {"terms": {"field": "authors", "size": 50}},
            "country":  {"terms": {"field": "country", "size": 50}}
        }
    }
    return es.search(index=INDEX, body=body)["aggregations"]

facets = fetch_facets()

# Sidebar filters ----------------------------------------------------------
with st.sidebar:
    st.header("Filters")
    year_sel   = st.multiselect("Year",     options=[b["key"] for b in facets["year"]["buckets"]])
    lang_sel   = st.multiselect("Language", options=[b["key"] for b in facets["language"]["buckets"]])
    author_sel = st.multiselect("Author",   options=[b["key"] for b in facets["author"]["buckets"]])
    ctry_sel   = st.multiselect("Country",  options=[b["key"] for b in facets["country"]["buckets"]])

# Build ES bool query only if query or filters are provided -----------------
run_search = bool(query_text.strip()) or any([year_sel, lang_sel, author_sel, ctry_sel])

hits = []
if run_search:
    bool_query = {"bool": {"must": [], "filter": []}}

    if query_text.strip():
        bool_query["bool"]["must"].append({
            "multi_match": {
                "query":  query_text,
                "fields": ["abstract^3", "title^1.5", "summary"],
                "type":   "best_fields"
            }
        })
    else:
        bool_query["bool"]["must"].append({"match_all": {}})

    for field, sel in [
        ("year", year_sel), ("language", lang_sel),
        ("authors", author_sel), ("country", ctry_sel)
    ]:
        if sel:
            bool_query["bool"]["filter"].append({"terms": {field: sel}})

    search_body = {
        "size": 5,
        "query": bool_query,
        "_source": ["title", "summary", "keywords", "pdf_url"]
    }
    response = es.search(index=INDEX, body=search_body)
    hits = response["hits"]["hits"]

# Results heading (smaller h4) -------------------------------------------
st.markdown(
    f"<h4 style='margin-top:1.2em'>Results: {len(hits)} document{'s' if len(hits)!=1 else ''}</h4>",
    unsafe_allow_html=True)

if hits:
    for hit in hits:
        src = hit["_source"]
        title_link = f"[{src['title']}]({src['pdf_url']})"
        st.markdown(f"### {title_link}")
        st.write(src.get("summary", "No summary available."))
        if src.get("keywords"):
            st.markdown("*Keywords:* " + ", ".join(src["keywords"]))
        st.markdown("---")
else:
    if run_search:
        st.info("No results found.")
    else:
        st.write("Enter a query to start searching.")
