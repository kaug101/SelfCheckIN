
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# You must set your Google Sheet ID here
GOOGLE_SHEET_ID = "1-_qYgfLjxnxfwo-sNkkM6xEDWwEAmtizUP0n9aUQS40"

def get_worksheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_ID)
    worksheet = sheet.sheet1
    return worksheet

def append_checkin_to_sheet(data_dict):
    worksheet = get_worksheet()
    row = [data_dict.get(key, "") for key in worksheet.row_values(1)]  # match header
    worksheet.append_row(row)
