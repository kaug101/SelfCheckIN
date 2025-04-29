
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

    if email:
        all_data = get_all_checkins()
        if not all_data.empty:
            user_exists = email in all_data["user"].unique()

        if user_exists:
            st.success("✅ Existing user found. Please login.")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                try:
                    payload = {"email": email, "password": password, "returnSecureToken": True}
                    res = requests.post(FIREBASE_REST_SIGNIN_URL, json=payload)
                    res.raise_for_status()
                    authenticated = True
                except Exception as e:
                    st.error(f"❌ Failed to login: {e}")
        else:
            st.info("🆕 New user. Please sign up.")
            password = st.text_input("Choose a password", type="password")
            password_confirm = st.text_input("Confirm password", type="password")
            if st.button("Sign Up"):
                if password == password_confirm and password != "":
                    try:
                        payload = {"email": email, "password": password, "returnSecureToken": True}
                        res = requests.post(FIREBASE_REST_SIGNUP_URL, json=payload)
                        res.raise_for_status()
                        authenticated = True
                    except Exception as e:
                        st.error(f"❌ Failed to signup: {e}")
                else:
                    st.error("❌ Passwords do not match or are empty!")

    return email, user_exists, authenticated
