
import streamlit as st
import requests
import pandas as pd
from google_sheet import get_all_checkins

FIREBASE_API_KEY = st.secrets["FIREBASE_API_KEY"]
FIREBASE_REST_SIGNIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_REST_SIGNUP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"

def email_step_authentication():
    email = st.text_input("Enter your email")

    user_exists = False
    authenticated = False
    login_attempted = False
    signup_attempted = False

    if email:
        all_data = get_all_checkins()
        if not all_data.empty:
            user_exists = email in all_data["user"].unique()

        if user_exists:
            st.success("✅ Existing user found. Please login.")
            password = st.text_input("Password", type="password", key="login_pw")
            if st.button("Login"):
                login_attempted = True
                try:
                   payload = {"email": email, "password": password, "returnSecureToken": True}
                   res = requests.post(FIREBASE_REST_SIGNIN_URL, json=payload)
                   res.raise_for_status()
                   res_data = res.json()
                   authenticated = True
                   st.session_state["user_email"] = email
                   st.session_state["user_password"] = password
                   st.session_state["id_token"] = res_data.get("idToken")
                except Exception as e:
                   st.error(f"❌ Failed to login: {e}")
        else:
            st.info("🆕 New user. Please sign up.")
            password = st.text_input("Choose a password", type="password", key="signup_pw")
            password_confirm = st.text_input("Confirm password", type="password", key="signup_confirm_pw")
            if st.button("Sign Up"):
                signup_attempted = True
                if password == password_confirm and password != "":
                    try:
                        payload = {"email": email, "password": password, "returnSecureToken": True}
                        res = requests.post(FIREBASE_REST_SIGNUP_URL, json=payload)
                        res.raise_for_status()
                        res_data = res.json()
                        authenticated = True
                        st.session_state["user_email"] = email
                        st.session_state["user_password"] = password
                        st.session_state["id_token"] = res_data.get("idToken")
                    except Exception as e:
                        st.error(f"❌ Failed to signup: {e}")
                else:
                    st.error("❌ Passwords do not match or are empty!")

    st.session_state["login_attempted"] = login_attempted
    st.session_state["signup_attempted"] = signup_attempted

    return email if authenticated else None, user_exists, authenticated
