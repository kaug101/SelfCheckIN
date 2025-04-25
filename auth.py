import streamlit as st
import pyrebase

firebase_config = st.secrets["FIREBASE_CONFIG"]

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

def google_login():
    st.markdown("### 🔐 Sign in with your email and password")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    col1, col2 = st.columns(2)

    if col1.button("Sign In"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state["user_email"] = email
            st.success("✅ Logged in successfully!")
        except Exception as e:
            st.error(f"Login failed: {e}")

    if col2.button("Create Account"):
        try:
            user = auth.create_user_with_email_and_password(email, password)
            st.session_state["user_email"] = email
            st.success("✅ Account created successfully!")
        except Exception as e:
            st.error(f"Account creation failed: {e}")
    
    return st.session_state.get("user_email")
