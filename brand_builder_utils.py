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
        "B) A 10-line micro-article (≈1-2 sentences per line) that links VERY recent "
        "world/events (<30 days) to those two themes, demonstrating thought-leadership.\n"
        "Return ONLY valid JSON:\n"
        "{\n  \"expertise\": [\"…\", \"…\"],\n  \"article\": \"<10 lines separated by \\n>\"\n}"
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
            temperature=0.3,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        st.error(f"⚠️ Brand-Builder error: {e}")
        return None
