import streamlit as st
import pyrebase

firebase_config = st.secrets["FIREBASE_CONFIG"]

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

def google_login():
    st.title("Sign in with Google")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    login_button = st.button("Sign In")
    register_button = st.button("Create Account")
    
    if login_button:
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state["user_email"] = email
            st.success("Logged in successfully!")
        except:
            st.error("Failed to login. Try again.")
    
    if register_button:
        try:
            user = auth.create_user_with_email_and_password(email, password)
            st.session_state["user_email"] = email
            st.success("Account created!")
        except:
            st.error("Failed to create account. Try again.")
    
    return st.session_state.get("user_email")
