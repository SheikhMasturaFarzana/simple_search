"""geo_locator.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Light‑weight wrapper around the OpenAI chat‑completion API that extracts only
**country‑level** locations from an arbitrary piece of text.  Designed for the
pipeline's enrichment step where we only need a coarse geographic signal
(Germany, France, …) to drive simple country facets.

Public function
---------------
>>> extract_locations_from_text(abstract) -> List[dict]

*   Returns a list of dictionaries, each with: `location` (English country
    name), `lat`, `lon`, `country_code` (ISO‑2).
*   If no countries are detected, an **empty list** is returned—never `None`.
*   Duplicate mentions are collapsed; German country names are normalised to
    English ("Deutschland" → "Germany").

Environment
-----------
Set an `OPENAI_API_KEY` env‑var **or** replace the placeholder in the file.
The default model is `gpt‑3.5‑turbo` with temperature 0 for deterministic
output.
"""

import os
import json
import openai

# -------------------------------------------------
# 1) Set your key in an env-var or paste it here
# -------------------------------------------------
openai.api_key =  "your_key"

# -------------------------------------------------
# 2) Main extractor
# -------------------------------------------------
def extract_locations_from_text(text: str):
    """
    Returns a list of dicts like
    [
      {"location": "Germany", "lat": 51.1657, "lon": 10.4515, "country_code": "DE"},
      ...
    ]
    If none found → empty list.
    """
    prompt = (
        "Extract a list of countries mentioned in the text below. "
        "For each country, return a JSON object with: "
        "location (country name), lat, lon, country_code (ISO-2). "
        "if the country names are in German, return the English name and respective coordinates. "
        "If a country is mentioned multiple times, return it only once. "
        "Return *only* a JSON list. If no countries, return [].\n\n"
        f"Text:\n{text}\n\nCountries:"
    )

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content.strip()

        # parse JSON safely
        try:
            data = json.loads(content)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            print("[WARN] GPT output was not valid JSON:\n", content)
            return []

    except Exception as e:
        print(f"[ERROR] OpenAI call failed: {e}")
        return []



