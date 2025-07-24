import pdfplumber, streamlit as st, textwrap, json
from openai import OpenAI                        # already in requirements
from agents.tools import tool
from agents.memory import VectorStoreMemory
from openai import OpenAI

# re-use your helpers
from checkin_utils import load_user_checkins, generate_embedding
from google_sheet import get_brandbuilder_ws, append_brand_plan


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
    emb = generate_embedding(combined)                         
    append_brand_plan({
        "date": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        "user": user_email,
        "plan": json.dumps(data),
        "embedding": json.dumps(emb)
    })
    return data


@tool
def load_last_checkins(user: str, k: int = 3) -> str:
    "Return the k most recent check-in notes for user."
    return "\n\n".join(load_user_checkins(user)[:k])

@tool
def fetch_brand_plan(user: str) -> str | None:
    "Return latest stored brand-building plan JSON (or None)."
    ws = get_brandbuilder_ws()
    rows = [r for r in ws.get_all_records() if r["user"] == user]
    return rows[-1]["plan"] if rows else None

@tool
def extract_pdf(file_bytes: bytes) -> str:
    "Extract plaintext from an uploaded résumé / LinkedIn PDF."
    import pdfplumber
    from io import BytesIO
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        pages = [p.extract_text() for p in pdf.pages]
    return "\n".join(p for p in pages if p).strip()

@tool
def persist_plan(user: str, plan_json: str, embedding: list[float]) -> None:
    "Append plan+embedding to Google Sheet."
    append_brand_plan({
        "date": datetime.utcnow().isoformat(" ", "minutes"),
        "user": user,
        "plan": plan_json,
        "embedding": json.dumps(embedding)
    })


brand_memory = VectorStoreMemory(
    name="brand_mem",
    dimensions=1536,
    distance_metric="cosine"
)

statement_agent = Agent(
    name="Quick-Statement",
    model="gpt-4o",
    instructions=(
        "You are a ghost-writer. Craft ONE ≤35-word statement that ties "
        "a headline (<30 days) to the user’s domain.\n"
        "If no brand-plan is present, raise the string NEED_BRAND_PLAN."
    ),
    tools=[load_last_checkins, fetch_brand_plan],
    memory=brand_memory,
    # Handoff path so the LLM *itself* can call the Plan agent if needed ↓
    handoffs=[handoff(lambda: plan_agent)]
)

plan_agent = Agent(
    name="6-Week-Plan",
    model="o3",
    instructions=(
        "You are a personal-branding strategist.\n"
        "Return JSON: {expertise:[…], plan_6w:[…]} (6 bullets)."
    ),
    tools=[extract_pdf, persist_plan],
    memory=brand_memory
)

def run_brandbuilder(task: str, **kwargs):
    """task = 'statement' | 'plan'. kwargs carry Streamlit inputs."""
    if task == "statement":
        result = Runner.run_sync(statement_agent, kwargs["user_email"])
        if result.final_output == "NEED_BRAND_PLAN":
            st.info("No plan on file – switching to 6-Week planner.")
            run_brandbuilder("plan", **kwargs)
            return
        st.success(result.final_output)
    else:  # task == "plan"
        pdf_text = extract_pdf(kwargs["pdf_bytes"])
        result   = Runner.run_sync(plan_agent, pdf_text)
        st.json(result.final_output)        # pretty-print plan

@tool
def parse_pdf(pdf_bytes: bytes) -> str:
    """LangChain-compatible: return plain text from a PDF file's raw bytes."""
    import pdfplumber
    from io import BytesIO

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        pages = [page.extract_text() for page in pdf.pages]
    return "\n".join(p for p in pages if p).strip()
