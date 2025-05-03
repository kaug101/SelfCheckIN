
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
from google_sheet import append_checkin_to_sheet, get_all_checkins

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
        answers[section] = [st.text_area(q, key=q) for q in questions]
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

def show_demo_coaching(selected_email):
    if selected_email == "alex@example.com":
        st.markdown("### Alex (alex@example.com)")
        st.markdown("""- 🧠 **Stretch into a Leadership Role**  
Alex is consistently performing at a high level and showing signs of sustained motivation and support. Taking on leadership can help channel their energy into multiplying impact.""")
        st.markdown("""- 🌱 **Experiment with New Challenges**  
To avoid plateauing, Alex should seek out stretch assignments or novel tasks that demand new skills and perspectives.""")
        st.markdown("""- 🧘 **Invest in Recovery Rituals**  
While high performing, the data hints at intense engagement that could lead to burnout. Small rituals like nature walks or journaling can enhance long-term resilience.""")
    elif selected_email == "jamie@example.com":
        st.markdown("### Jamie (jamie@example.com)")
        st.markdown("""- 🛠️ **Build a Resilience Routine**  
Jamie’s entries show signs of moderate motivation but inconsistent energy. Introducing small, daily recovery habits can help maintain momentum.""")
        st.markdown("""- 🔍 **Clarify a Meaningful Short-Term Goal**  
The text shows a drift in purpose. Setting a concrete 2-week target can reinstate direction and reduce emotional fatigue.""")
        st.markdown("""- 🤝 **Expand Support Circle**  
Support system references are sparse. Encouraging Jamie to proactively reconnect with peers or mentors can stabilize emotional load.""")
    elif selected_email == "morgan@example.com":
        st.markdown("### Morgan (morgan@example.com)")
        st.markdown("""- 🛌 **Permission to Rest**  
Morgan’s check-ins point to exhaustion and demotivation. Before any change, recovery needs to be prioritized — guilt-free rest is valid and necessary.""")
        st.markdown("""- 🧩 **Reconnect to Core Values**  
The text shows signs of identity disconnection. Reflecting on why certain things matter can re-anchor purpose and self-worth.""")
        st.markdown("""- 🔦 **Find Micro-Moments of Joy**  
Morgan should be encouraged to note 1–2 tiny joys per day. Building emotional scaffolding from joy is a proven recovery tool.""")
    else:
        st.warning("No coaching suggestions available.")
