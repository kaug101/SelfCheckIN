import openai
import streamlit as st
import matplotlib.pyplot as plt

import pandas as pd
from datetime import datetime
from google_sheet import append_checkin_to_sheet, get_all_checkins
from checkin_crypto import encrypt_checkin, decrypt_checkin
from openai import OpenAI
from google_sheet import get_all_checkins_cached
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

import random

def build_past_context(user_email: str, max_checkins: int = 5) -> str:
    """Return a short paragraph with the user’s most recent answers."""
    df = load_user_checkins(user_email)
    if df is None or df.empty:
        return "No history yet."
    latest = df.sort_values("date").tail(max_checkins)

    out_lines = []
    for _, row in latest.iterrows():
        pieces = []
        for cat in canvas_qs_pool.keys():      # keep category order
            pieces.append(
                f"{cat}: {row.get(f'{cat} Q1','')} | {row.get(f'{cat} Q2','')}"
            )
        out_lines.append(f"{row['date']}: " + " || ".join(pieces))
    return "\n".join(out_lines)


# checkin_utils.py
def fetch_dynamic_qs_openai(user_email: str) -> dict:
    """
    Return a dict with exactly 5 categories → 2 × {"q","help"} each.
    Falls back to the static pool (with canvas_help) if anything goes wrong.
    """
    if "dynamic_qs" in st.session_state:           # already fetched this run
        return st.session_state["dynamic_qs"]

    # ---- build past-context block (same as before) ---------------------------
    past_ctx = build_past_context(user_email)

    system = (
        "You are an upbeat career coach.\n"
        "For each of the five categories I give you, produce *exactly two* "
        "fresh reflection questions (Max 12 words) **and** a one-sentence help tip (Max 12 words). \n"
        "Return ONLY valid JSON like:\n"
        "{\n"
        '  "Motivation": [ {"q":"...","help":"..."}, {"q":"...","help":"..."} ],\n'
        '  "Energy & Resilience": [...], ...\n'
        "}"
    )

    user_prompt = f"""PAST ANSWERS
{past_ctx}

CATEGORIES (keep names & order):
{list(canvas_qs_pool.keys())}
"""

    try:
        client  = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        resp    = client.chat.completions.create(
            model="o3",                      # o3 ignores temperature → don’t send it
            messages=[{"role":"system","content":system},
                      {"role":"user",  "content":user_prompt}],
        )
        data = json.loads(resp.choices[0].message.content)

        # --- quick schema sanity-check ---------------------------------------
        for cat in canvas_qs_pool.keys():
            assert cat in data and len(data[cat]) == 2
            for item in data[cat]:
                assert isinstance(item, dict) and "q" in item and "help" in item

        st.session_state["dynamic_qs"] = data
        return data

    except Exception as e:
        # graceful fallback → wrap static pool with their stored help blurbs
        st.warning(f"⚠️ Using static pool. ({e})")
        fallback = {
            cat: [{"q": q,
                   "help": canvas_help.get(q,
                            "Just be honest — even rough thoughts count.") }
                  for q in random.sample(questions, 2)]
            for cat, questions in canvas_qs_pool.items()
        }
        st.session_state["dynamic_qs"] = fallback
        return fallback


# 🎯 Playful growth-mindset question pool
canvas_qs_pool = {
    "Motivation": [
        "What tiny thing still lights a spark in you?",
        "If your life had a trailer, what scene would you keep in?",
        "What’s keeping you curious lately?",
        "When did you last feel like, ‘heck yes!’?",
        "What would you do tomorrow even if no one noticed?"
    ],
    "Energy & Resilience": [
        "Are you running on espresso, fumes, or vibes?",
        "What’s been your emotional battery percentage this week?",
        "What people, snacks, or activities recharge you?",
        "What's been draining your inner superhero powers?",
        "If you had a ‘low energy’ warning light, would it be on?"
    ],
    "Support Systems": [
        "Who’s your ride-or-die this week?",
        "If you had a lifeline, who would you call?",
        "Any unsung heroes you want to thank?",
        "Are you asking for help or trying to solo everything?",
        "Who deserves a coffee for being there?"
    ],
    "Growth Mindset": [
        "What’s something new you messed up — and learned from?",
        "When did you last surprise yourself?",
        "Where are you quietly leveling up?",
        "Any feedback you dodged (but kind of needed)?",
        "What's one awkward thing you’re doing to grow?"
    ],
    "Vision": [
        "What would ‘Level 2’ of your life look like?",
        "Even without the full map, what’s the next step?",
        "What future version of you would fist bump you today?",
        "What are you daydreaming about these days?",
        "If your purpose was a playlist, what song just got added?"
    ]
}

