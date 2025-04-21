
import streamlit as st

def google_login():
    st.markdown("### Sign in with Google")
    user_email = st.text_input("Email (Google Sign-In placeholder)")
    if st.button("Continue"):
        st.session_state["user_email"] = user_email
    return st.session_state.get("user_email")
