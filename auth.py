import streamlit as st
import requests
import os 

FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
FIREBASE_REST_SIGNIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_REST_SIGNUP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
FIREBASE_REST_RESET_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"

def firebase_login(email: str, password: str) -> tuple[bool, str]:
    payload = {"email": email, "password": password, "returnSecureToken": True}
    try:
        res = requests.post(FIREBASE_REST_SIGNIN_URL, json=payload)
        res.raise_for_status()
        return True, res.json().get("idToken")
    except Exception as e:
        return False, None


def firebase_signup(email: str, password: str) -> tuple[bool, str]:
    payload = {"email": email, "password": password, "returnSecureToken": True}
    try:
        res = requests.post(FIREBASE_REST_SIGNUP_URL, json=payload)
        res.raise_for_status()
        return True, res.json().get("idToken")
    except Exception as e:
        return False, None


def send_password_reset_email(email: str) -> bool:
    payload = {"requestType": "PASSWORD_RESET", "email": email}
    try:
        res = requests.post(FIREBASE_REST_RESET_URL, json=payload)
        res.raise_for_status()
        return True
    except Exception:
        return False



