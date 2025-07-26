# brand_agents.py

from langchain.agents import Tool, AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
import json, datetime
from checkin_utils import load_user_checkins, generate_embedding
from google_sheet import get_brandbuilder_ws, append_brand_plan
from brand_builder_utils import extract_pdf_text

# ---- Tool wrappers --------------------------------------------------------

@tool
def fetch_last_checkins(user_email: str) -> str:
    """Return the user's 3 most recent check-ins."""
    return "\n\n".join(load_user_checkins(user_email)[-3:])

@tool
def get_brand_plan(user_email: str) -> str:
    """Return the most recent brand-building plan (JSON string) or 'None'."""
    ws = get_brandbuilder_ws()
    rows = [r for r in ws.get_all_records() if r["user"] == user_email]
    return rows[-1]["plan"] if rows else "No plan found"

@tool
def parse_pdf(pdf_bytes: bytes) -> str:
    """Extracts plain text from the uploaded PDF résumé."""
    return extract_pdf_text(pdf_bytes)

@tool
def store_plan(user_email: str, plan_json: str) -> str:
    """Stores the plan and its embedding in the Google Sheet."""
    emb = generate_embedding(plan_json)
    append_brand_plan({
        "date": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        "user": user_email,
        "plan": plan_json,
        "embedding": json.dumps(emb)
    })
    return "Plan saved."

# ---- LLM setup ------------------------------------------------------------

llm_gpt4 = ChatOpenAI(model="gpt-4o", temperature=0.4)
llm_plan = ChatOpenAI(model="gpt-4o", temperature=0.3)
llm_o3   = ChatOpenAI(model="o3")

# ---- Agent 1: Quick Statement ---------------------------------------------

quick_tools = [fetch_last_checkins, get_brand_plan]

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

quick_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a professional brand positioning expert who helps individuals articulate "
     "their unique value and insight in a single, sharp expert statement.\n\n"
     "Use the user's background, past check-ins, and CV/resume (if available) to generate "
     "a positioning sentence that:\n"
     "- Clearly defines the user’s domain of expertise\n"
     "- Ties into a relevant trend or challenge in that domain\n"
     "- Is ≤35 words\n"
     "- Sounds bold, insightful, and original\n\n"
     "Return ONLY the final statement – no commentary, markdown, or formatting."),
    ("user",
     "USER CONTEXT:\n"
     "{input}\n\n"
     "Generate the positioning statement."),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])



quick_agent = create_openai_functions_agent(llm=llm_gpt4,
                                            tools=quick_tools,
                                            prompt=quick_prompt)

QuickStatementAgent = AgentExecutor(agent=quick_agent,
                                    tools=quick_tools,
                                    verbose=True)

# ---- Agent 2: Brand Plan Builder -----------------------------------------

plan_tools = [parse_pdf, store_plan]

plan_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a personal branding strategist.\n"
     "Given a user's résumé (in plain text), extract a 6-week brand plan as JSON.\n\n"
     "The JSON MUST have this exact structure:\n"
     "{{\n"
     "  \"expertise\": [\"<theme1>\", \"<theme2>\"],\n"
     "  \"plan_6w\": [\n"
     "    \"Week 1: ...\",\n"
     "    \"Week 2: ...\",\n"
     "    \"Week 3: ...\",\n"
     "    \"Week 4: ...\",\n"
     "    \"Week 5: ...\",\n"
     "    \"Week 6: ...\"\n"
     "  ]\n"
     "}}\n\n"
     "Return ONLY valid JSON matching the format above. Do not include explanations or text before or after the JSON."),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])


plan_agent = create_openai_functions_agent(llm=llm_plan,
                                           tools=plan_tools,
                                           prompt=plan_prompt)

PlanBuilderAgent = AgentExecutor(agent=plan_agent,
                                 tools=plan_tools,
                                 verbose=True)

def get_user_context(user_email: str) -> str:
    """Returns combined context from past check-ins and brand plan (CV)."""

    # --- Load recent check-ins
    checkins = load_user_checkins(user_email)
    checkin_context = "\n".join(f"- {c}" for c in checkins[-3:]) if checkins else "None found."

    # --- Load most recent brand plan (CV-based)
    ws = get_brandbuilder_ws()
    rows = [r for r in ws.get_all_records() if r["user"] == user_email]
    if rows:
        latest_plan = rows[-1].get("plan", "")
        try:
            plan_data = json.loads(latest_plan)
            cv_context = f"Expertise: {', '.join(plan_data.get('expertise', []))}\n"
            cv_context += "Plan Highlights:\n" + "\n".join(f"- {line}" for line in plan_data.get("plan_6w", []))
        except json.JSONDecodeError:
            cv_context = latest_plan  # fallback to raw string if parsing fails
    else:
        cv_context = "None found."

    return (
        "Check-Ins:\n"
        f"{checkin_context}\n\n"
        "CV Summary / Brand Plan:\n"
        f"{cv_context}"
    )
