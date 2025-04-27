import streamlit as st
import pyrebase

firebase_config = st.secrets["FIREBASE_CONFIG"]

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

def google_login():
    st.title("Sign in with Firebase")
    
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    login_button = st.button("Sign In")
    register_button = st.button("Create Account")
    
    if login_button:
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state["user_email"] = email
            st.success("✅ Logged in successfully!")
        except Exception as e:
            st.error(f"❌ Failed to login: {e}")
    
    if register_button:
        try:
            user = auth.create_user_with_email_and_password(email, password)
            st.session_state["user_email"] = email
            st.success("✅ Account created successfully!")
        except Exception as e:
            st.error(f"❌ Failed to create account: {e}")
    
    return st.session_state.get("user_email")
