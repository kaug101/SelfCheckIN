import streamlit as st
import requests

FIREBASE_API_KEY = st.secrets["FIREBASE_API_KEY"]
FIREBASE_REST_SIGNIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_REST_SIGNUP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
FIREBASE_REST_RESET_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"

def send_password_reset_email(email):
    st.info("🔧 Reset password function was entered.")
    if not email:
        st.error("⚠️ No email provided. Please enter your email first.")
        return
        
    payload = {"requestType": "PASSWORD_RESET", "email": email}
    try:
        res = requests.post(FIREBASE_REST_RESET_URL, json=payload)
        data = res.json()
        if "error" in data:
            st.error(f"❌ Firebase error: {data['error']['message']}")
        else:
            st.success(f"📧 Password reset email sent to {email}.")
    except Exception as e:
        st.error(f"❌ Failed to send reset email: {e}")

def email_step_authentication():
    authenticated = False
    login_attempted = False
    signup_attempted = False

    #st.write("Session State:", dict(st.session_state))

    if st.session_state.get("reset_password_clicked", False):
        email_to_use = st.session_state.get("temp_email", "")
        st.write("🔧 Reset password function was triggered.")
        send_password_reset_email(email_to_use)
        # Reset the flag so it doesn't run again on next rerun
        st.session_state["reset_password_clicked"] = False


    email = st.text_input("Enter your email")

    if email:
        st.session_state["temp_email"] = email
    
    auth_mode = st.radio("What would you like to do?", ["🔓 Login", "🆕 Sign Up"])

    if email:
        if auth_mode == "🔓 Login":
            password = st.text_input("Password", type="password", key="login_pw")
            login_failed = False
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
                    st.error(f"❌ Login failed")
                    login_failed = True
            
            if login_failed:
                if st.button("Reset Password"):
                    st.info("🔧 Reset password session state was changed.")
                    st.session_state["reset_password_clicked"] = True
            

                    

        elif auth_mode == "🆕 Sign Up":
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
                        st.error(f"❌ Signup failed: {e}")
                else:
                    st.error("❌ Passwords do not match or are empty!")

    st.session_state["login_attempted"] = login_attempted
    st.session_state["signup_attempted"] = signup_attempted

    return email if authenticated else None, None, authenticated
