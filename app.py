import streamlit as st
from auth import ( 
    email_step_authentication,
    send_password_reset_email
)
from checkin_utils import (
    ask_questions,
    #generate_score,
    save_checkin,
    load_user_checkins,
    show_insights,
    get_demo_checkins,
    generate_openai_feedback,
    show_demo_coaching,
    build_image_prompt,
    generate_image_from_prompt,
    reflect_on_last_action    
)

from openai_score_with_explanation import generate_openai_score
from checkin_utils import overlay_coaching_text

from delete_user_utils import delete_account_from_firebase, delete_all_user_checkins



st.set_page_config(page_title="Daily Check-In App", layout="centered")
st.title("🏁 Welcome to the Daily Check-In App")

mode = st.radio("Choose your mode:", ["🎯 Demo Mode", "🙋‍♂️ User Mode"])
# app.py (very top, before st.set_page_config or any widgets)
from google_sheet import get_all_checkins_cached

# warm the cache immediately
get_all_checkins_cached()

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
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        user_email, user_exists, authenticated = email_step_authentication()
        login_attempted = st.session_state.get("login_attempted", False)
        signup_attempted = st.session_state.get("signup_attempted", False)
        
        if st.session_state.get("reset_password_clicked", False):
            email_to_use = st.session_state.get("temp_email", "")
            st.write("🔧 Reset password function was triggered.")
            send_password_reset_email(email_to_use)
            # Reset the flag so it doesn't run again on next rerun
            st.session_state["reset_password_clicked"] = False
        
        elif authenticated:
            if not user_email:
                user_email = "unknown@example.com"
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = user_email
            st.rerun()
        elif user_email and (login_attempted or signup_attempted):
            st.error("❌ Login issue. Try again.")
    else:
        user_email = st.session_state.get("user_email", "unknown@example.com")
        st.success(f"✅ Logged in as: {user_email}")
        user_action = "🆕 New Check-In"

        df = load_user_checkins(user_email)
        if df is not None and not df.empty:
            #user_action = st.radio("Choose Action", ["New Check-In", "View Past Insights", "Delete My Account"]) #st.selectbox("What would you like to do?", ("📈 View Past Insights", "🆕 New Check-In"))
             # Reflect on last coaching actions
            reflect_on_last_action(df)
            user_action = st.radio("Choose Action", ["🆕 New Check-In", "📈 View Past Insights", "🗑 Delete My Account"])


        if user_action == "🗑 Delete My Account":
            st.warning("⚠️ This will permanently delete your check-ins and Firebase account.")
            if st.button("❗ Confirm Deletion"):
                success1 = delete_all_user_checkins(user_email)
                success2 = delete_account_from_firebase(st.session_state.get("id_token"))
                if success1 and success2:
                    st.success("✅ Your account and check-ins were deleted.")
                else:
                    st.warning("⚠️ Some parts of deletion may have failed.")
                st.stop()

        if user_action == "📈 View Past Insights":
            show_insights(df)
            if st.button("🚪 Sign Out"):
                st.session_state.clear()
                st.rerun()

        

        if user_action == "🆕 New Check-In":
            with st.form("checkin_form"):
                canvas_answers = ask_questions(key_prefix="form_")
                submitted = st.form_submit_button("Submit and Save Check-In")

            if submitted:
                st.subheader("🧠 Coaching Feedback from AI")
                with st.spinner("Generating insights..."):
                    score, insights = generate_openai_feedback(canvas_answers)
                    st.markdown(insights)

                try:
                    save_checkin(user_email, canvas_answers, score, recommendation=insights)
                except Exception as e:
                    import traceback
                    st.error(f"❌ Failed to save check-in: {e}")
                    st.code(traceback.format_exc(), language="python")

        if user_action == "📈 View Past Insights":
            show_insights(df)
            if st.button("🚪 Sign Out"):
                st.session_state.clear()
                st.rerun()

        if user_action == "🆕 New Check-In":
            canvas_answers = ask_questions()
            if st.button("Submit and Save Check-In"):
                #st.info("🔄 Calculating your dynamic score...")
                #score = generate_score(canvas_answers)
                #score, justification = generate_openai_score(canvas_answers)
                #st.success(f"✅ Your total score is **{score}/25**")
                #st.markdown(f"🧾 *{justification}*")
                st.subheader("🧠 Coaching Feedback from AI")
                with st.spinner("Generating insights..."):
                    score, insights = generate_openai_feedback(canvas_answers)
                    st.markdown(insights)
                    #img_prompt = build_image_prompt(insights)
                    #image_url = generate_image_from_prompt(img_prompt)
                    #if image_url:
                    #    image_with_text = overlay_coaching_text(image_url, action_items)
                    #    st.image(image_with_text, caption="Your coaching visualization + key actions", use_container_width=True)


                try:
                    save_checkin(user_email, canvas_answers, score, recommendation=insights)
                    #st.success("✅ Check-in successfully saved!")
                except Exception as e:
                    import traceback
                    st.error(f"❌ Failed to save check-in: {e}")
                    st.code(traceback.format_exc(), language="python")
