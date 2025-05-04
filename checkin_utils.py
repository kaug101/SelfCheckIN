
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
from google_sheet import append_checkin_to_sheet, get_all_checkins
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
            st.text_area(q, key=q, max_chars=800, help="Max ~100 words") for q in questions
        ]
    return answers

def generate_score(canvas_answers):
    score = 0
    for answers in canvas_answers.values():
        for ans in answers:
            length = len(ans.strip())
            if length > 100: score += 5
            elif length > 50: score += 4
            elif length > 20: score += 3
            elif length > 5: score += 2
            else: score += 1
    return min(score, 25)

def save_checkin(user_email, canvas_answers, score):
    entry = {"date": str(date.today()), "user": user_email, "score": score}
    for section, answers in canvas_answers.items():
        entry[f"{section} Q1"] = answers[0]
        entry[f"{section} Q2"] = answers[1]
    append_checkin_to_sheet(entry)

def load_user_checkins(user_email):
    df = get_all_checkins()
    if df is not None and not df.empty:
        return df[df["user"] == user_email]
    return None

def get_demo_checkins(selected_email):
    df = get_all_checkins()
    if df is not None and not df.empty:
        return df[df["user"] == selected_email]
    return pd.DataFrame()

def show_insights(df):
    st.dataframe(df.sort_values(by="date", ascending=False), use_container_width=True)
    if "date" in df.columns and "score" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        st.line_chart(df.set_index("date")["score"])

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
