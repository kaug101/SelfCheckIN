
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import base64
from pathlib import Path

# Decode the service account JSON from Streamlit secrets if needed
sa_path = "service_account.json"
if not Path(sa_path).exists() and "GCP" in st.secrets and "service_account_base64" in st.secrets["GCP"]:
    key_data = base64.b64decode(st.secrets["GCP"]["service_account_base64"])
    with open(sa_path, "wb") as f:
        f.write(key_data)

# Your actual Google Sheet ID
GOOGLE_SHEET_ID = "1-_qYgfLjxnxfwo-sNkkM6xEDWwEAmtizUP0n9aUQS40"

def get_worksheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(sa_path, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_ID)
    worksheet = sheet.sheet1
    return worksheet

def append_checkin_to_sheet(data_dict):
    worksheet = get_worksheet()
    headers = worksheet.row_values(1)
    print("Headers in sheet:", headers)
    print("Data dict keys:", list(data_dict.keys()))
    row = [data_dict.get(key, "") for key in headers]
    try:
        worksheet.append_row(row)
    except Exception as e:
        st.error(f"❌ Failed to write to Google Sheets: {e}")


