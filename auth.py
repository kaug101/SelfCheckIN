import streamlit as st
import requests

FIREBASE_API_KEY = st.secrets["FIREBASE_API_KEY"]  # 🔥 Add this to secrets.toml

FIREBASE_REST_SIGNIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_REST_SIGNUP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"

def google_login():
    st.title("Sign In with Firebase (REST API)")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    col1, col2 = st.columns(2)
    login_clicked = col1.button("Login")
    signup_clicked = col2.button("Sign Up")

    if login_clicked:
        try:
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            res = requests.post(FIREBASE_REST_SIGNIN_URL, json=payload)
            res.raise_for_status()
            user_info = res.json()
            st.session_state["user_email"] = user_info["email"]
            st.session_state["id_token"] = user_info["idToken"]
            st.success("✅ Logged in successfully!")
        except Exception as e:
            st.error(f"❌ Failed to login: {e}")

    if signup_clicked:
        try:
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            res = requests.post(FIREBASE_REST_SIGNUP_URL, json=payload)
            res.raise_for_status()
            user_info = res.json()
            st.session_state["user_email"] = user_info["email"]
            st.session_state["id_token"] = user_info["idToken"]
            st.success("✅ Account created and logged in successfully!")
        except Exception as e:
            st.error(f"❌ Failed to create account: {e}")

    return st.session_state.get("user_email")
