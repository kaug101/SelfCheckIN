import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

GOOGLE_SHEET_ID = "1-_qYgfLjxnxfwo-sNkkM6xEDWwEAmtizUP0n9aUQS40"

def get_worksheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials_dict = st.secrets["GCP"]
    creds = service_account.Credentials.from_service_account_info(credentials_dict)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_ID)
    return sheet.sheet1

def append_checkin_to_sheet(data_dict):
    try:
        worksheet = get_worksheet()
        headers = worksheet.row_values(1)
        row = [data_dict.get(header, "") for header in headers]
        worksheet.append_row(row)
        st.success("✅ Successfully saved check-in to Google Sheet.")
    except Exception as e:
        st.error(f"❌ Failed to write to Google Sheets: {e}")
