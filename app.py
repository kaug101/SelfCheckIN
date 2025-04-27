
import streamlit as st
from datetime import date
from auth import google_login
from checkin_utils import ask_questions, generate_score, save_checkin, load_user_checkins, show_insights

st.set_page_config(page_title="Daily Fuel Check", layout="centered")

user_email = google_login()
if not user_email:
    st.stop()

st.title("👋 Welcome to your Daily Fuel Check-In")
st.subheader(f"Logged in as: {user_email}")

option = st.selectbox(
    "What would you like to do today?",
    ("Choose an option...", "📈 View Past Insights", "🆕 New Check-In")
)

if option == "📈 View Past Insights":
    st.header("📈 Your Past Check-Ins and Insights")
    df = load_user_checkins(user_email)
    if df is not None:
        show_insights(df)

elif option == "🆕 New Check-In":
    st.header("🆕 New Daily Check-In")
    canvas_answers = ask_questions()

    if st.button("Submit and Save Check-In"):
        st.info("🔄 Calculating your dynamic score using AI...")
        score = generate_score(canvas_answers)
        
        st.success(f"✅ Your total score is **{score}/25** (AI-assessed)")
        
        if score >= 20:
            st.write("✅ **Strong fuel - full tank**")
        elif score >= 15:
            st.write("🟡 **Moderate - needs tuning**")
        elif score >= 10:
            st.write("🔻 **Low - time for refueling strategies**")
        else:
            st.write("🚨 Danger zone - needs support, rest, or reorientation")
        
        try:
            save_checkin(user_email, canvas_answers, score)
            st.success("✅ Check-in successfully saved to Google Sheets!")
        except Exception as e:
            import traceback
            st.error(f"❌ Failed to save check-in: {e}")
            st.code(traceback.format_exc(), language="python")