# 📝 Contextual help for each question
canvas_help = {
    "What tiny thing still lights a spark in you?": "Think small — even a funny meme, warm tea, or unfinished idea counts.",
    "If your life had a trailer, what scene would you keep in?": "What recent moment felt ‘so you’ or gave your story momentum?",
    "What’s keeping you curious lately?": "Name anything you keep coming back to — a topic, project, mystery.",
    "When did you last feel like, ‘heck yes!’?": "Capture a moment of alignment, excitement, or even wild spontaneity.",
    "What would you do tomorrow even if no one noticed?": "What action would still feel worthwhile — even in secret?",

    "Are you running on espresso, fumes, or vibes?": "Be honest — your internal battery status matters more than your to-do list.",
    "What’s been your emotional battery percentage this week?": "Try a number or describe it: charged, drained, blinking red?",
    "What people, snacks, or activities recharge you?": "List your go-to power-ups — silly, serious, or unexpected.",
    "What's been draining your inner superhero powers?": "Where have you been leaking energy, even subtly?",
    "If you had a ‘low energy’ warning light, would it be on?": "Any warning signs you’ve been trying to ignore?",

    "Who’s your ride-or-die this week?": "Who’s shown up for you — practically or emotionally?",
    "If you had a lifeline, who would you call?": "Think of someone who makes you feel safer or stronger.",
    "Any unsung heroes you want to thank?": "Mention the folks who helped you (even without knowing it).",
    "Are you asking for help or trying to solo everything?": "Have you been open or secretly juggling it all?",
    "Who deserves a coffee for being there?": "Who showed up in a way you want to acknowledge?",

    "What’s something new you messed up — and learned from?": "Own the goof — and the wisdom you squeezed from it.",
    "When did you last surprise yourself?": "Describe a moment that made you think, ‘Whoa, did I just do that?’",
    "Where are you quietly leveling up?": "Even if no one sees it — where are you growing?",
    "Any feedback you dodged (but kind of needed)?": "Time to admit it — what feedback still lingers?",
    "What's one awkward thing you’re doing to grow?": "Growth is often messy — name your current beautiful mess.",

    "What would ‘Level 2’ of your life look like?": "Paint a picture of your next evolution — vague is okay.",
    "Even without the full map, what’s the next step?": "Tiny moves forward count. What feels like progress today?",
    "What future version of you would fist bump you today?": "Who are you becoming — and would they be proud?",
    "What are you daydreaming about these days?": "Fantasies and vague pulls often signal buried desires.",
    "If your purpose was a playlist, what song just got added?": "Pick a vibe or track that reflects your current direction."
}

# checkin_utils.py
import hashlib
import textwrap
import streamlit as st
from typing import Dict, List

# checkin_utils.py
import hashlib, streamlit as st, textwrap

DEFAULT_HELP = "Just be honest — even rough thoughts count."

def _normalise_section(payload):
    """Convert any supported payload shape to [{'q': ..., 'help': ...}, …]."""
    if isinstance(payload, dict) and "questions" in payload:                 # new JSON
        qs, hs = payload.get("questions", [])[:2], payload.get("help", [])
        return [{"q": q, "help": hs[i] if i < len(hs) else DEFAULT_HELP}
                for i, q in enumerate(qs)]
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):  # list of dicts
        return payload[:2]
    if isinstance(payload, list):                                            # list of strings
        from .checkin_utils import canvas_help
        return [{"q": q, "help": canvas_help.get(q, DEFAULT_HELP)}
                for q in payload[:2]]
    return []  # fallback



def ask_questions(key_prefix=""):
    answers = {}
    user_email  = st.session_state.get("user_email", "")
    question_set = fetch_dynamic_qs_openai(user_email)

    for section, qa_pairs in question_set.items():
        st.markdown(f"#### {section}")
        answers[section] = []

        for idx, qa in enumerate(qa_pairs):
            q_text  = qa["q"]
            help_txt = qa.get("help") or "Just be honest — even rough thoughts count."

            # stable widget key
            slug = hashlib.md5(q_text.encode()).hexdigest()[:6]
            key  = f"{section}_{idx}_{slug}"

            ans = st.text_area(
                label=q_text,
                key=f"{key_prefix}{key}",
                placeholder=help_txt,
                help=help_txt
            )
            st.caption(help_txt)
            answers[section].append(ans)

    return answers





