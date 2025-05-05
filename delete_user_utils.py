
import streamlit as st
import requests
import pandas as pd
from google_sheet import get_all_checkins, update_google_sheet

FIREBASE_API_KEY = st.secrets["FIREBASE_API_KEY"]
FIREBASE_REST_DELETE_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:delete?key={FIREBASE_API_KEY}"

def delete_account_from_firebase(id_token):
    try:
        res = requests.post(FIREBASE_REST_DELETE_URL, json={"idToken": id_token})
        res.raise_for_status()
        return True
    except Exception as e:
        st.error(f"❌ Firebase deletion failed: {e}")
        return False

def delete_all_user_checkins(user_email):
    try:
        df = get_all_checkins()
        if not df.empty:
            updated_df = df[df["user"] != user_email]
            update_google_sheet(updated_df)
            return True
        else:
            return False
    except Exception as e:
        st.error(f"❌ Failed to update Google Sheet: {e}")
        return False
