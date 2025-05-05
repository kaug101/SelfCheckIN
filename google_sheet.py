import gspread
from google.oauth2 import service_account
import base64
import json
import streamlit as st
import pandas as pd

GOOGLE_SHEET_ID = "1-_qYgfLjxnxfwo-sNkkM6xEDWwEAmtizUP0n9aUQS40"


def get_worksheet():
    encoded_credentials = st.secrets["GCP"]["service_account_base64"]
    decoded = base64.b64decode(encoded_credentials).decode("utf-8")
    credentials_dict = json.loads(decoded)

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = service_account.Credentials.from_service_account_info(credentials_dict, scopes=scope)
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(GOOGLE_SHEET_ID)
    return sheet.sheet1

def append_checkin_to_sheet(entry: dict):
    try:
        worksheet = get_worksheet()
        header = worksheet.row_values(1)     
        row = [entry.get(col, "") for col in header]
        worksheet.append_row(row)
        st.success("✅ Successfully saved check-in.")
    except Exception as e:
        import traceback
        st.error("❌ Failed to save check-in.")
        st.code(traceback.format_exc(), language="python")


def get_all_checkins():
    try:
        worksheet = get_worksheet()
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        import traceback
        st.error("❌ Failed to load check-ins.")
        st.code(traceback.format_exc(), language="python")
        return None


def update_google_sheet(updated_df):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(
            st.secrets["GCP"], scopes=scope
        )
        client = gspread.authorize(creds)

        sheet = client.open_by_key(st.secrets["GOOGLE_SHEET_ID"])
        worksheet = sheet.sheet1

        worksheet.clear()  # ⚠️ clears existing sheet
        worksheet.update([updated_df.columns.values.tolist()] + updated_df.values.tolist())
        return True
    except Exception as e:
        st.error(f"❌ Failed to update sheet: {e}")
        return False
