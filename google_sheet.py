
import gspread
from google.oauth2 import service_account
import base64
import json
import streamlit as st

GOOGLE_SHEET_ID = "your_google_sheet_id_here"

def get_worksheet():
    encoded_credentials = st.secrets["GCP"]["service_account_base64"]
    decoded = base64.b64decode(encoded_credentials).decode("utf-8")
    credentials_dict = json.loads(decoded)
    credentials = service_account.Credentials.from_service_account_info(credentials_dict)
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(GOOGLE_SHEET_ID)
    return sheet.sheet1

def append_checkin_to_sheet(data_dict):
    try:
        worksheet = get_worksheet()
        headers = worksheet.row_values(1)
        row = [data_dict.get(header, "") for header in headers]
        worksheet.append_row(row)
        st.success("✅ Successfully saved check-in to Google Sheets.")
    except Exception as e:
        import traceback
        st.error("❌ Failed to write to Google Sheets.")
        st.code(traceback.format_exc(), language="python")
