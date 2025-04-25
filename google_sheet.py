
import gspread
from oauth2client.service_account import ServiceAccountCredentials

GOOGLE_SHEET_ID = "your_google_sheet_id_here"

def get_worksheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_ID)
    worksheet = sheet.sheet1
    return worksheet

def append_checkin_to_sheet(data_dict):
    worksheet = get_worksheet()
    row = [data_dict.get(key, "") for key in worksheet.row_values(1)]
    worksheet.append_row(row)
