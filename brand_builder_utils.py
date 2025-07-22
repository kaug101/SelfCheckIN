import pdfplumber, streamlit as st, textwrap, json
from openai import OpenAI                        # already in requirements

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def extract_pdf_text(uploaded_pdf) -> str:
    """Return plain-text from a one-file `st.file_uploader` object."""
    with pdfplumber.open(uploaded_pdf) as pdf:
        pages = [page.extract_text() for page in pdf.pages]
    return "\n".join(p for p in pages if p).strip()

def build_prompt(resume_text: str) -> list[dict]:
    system = (
        "You are a senior personal-branding strategist.\n"
        "The user just uploaded their résumé / LinkedIn PDF.\n"
        "Analyse it and deliver:\n"
        "A) **exactly two** distinct expertise themes this person should amplify.\n"
        "B) A 90-day brand-building plan (bulleted).\n"
        "C) Two 5-line micro-articles (≈1–2 sentences per line) linking **news from the last 30 days** "
        "to each theme. Put any source URLs directly in the lines as Markdown links.\n\n"
        "Return **ONLY valid JSON** with this structure - nothing else:\n"
        "{\n"
        "  \"expertise\": [\n"
        "    \"<theme-1>\",\n"
        "    \"<theme-2>\"\n"
        "  ],\n"
        "  \"plan_90_days\": [            # 6–10 high-level bullets are enough\n"
        "    \"Week 1-2: …\",\n"
        "    \"Week 3-4: …\"\n"
        "  ],\n"
        "  \"micro_articles\": [          # one JSON object per theme\n"
        "    {\n"
        "      \"theme\": \"<theme-1>\",\n"
        "      \"article\": \"line 1\\nline 2\\nline 3\\nline 4\\nline 5\"\n"
        "    },\n"
        "    {\n"
        "      \"theme\": \"<theme-2>\",\n"
        "      \"article\": \"line 1\\nline 2\\nline 3\\nline 4\\nline 5\"\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": resume_text[:120_000]}   # O3 can handle 128 k, stay safe
    ]

def generate_brand_brief(resume_text: str) -> dict|None:
    """Call O3 once and return the parsed JSON, or None on error."""
    try:
        resp = client.chat.completions.create(
            model="o3",
            messages=build_prompt(resume_text),
            response_format={"type": "json_object"}  # guarantees pure-JSON output
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        st.error(f"⚠️ Brand-Builder error: {e}")
        return None
