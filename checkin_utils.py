import openai
import streamlit as st
import matplotlib.pyplot as plt

import pandas as pd
from datetime import datetime
from google_sheet import append_checkin_to_sheet, get_all_checkins
from checkin_crypto import encrypt_checkin, decrypt_checkin
from openai import OpenAI

import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

canvas_qs = {
    "Motivation": ["What still excites or matters to me?", "If I could only keep one reason to continue, what would it be?"],
    "Energy & Resilience": ["How am I feeling lately - physically, emotionally?", "What restores me? What drains me?"],
    "Support Systems": ["Who's truly in my corner right now?", "Where can I get the help I'm missing?"],
    "Growth Mindset": ["What's something new I've learned recently?", "Where am I avoiding challenge or feedback?"],
    "Vision": ["What would 'further' look like?", "Even if I don't know the final goal, what feels like the next right step?"]
}

canvas_help = {
    "What still excites or matters to me?": "Think about what gives you energy lately — even small sparks.",
    "If I could only keep one reason to continue, what would it be?": "Try to identify your strongest current source of drive or hope.",
    "How am I feeling lately - physically, emotionally?": "Check in with your body and mood — are you tired, calm, anxious?",
    "What restores me? What drains me?": "Mention any recent experiences or habits that energize or deplete you.",
    "Who's truly in my corner right now?": "Reflect on people who offer real emotional or practical support.",
    "Where can I get the help I'm missing?": "Name people or systems you could reach out to or wish you had.",
    "What's something new I've learned recently?": "This could be personal insight, a skill, or lesson — big or small.",
    "Where am I avoiding challenge or feedback?": "Be honest: are there areas you're playing it safe?",
    "What would 'further' look like?": "Describe what progress or growth would mean right now — even vaguely.",
    "Even if I don't know the final goal, what feels like the next right step?": "What’s a small experiment or move that feels meaningful?"
}

def ask_questions():
    answers = {}
    for section, questions in canvas_qs.items():
        st.markdown(f"#### {section}")
        answers[section] = [
            st.text_area(
                q,
                key=q,
                max_chars=500,
                placeholder=canvas_help.get(q, "Max 100 words (~500 characters)"),
                help=canvas_help.get(q)
            ) for q in questions
        ]
    return answers





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
                row_text = " | ".join(str(row.get(f"{section} Q{i}")) for section in canvas_qs for i in [1, 2])
                context_snippets.append(f"{row['date']}: {row_text}")

    context_block = "\n".join(context_snippets[:3])

    flat_responses = []
    for category, responses in canvas_answers.items():
        joined = " | ".join(responses)
        flat_responses.append(f"{category}: {joined}")

    prompt = f"""
You are a professional human coach known for being warm, insightful, and practical.

The user has completed a new check-in. Use the past check-in context below to enrich your understanding of patterns and history.

Past Check-In Context:
{context_block}

New Check-In:
{chr(10).join(flat_responses)}

Your task is to:
1. Thoughtfully analyze the current responses
2. Assign a score from 1 to 25 based on:
   - Emotional clarity
   - Depth of self-awareness
   - Intentionality
   - Growth-oriented thinking
3. Provide a short justification for the score
4. Share 2–3 specific coaching actions or reflections
5. Summarize their overall theme or growth direction in one line

Format:
Score: <number>
Explanation: <brief explanation>
Actions:
- <Personalized suggestion 1>
- <Personalized suggestion 2>
- <Optional suggestion 3>
Theme: <1-line theme>
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": "You are a wise and supportive human coach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
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


def show_insights(df):
    import matplotlib.pyplot as plt
    from datetime import datetime, timedelta
    import matplotlib.dates as mdates

    st.subheader("📊 Check-In Score Summary")

    if "date" in df.columns and "score" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
        df = df.sort_values("date")

        # User selection for timeframe
        timeframe = st.selectbox("Show scores for:", ["Last 7 days", "Last 14 days", "Last 30 days", "All time"])
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

def load_user_checkins(user_email):
    df = get_all_checkins()
    if df is not None and not df.empty:
        password = st.session_state.get("user_password", "")
        df["user_decrypted"] = df["user"].apply(lambda val: decrypt_checkin(val, password, user_email))
        df = df[df["user_decrypted"] == user_email]
        for col in df.columns:
            if col in ("user", "score", "recommendation", "date") or "Q" in col:
                df[col] = df[col].apply(lambda val: decrypt_checkin(val, password, user_email) if val else "")
        if "embedding" in df.columns:
            df["embedding_vector"] = df["embedding"].apply(lambda x: json.loads(x) if x and x.strip().startswith("[") else None)
        return df
    return None



