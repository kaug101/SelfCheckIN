
import streamlit as st
import pandas as pd
from auth import email_step_authentication
from checkin_utils import (
    ask_questions,
    generate_score,
    save_checkin,
    load_user_checkins,
    show_insights,
    show_demo_coaching,
    get_demo_checkins
)

st.set_page_config(page_title="Fuel Check-In App", layout="centered")
st.title("🏁 Welcome to the Daily Fuel Check-In App")

mode = st.radio("Choose your mode:", ["🎯 Demo Mode", "🙋‍♂️ User Mode"])

if mode == "🎯 Demo Mode":
    st.subheader("Demo Mode: View Individual Personas")
    selected_persona = st.radio("Choose a persona:", ["Alex (alex@example.com)", "Jamie (jamie@example.com)", "Morgan (morgan@example.com)"])

    persona_map = {
        "Alex (alex@example.com)": "alex@example.com",
        "Jamie (jamie@example.com)": "jamie@example.com",
        "Morgan (morgan@example.com)": "morgan@example.com"
    }

    demo_data = get_demo_checkins(persona_map[selected_persona])
    if not demo_data.empty:
        show_insights(demo_data)
        st.header("🧑‍🏫 Coaching Recommendations")
        show_demo_coaching(persona_map[selected_persona])
    else:
        st.warning("No demo data found for this persona.")

elif mode == "🙋‍♂️ User Mode":
    st.subheader("User Login / Signup")

    user_email, user_exists, authenticated = email_step_authentication()

    if authenticated:
        st.success(f"✅ Logged in as: {user_email}")
        user_action = "🆕 New Check-In"  # Default for new users

        df = load_user_checkins(user_email)
        if df is not None and not df.empty:
            user_action = st.selectbox("What would you like to do?", ("📈 View Past Insights", "🆕 New Check-In"))

        if user_action == "📈 View Past Insights":
            if df is not None:
                show_insights(df)

        if user_action == "🆕 New Check-In":
            canvas_answers = ask_questions()
            if st.button("Submit and Save Check-In"):
                st.info("🔄 Calculating your dynamic score...")
                score = generate_score(canvas_answers)
                st.success(f"✅ Your total score is **{score}/25**")
                try:
                    save_checkin(user_email, canvas_answers, score)
                    st.success("✅ Check-in successfully saved!")
                except Exception as e:
                    import traceback
                    st.error(f"❌ Failed to save check-in: {e}")
                    st.code(traceback.format_exc(), language="python")
