
import streamlit as st
import requests

FIREBASE_API_KEY = st.secrets["FIREBASE_CONFIG"]["apiKey"]

def firebase_login():
    st.markdown("### 🔐 Firebase Email/Password Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    action = st.radio("Choose action", ["Login", "Sign Up"])

    if st.button("Submit"):
        if action == "Login":
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
        else:
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        response = requests.post(url, json=payload)
        if response.status_code == 200:
            st.session_state["user_email"] = response.json().get("email")
            st.success(f"✅ {action} successful!")
        else:
            st.error(f"{action} failed: {response.json().get('error', {}).get('message')}")

    return st.session_state.get("user_email")
