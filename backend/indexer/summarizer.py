"""
summarizer.py  – Return a 1-2 sentence summary of an abstract.

Usage inside code:
    from summarizer import summarize_text
    summary = summarize_text(abstract)
"""

import os
import openai

# -------------------------------------------------
# 1) Supply your key (env-var is cleaner for CI)
# -------------------------------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------------------------------
# 2) Main function
# -------------------------------------------------
def summarize_text(text: str) -> str:
    """
    Summarise `text` in ≤ 2 sentences (≈ ≤ 40 words).
    Returns an empty string on failure.
    """
    if not text.strip():
        return ""
    
    prompt = (
        "Summarise the following abstract in no more than TWO sentences "
        "(about 40 words total). Use plain language.\n\n"
        "Provide summary in input language.\n"
        f"Abstract:\n{text}\n\nSummary:"
    )

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            temperature=0.3,
            max_tokens=80,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[ERROR] OpenAI summariser failed: {e}")
        return ""


# -------------------------------------------------
# 3) CLI quick-check
# -------------------------------------------------
if __name__ == "__main__":
    demo = (
        "This paper analyses migration policy reforms in Germany and France "
        "between 2015-2023, highlighting the role of civic integration "
        "programmes and labour-market demand in shaping admission criteria."
    )
    print(summarize_text(demo))
