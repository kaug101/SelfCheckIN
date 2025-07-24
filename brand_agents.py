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
    return rows[-1]["plan"] if rows else "None"

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
llm_o3   = ChatOpenAI(model="o3")

# ---- Agent 1: Quick Statement ---------------------------------------------

quick_tools = [fetch_last_checkins, get_brand_plan]

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

quick_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a ghostwriter creating concise expert statements..."),
    ("user", "{input}"),
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
    ("system", "You are a brand strategist..."),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])


plan_agent = create_openai_functions_agent(llm=llm_o3,
                                           tools=plan_tools,
                                           prompt=plan_prompt)

PlanBuilderAgent = AgentExecutor(agent=plan_agent,
                                 tools=plan_tools,
                                 verbose=True)
