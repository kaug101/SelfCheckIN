
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

def generate_openai_feedback(canvas_answers: dict) -> str:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    flat_responses = []
    for category, responses in canvas_answers.items():
        joined = " | ".join(responses)
        flat_responses.append(f"{category}: {joined}")

    prompt = f"""
You are a helpful and empathetic coach. Below are a user's self-check-in responses across 5 life areas.

Please provide:
- A short paragraph (3–5 sentences) of overall insights
- 2–3 personalized coaching actions
- A 1-line theme or direction for their next phase of growth

Responses:
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
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ OpenAI Error: {str(e)}"

