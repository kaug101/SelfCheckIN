
import streamlit as st
import pandas as pd
from datetime import date
import os
import openai

def generate_score(canvas_answers):
    # Real API call would go here
    score = 0
    for answers in canvas_answers.values():
        for ans in answers:
            length = len(ans.strip())
            if length > 100:
                score += 5
            elif length > 50:
                score += 4
            elif length > 20:
                score += 3
            elif length > 5:
                score += 2
            else:
                score += 1
    return min(score, 25)

canvas_qs = {
    "Motivation": [
        "What still excites or matters to me?",
        "If I could only keep one reason to continue, what would it be?",
    ],
    "Energy & Resilience": [
        "How am I feeling lately - physically, emotionally?",
        "What restores me? What drains me?",
    ],
    "Support Systems": [
        "Who's truly in my corner right now?",
        "Where can I get the help I'm missing?",
    ],
    "Growth Mindset": [
        "What's something new I've learned recently?",
        "Where am I avoiding challenge or feedback?",
    ],
    "Vision": [
        "What would 'further' look like?",
        "Even if I don't know the final goal, what feels like the next right step?",
    ]
}

def ask_questions():
    answers = {}
    for section, questions in canvas_qs.items():
        st.markdown(f"#### {section}")
        answers[section] = [st.text_area(q, key=q) for q in questions]
    return answers

def save_checkin(user_email, canvas_answers, score):
    entry = {
        "date": date.today(),
        "user": user_email,
        "score": score
    }
    for section, answers in canvas_answers.items():
        entry[f"{section} Q1"] = answers[0]
        entry[f"{section} Q2"] = answers[1]

    df = pd.DataFrame([entry])
    os.makedirs("data", exist_ok=True)
    file_path = "data/checkins.csv"
    if os.path.exists(file_path):
        old = pd.read_csv(file_path)
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(file_path, index=False)

def load_user_checkins(user_email):
    file_path = "data/checkins.csv"
    if not os.path.exists(file_path):
        return pd.DataFrame()
    df = pd.read_csv(file_path)
    return df[df['user'] == user_email]
