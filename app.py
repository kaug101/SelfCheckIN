
import streamlit as st
from datetime import date
from auth import google_login
from checkin_utils import ask_questions, generate_score, save_checkin, load_user_checkins

st.set_page_config(page_title="Daily Fuel Check", layout="centered")

user_email = google_login()
if not user_email:
    st.stop()

st.title("🛠️ Daily Fuel Check-In")

st.subheader("📝 Fuel Canvas")
canvas_answers = ask_questions()

if st.button("Submit Check-In"):
    st.info("🔄 Calculating your dynamic score using AI...")
    score = generate_score(canvas_answers)

    st.success(f"Your total score is **{score}/25** (AI-assessed)")

    if score >= 20:
        st.write("✅ **Strong fuel - full tank**")
    elif score >= 15:
        st.write("🟡 **Moderate - needs tuning**")
    elif score >= 10:
        st.write("🔻 **Low - time for refueling strategies**")
    else:
        st.write("🚨 **Danger zone - needs support, rest, or reorientation**")

    if st.button("Save Check-In"):
        save_checkin(user_email, canvas_answers, score)
        st.success("✅ Check-in saved!")

st.subheader("📅 Your Past Check-Ins")
checkins_df = load_user_checkins(user_email)
if checkins_df.empty:
    st.info("No previous check-ins found.")
else:
    st.dataframe(checkins_df.sort_values(by='date', ascending=False), use_container_width=True)
