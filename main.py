# ---- Google Sheets (Render ENV)
creds_json = os.getenv("GOOGLE_SHEET_CREDENTIALS")

if creds_json:
    creds_info = json.loads(creds_json)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open(os.getenv("SHEET_NAME")).sheet1
else:
    # Mode safe: éviter plantage Render
    sheet = None
