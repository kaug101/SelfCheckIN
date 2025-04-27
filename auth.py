
import streamlit as st

def google_login():
    st.markdown("### Sign in with Google (placeholder)")
    user_email = st.text_input("Email")
    if st.button("Continue"):
        st.session_state["user_email"] = user_email
    return st.session_state.get("user_email")
