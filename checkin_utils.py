import openai
import streamlit as st
import pandas as pd
from datetime import datetime
from google_sheet import append_checkin_to_sheet, get_all_checkins
from checkin_crypto import encrypt_checkin, decrypt_checkin
from openai import OpenAI

canvas_qs = {
    "Motivation": ["What still excites or matters to me?", "If I could only keep one reason to continue, what would it be?"],
    "Energy & Resilience": ["How am I feeling lately - physically, emotionally?", "What restores me? What drains me?"],
    "Support Systems": ["Who's truly in my corner right now?", "Where can I get the help I'm missing?"],
    "Growth Mindset": ["What's something new I've learned recently?", "Where am I avoiding challenge or feedback?"],
    "Vision": ["What would 'further' look like?", "Even if I don't know the final goal, what feels like the next right step?"]
}

def ask_questions():
    answers = {}
    for section, questions in canvas_qs.items():
        st.markdown(f"#### {section}")
        answers[section] = [
            st.text_area(q, key=q, max_chars=500, help="Max 100 words (~500 characters)") for q in questions
        ]
    return answers

def save_checkin(user_email, canvas_answers, score, recommendation=None):
    password = st.session_state.get("user_password", "")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = {
        "date": encrypt_checkin(now_str, password, user_email),
        "user": encrypt_checkin(user_email, password, user_email),
        "score": encrypt_checkin(str(score), password, user_email),
        "recommendation": encrypt_checkin(recommendation or "", password, user_email)
    }
    for section, answers in canvas_answers.items():
        entry[f"{section} Q1"] = encrypt_checkin(answers[0], password, user_email)
        entry[f"{section} Q2"] = encrypt_checkin(answers[1], password, user_email)
    append_checkin_to_sheet(entry)

def load_user_checkins(user_email):
    df = get_all_checkins()
    if df is not None and not df.empty:
        password = st.session_state.get("user_password", "")
        df["user_decrypted"] = df["user"].apply(lambda val: decrypt_checkin(val, password, user_email))
        df = df[df["user_decrypted"] == user_email]
        for col in df.columns:
            if col in ("user", "score", "recommendation", "date") or "Q" in col:
                df[col] = df[col].apply(lambda val: decrypt_checkin(val, password, user_email) if val else "")
        return df
    return None

def generate_openai_feedback(canvas_answers: dict) -> tuple[int, str]:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    flat_responses = []
    for category, responses in canvas_answers.items():
        joined = " | ".join(responses)
        flat_responses.append(f"{category}: {joined}")

    prompt = f"""
You are a professional human coach known for being warm, insightful, and practical.

A user has completed a daily self-check-in across 5 key life areas: Motivation, Energy & Resilience, Support Systems, Growth Mindset, and Vision.

Your task is to:
1. Thoughtfully analyze their responses
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

User's responses:
{chr(10).join(flat_responses)}
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
        # Extract the score from the response
        score_line = next((line for line in content.splitlines() if line.startswith("Score:")), "")
        score = int("".join([c for c in score_line if c.isdigit()])) if score_line else 0
        return score, content
    except Exception as e:
        return 0, f"⚠️ OpenAI Error: {str(e)}"


def build_image_prompt(insights: str) -> str:
    return f"""
Create a clear and motivating illustration that visually represents a personalized action plan.

Based on the following coaching suggestions:
{insights}

Please generate an image that helps the user remember and follow through on their next steps.

Include:
- Visual symbols or scenes that represent each recommended action (e.g. journaling, reaching out, taking rest)
- An implicit sense of sequence or progression (like a path, timeline, or staircase)
- Elements tied to specific keywords in the actions (e.g. 'plan', 'support', 'goal', 'energy')

Optionally: You may add **1–3 short readable text labels** (1–2 words each) to anchor key steps — only if they enhance clarity. Avoid long sentences.

Style: Gentle realism or symbolic clarity. Motivational, grounded, and visually clean.
"""



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

def show_insights(df):
    st.subheader("📊 Check-In Score Summary")
    if "date" in df.columns and "score" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")
        st.line_chart(df.set_index("date")["score"])

    if "recommendation" in df.columns and not df["recommendation"].isnull().all():
        latest = df.sort_values("date").iloc[-1]
        st.subheader("🧠 Last Coaching Recommendation")
        st.markdown(latest["recommendation"])

    with st.expander("📋 Show full check-in details"):
        st.dataframe(df.sort_values(by="date", ascending=False), use_container_width=True)


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