def _wrap_q(q: str) -> dict:
    """Return the canonical {"q": …, "help": …} structure for any plain string."""
    return {
        "q": q,
        "help": canvas_help.get(q, "Just be honest — even rough thoughts count.")
    }


def get_dynamic_questions_once():
    if "dynamic_qs" not in st.session_state:
        st.session_state["dynamic_qs"] = {
            section: random.sample(questions, 2)
            for section, questions in canvas_qs_pool.items()
        }
    return st.session_state["dynamic_qs"]


def build_image_prompt(insights: str) -> str:
    return f"""
Create a clean, flat-style digital illustration that clearly represents a personalized coaching action plan.
Purpose: The image should help the user **visually recall** and **stay motivated to follow** their action plan.

The image should:
- Depict 3 key steps based on the actions from these coaching suggestions: {insights}
- Show these steps as a vertical or horizontal sequence, like a roadmap or flow
- For each step, include a symbolic scene   
- Use realistic or symbolic visuals only 
- Strictly avoid any form of written or typographic characters. Do not include letters, numbers, signs, or symbolic text.
- Style: Flat illustration, warm tone, soft colors

"""


def generate_openai_feedback(canvas_answers: dict) -> tuple[int, str]:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    # Prepare current embedding
    current_text = " ".join(ans for section in canvas_answers.values() for ans in section)
    current_embedding = generate_embedding(current_text)

    # Load past check-ins with embeddings
    user_email = st.session_state.get("user_email", "")
    df = load_user_checkins(user_email)
    context_snippets = []

    if df is not None and "embedding_vector" in df.columns:
        embedding_tuples = [(i, vec) for i, vec in enumerate(df["embedding_vector"]) if vec is not None]
        if embedding_tuples:
            row_indices, vectors = zip(*embedding_tuples)
            top_indices = get_top_similar_checkins(current_embedding, list(vectors))
            for rel_idx in top_indices:
                idx = row_indices[rel_idx]
                row = df.iloc[idx]
                row_text = " | ".join(str(row.get(f"{section} Q{i}")) for section in canvas_qs_pool for i in [1, 2])
                context_snippets.append(f"{row['date']}: {row_text}")

    context_block = "\n".join(context_snippets[:3])

    flat_responses = []
    for category, responses in canvas_answers.items():
        joined = " | ".join(responses)
        flat_responses.append(f"{category}: {joined}")
    flat_response_block = "\n".join(flat_responses)

    prompt = f"""
You are a professional human coach known for being insightful, and practical.
Act as a tough, no-nonsense career coach specifically for professionals looking to grow. Avoid fluff and provide clear, direct, and actionable guidance. Pushe users hard, be brutally honest, and avoid sugar-coating advice. 
Focus on practical strategies, filling skill gaps, developing personal branding and networking plans. 
The tone is sharp, businesslike, and mirrors the precision of an executive coach—focused on results, accountability, and professional growth.
Encourage progress, speak like a trusted coach who believes in the user's potential.
Use clear, concise language.

The user has completed a new check-in. Use the past check-in context below to enrich your understanding of patterns and history.

Past Check-In Context:
{context_block}

New Check-In:
{flat_response_block}

Your task is to:
1. Thoughtfully analyze the current responses
2. Assign a score from 1 to 25 based on:
   - Emotional clarity
   - Depth of self-awareness
   - Intentionality
   - Growth-oriented thinking
   
3. Provide a short justification for the score

4. Share 3 concise, actionable coaching suggestions (max 12 words each).

5. Provide reference to a relevant framework to explore further (max 1 line)

Format:
Score: <number>
Explanation: <brief explanation>
Actions:
- <Actionable suggestion 1> (max 12 words)
- <Actionable suggestion 2>
- <Optional suggestion 3>
Framework: <1-line>
"""

    try:
        response = client.chat.completions.create(
            #model="gpt-4o",
            model="o3",
            messages=[
                {"role": "system", "content": "You are a wise and supportive human coach."},
                {"role": "user", "content": prompt}
            ],
            temperature=1,
        )
        content = response.choices[0].message.content.strip()
        score_line = next((line for line in content.splitlines() if line.startswith("Score:")), "")
        score = int("".join([c for c in score_line if c.isdigit()])) if score_line else 0
        return score, content
    except Exception as e:
        return 0, f"⚠️ OpenAI Error: {str(e)}"


