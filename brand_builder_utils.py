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

# brand_builder_utils.py
import json, datetime as dt, streamlit as st
from openai import OpenAI
from google_sheet import append_brand_plan, get_brandbuilder_ws
from checkin_utils import load_user_checkins, generate_embedding, build_past_context

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ---------- QUICK STATEMENT --------------------------------------------------
def make_quick_statement(user_email: str) -> str:
    """
    Return one expert statement that ties a headline (<30 days) to the user’s domain.
    Falls back gracefully if no past brand-plan exists.
    """
    # past check-in context  (≤ 1 k chars)
    past_ctx = build_past_context(user_email, max_checkins=3)

    # latest stored brand plan (optional)
    ws = get_brandbuilder_ws()
    records = [r for r in ws.get_all_records() if r.get("user") == user_email]
    plan_ctx = records[-1]["plan"] if records else "None yet."

    system = (
        "You are a senior thought-leadership ghost-writer.\n"
        "Write ONE punchy expert statement (≤35 words) that links a real-world news "
        "event from the last 30 days to the professional themes below. "
        "End the sentence with a short parenthetical source link, e.g. (NYT).\n\n"
        "RETURN ONLY the sentence – no markdown, no extra lines."
    )
    user = f"""THEMES (from last brand-plan): {plan_ctx}

PAST CHECK-IN HIGHLIGHTS:
{past_ctx}
"""

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"system","content":system},
                  {"role":"user",  "content":user}],
        response_format={"type":"text"}
    )
    return resp.choices[0].message.content.strip()

# ---------- 6-WEEK PLAN ------------------------------------------------------
def build_plan_from_pdf(pdf_text: str, user_email: str) -> dict:
    """
    Return JSON {expertise:[…], plan_6w:[…]} and persist to Google Sheet
    with an embedding of (pdf + plan).
    """
    system = (
        "You are a senior personal-branding strategist.\n"
        "Analyse the résumé below and deliver:\n"
        "A) exactly 2 expertise themes.\n"
        "B) a 6-week brand-building plan as 6 bullets (one per week).\n"
        "Return ONLY valid JSON:\n"
        "{ \"expertise\":[\"…\",\"…\"], \"plan_6w\":[\"Week 1: …\", …] }"
    )

    resp = client.chat.completions.create(
        model="o3",
        messages=[{"role":"system","content":system},
                  {"role":"user",  "content":pdf_text[:120_000]}],
        response_format={"type":"json_object"}
    )
    data = json.loads(resp.choices[0].message.content)

    # ------ store in Sheet with embedding ------------------------------------
    combined = pdf_text[:20_000] + "\n" + json.dumps(data)
    emb = generate_embedding(combined)                         :contentReference[oaicite:1]{index=1}
    append_brand_plan({
        "date": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        "user": user_email,
        "plan": json.dumps(data),
        "embedding": json.dumps(emb)
    })
    return data
