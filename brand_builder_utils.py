import pdfplumber, streamlit as st, textwrap, json
from openai import OpenAI                        # already in requirements

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def extract_pdf_text(uploaded_pdf) -> str:
    """Return plain-text from a one-file `st.file_uploader` object."""
    with pdfplumber.open(uploaded_pdf) as pdf:
        pages = [page.extract_text() for page in pdf.pages]
    return "\n".join(p for p in pages if p).strip()

def build_prompt(resume_text: str) -> list[dict]:
   # brand_builder_utils.py  – inside build_prompt()
    system = (
        "You are a senior personal-branding strategist.\n"
        "... (same description) ...\n\n"
        "Return **ONLY valid JSON** exactly like this – no extra keys, no markdown, nothing else:\n"
        "{\n"
        "  \"expertise\": [\"Product-Led Growth\", \"AI Ethics\"],\n"
        "  \"plan_90_days\": [\n"
        "    \"Week 1-2: audit existing content …\",\n"
        "    \"Week 3-4: publish long-form piece on …\"\n"
        "  ],\n"
        "  \"micro_articles\": [\n"
        "    {\"theme\": \"Product-Led Growth\", \"article\": \"line1\\nline2\\nline3\\nline4\\nline5\"},\n"
        "    {\"theme\": \"AI Ethics\",        \"article\": \"line1\\nline2\\nline3\\nline4\\nline5\"}\n"
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