def generate_image_from_prompt(prompt_text: str) -> str:
    try:
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt_text,
            n=1,
            size="1024x1024"
        )
        return response.data[0].url
    except Exception as e:
        st.error(f"❌ Image generation failed: {e}")
        return ""



from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

def overlay_coaching_text(image_url: str, action_items: list[str]) -> Image.Image:

    # Parse coaching suggestions
    #lines = [line.strip("- ").strip() for line in insights.splitlines() if line.strip().startswith("-")]
    lines = action_items

    # Load image
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content)).convert("RGBA")

    draw = ImageDraw.Draw(img)
    width, height = img.size

    # Try to load a clean font
    try:
        font = ImageFont.truetype("arial.ttf", size=28)
    except:
        font = ImageFont.load_default()

    # Draw background strip at top
    overlay = Image.new("RGBA", img.size, (255,255,255,0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([0, 0, width, 40 + 35 * len(lines)], fill=(255, 255, 255, 220))  # White strip

    # Draw each line
    y = 20
    for line in lines:
        overlay_draw.text((30, y), line, font=font, fill=(0, 0, 0, 255))  # Black text
        y += 35

    # Combine
    combined = Image.alpha_composite(img, overlay)

    return combined.convert("RGB")


def show_insights(df, key_prefix: str = "insights"):
    import matplotlib.pyplot as plt
    from datetime import datetime, timedelta
    import matplotlib.dates as mdates

    st.subheader("📊 Check-In Score Summary")

    if "date" in df.columns and "score" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
        df = df.sort_values("date")

        # User selection for timeframe
        timeframe = st.selectbox(
            "Show scores for:",
            ["Last 7 days", "Last 14 days", "Last 30 days", "All time"],
            key=f"{key_prefix}_timeframe"
        )
        days_map = {
            "Last 7 days": 7,
            "Last 14 days": 14,
            "Last 30 days": 30,
            "All time": None
        }
        days = days_map[timeframe]
        if days:
            cutoff_date = datetime.now().date() - timedelta(days=days)
            df_filtered = df[df["date"].dt.date >= cutoff_date]
        else:
            df_filtered = df

        # Plot
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(df["date"], df["score"], marker='o', linestyle='-', color='gray', alpha=0.3, label="All scores")
        ax.plot(df_filtered["date"], df_filtered["score"], marker='o', linestyle='-', color='blue', label=f"{timeframe}")

        # Threshold lines
        ax.axhline(y=10, color='red', linestyle='--', linewidth=1, label='Needs Attention (<10)')
        ax.axhline(y=20, color='green', linestyle='--', linewidth=1, label='Excellent (≥20)')

        ax.set_ylim(1, 25)
        ax.set_title("Check-In Score Summary")
        ax.set_xlabel("Date")
        ax.set_ylabel("Score (1–25)")

        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate(rotation=45)

        ax.grid(True)
        ax.legend()
        st.pyplot(fig)

    # Coaching recommendation
    if "recommendation" in df.columns and not df["recommendation"].isnull().all():
        latest = df.sort_values("date").iloc[-1]
        st.subheader("🧠 Last Coaching Recommendation")
        st.markdown(latest["recommendation"])

    # Full data table
    with st.expander("📋 Show full check-in details"):
        st.dataframe(
            df.sort_values(by="date", ascending=False).style.format({"date": lambda d: d.strftime("%Y-%m-%d")}),
            use_container_width=True,
            height=300
        )




def get_demo_checkins(selected_email):
    df = get_all_checkins()
    if df is not None and not df.empty:
        password = st.session_state.get("user_password", "")
        df["user_decrypted"] = df["user"].apply(lambda val: decrypt_checkin(val, password, selected_email))
        df = df[df["user_decrypted"] == selected_email]
        for col in df.columns:
            if col in ("user", "score", "recommendation", "date") or "Q" in col:
                df[col] = df[col].apply(lambda val: decrypt_checkin(val, password, selected_email) if val else "")
        return df
    return pd.DataFrame()

def show_demo_coaching(selected_email):
    if selected_email == "alex@example.com":
        st.markdown("### Alex (alex@example.com)")
        st.markdown("- 🧠 **Stretch into a Leadership Role**  \nAlex is consistently performing at a high level and showing signs of sustained motivation and support. Taking on leadership can help channel their energy into multiplying impact.")
        st.markdown("- 🌱 **Experiment with New Challenges**  \nTo avoid plateauing, Alex should seek out stretch assignments or novel tasks that demand new skills and perspectives.")
        st.markdown("- 🧘 **Invest in Recovery Rituals**  \nWhile high performing, the data hints at intense engagement that could lead to burnout. Small rituals like nature walks or journaling can enhance long-term resilience.")
    elif selected_email == "jamie@example.com":
        st.markdown("### Jamie (jamie@example.com)")
        st.markdown("- 🛠️ **Build a Resilience Routine**  \nJamie’s entries show signs of moderate motivation but inconsistent energy. Introducing small, daily recovery habits can help maintain momentum.")
        st.markdown("- 🔍 **Clarify a Meaningful Short-Term Goal**  \nThe text shows a drift in purpose. Setting a concrete 2-week target can reinstate direction and reduce emotional fatigue.")
        st.markdown("- 🤝 **Expand Support Circle**  \nSupport system references are sparse. Encouraging Jamie to proactively reconnect with peers or mentors can stabilize emotional load.")
    elif selected_email == "morgan@example.com":
        st.markdown("### Morgan (morgan@example.com)")
        st.markdown("- 🛌 **Permission to Rest**  \nMorgan’s check-ins point to exhaustion and demotivation. Before any change, recovery needs to be prioritized — guilt-free rest is valid and necessary.")
        st.markdown("- 🧩 **Reconnect to Core Values**  \nThe text shows signs of identity disconnection. Reflecting on why certain things matter can re-anchor purpose and self-worth.")
        st.markdown("- 🔦 **Find Micro-Moments of Joy**  \nMorgan should be encouraged to note 1–2 tiny joys per day. Building emotional scaffolding from joy is a proven recovery tool.")
    else:
        st.warning("No coaching suggestions available.")




def generate_embedding(text: str) -> list[float]:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


def get_top_similar_checkins(current_embedding, past_embeddings, top_k=3):
    if not past_embeddings:
        return []
    sims = cosine_similarity([current_embedding], past_embeddings)[0]
    top_indices = np.argsort(sims)[-top_k:][::-1]
    return top_indices


# Modify save_checkin to include embedding

def save_checkin(user_email, canvas_answers, score, recommendation=None):
    password = st.session_state.get("user_password", "")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    flat_text = " ".join(ans for section in canvas_answers.values() for ans in section)
    embedding = generate_embedding(flat_text)

    entry = {
        "date": encrypt_checkin(now_str, password, user_email),
        "user": encrypt_checkin(user_email, password, user_email),
        "score": encrypt_checkin(str(score), password, user_email),
        "recommendation": encrypt_checkin(recommendation or "", password, user_email),
        "embedding": json.dumps(embedding)
    }
    for section, answers in canvas_answers.items():
        entry[f"{section} Q1"] = encrypt_checkin(answers[0], password, user_email)
        entry[f"{section} Q2"] = encrypt_checkin(answers[1], password, user_email)
    append_checkin_to_sheet(entry)


# Modify load_user_checkins to extract embeddings

def load_user_checkins(user_email: str):
    # pull from cache instead of hitting Google Sheets every rerun
    df = get_all_checkins_cached()

    if df is None or df.empty:
        return None

    password = st.session_state.get("user_password", "")

    # ---------- decrypt user column and filter to this user ----------
    df["user_decrypted"] = df["user"].apply(
        lambda val: decrypt_checkin(val, password, user_email)
    )
    df = df[df["user_decrypted"] == user_email]

    # ---------- decrypt the rest of the columns you care about -------
    for col in df.columns:
        if col in ("user", "score", "recommendation", "date") or "Q" in col:
            df[col] = df[col].apply(
                lambda val: decrypt_checkin(val, password, user_email) if val else ""
            )

    # (optional) parse embedding JSON
    if "embedding" in df.columns:
        df["embedding_vector"] = df["embedding"].apply(
            lambda x: json.loads(x) if x and x.strip().startswith("[") else None
        )

    return df

def reflect_on_last_action(df):
    if df is not None and not df.empty:
        latest = df.sort_values("date").iloc[-1]
        last_reco = latest.get("recommendation", "")
        st.info("📌 Here's a reminder of your last coaching action plan:")
        st.markdown(last_reco)

        rating = st.slider(
            "How well were you able to follow through with this?",
            min_value=1,
            max_value=5,
            value=3,
            format="%d 🌟"
        )

        st.session_state["last_action_rating"] = rating
