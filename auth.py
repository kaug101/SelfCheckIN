import streamlit as st
import requests

FIREBASE_API_KEY = st.secrets["FIREBASE_API_KEY"]
FIREBASE_REST_SIGNIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_REST_SIGNUP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
FIREBASE_REST_RESET_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"

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

def check_if_user_exists(email):
    payload = {
        "email": email,
        "password": "this-password-will-not-work",
        "returnSecureToken": True
    }
    try:
        res = requests.post(FIREBASE_REST_SIGNIN_URL, json=payload)
        error_msg = res.json().get("error", {}).get("message", "")
        return "INVALID_LOGIN_CREDENTIALS" in error_msg or "INVALID_PASSWORD" in error_msg
    except Exception:
        return False

def email_step_authentication():
    authenticated = False
    login_attempted = False
    signup_attempted = False
    user_exists = None
    email_confirmed = False

    email = st.text_input("Enter your email")

    if email:
        if st.button("Continue"):
            st.session_state["entered_email"] = email
            st.rerun()

    if "entered_email" in st.session_state:
        email = st.session_state["entered_email"]
        user_exists = check_if_user_exists(email)

        st.write(f"**Email:** {email}")
        if user_exists:
            st.success("✅ User exists. Please log in.")
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
            st.info("🆕 No account found. Please sign up.")
            pw1 = st.text_input("Choose a password", type="password", key="signup_pw1")
            pw2 = st.text_input("Confirm password", type="password", key="signup_pw2")
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
