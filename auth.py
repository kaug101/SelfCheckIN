import streamlit as st
import requests

FIREBASE_API_KEY = st.secrets["FIREBASE_API_KEY"]
FIREBASE_REST_SIGNIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_REST_SIGNUP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
FIREBASE_REST_RESET_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"
FIREBASE_REST_LOOKUP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={FIREBASE_API_KEY}"

def send_password_reset_email(email):
    payload = {
        "requestType": "PASSWORD_RESET",
        "email": email
    }
    try:
        res = requests.post(FIREBASE_REST_RESET_URL, json=payload)
        res.raise_for_status()
        st.success(f"📧 Password reset email sent to {email}.")
    except Exception as e:
        st.error(f"❌ Failed to send reset email: {e}")

def firebase_user_exists(email: str) -> bool:
    try:
        res = requests.post(FIREBASE_REST_LOOKUP_URL, json={"email": [email]})
        data = res.json()
        return "users" in data
    except Exception as e:
        st.warning(f"⚠️ Could not check user: {e}")
        return False

def email_step_authentication():
    email = st.text_input("Enter your email")

    authenticated = False
    login_attempted = False
    signup_attempted = False
    user_exists = None

    if email:
        user_exists = firebase_user_exists(email)

        if user_exists:
            st.success("✅ User found. Please login.")
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
                    if st.button("Reset Password"):
                        send_password_reset_email(email)
        else:
            st.info("🆕 No Firebase account found. Please sign up.")
            pw1 = st.text_input("Choose a password", type="password", key="signup_pw")
            pw2 = st.text_input("Confirm password", type="password", key="signup_confirm_pw")
            if st.button("Sign Up"):
                signup_attempted = True
                if pw1 == pw2 and pw1 != "":
                    try:
                        payload = {"email": email, "password": pw1, "returnSecureToken": True}
                        res = requests.post(FIREBASE_REST_SIGNUP_URL, json=payload)
                        res.raise_for_status()
                        res_data = res.json()
                        authenticated = True
                        st.session_state["user_email"] = email
                        st.session_state["user_password"] = pw1
                        st.session_state["id_token"] = res_data.get("idToken")
                    except Exception as e:
                        st.error(f"❌ Failed to signup: {e}")
                else:
                    st.error("❌ Passwords do not match or are empty!")

    st.session_state["login_attempted"] = login_attempted
    st.session_state["signup_attempted"] = signup_attempted

    return email if authenticated else None, user_exists, authenticated
