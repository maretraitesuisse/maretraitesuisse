import os
import json
from google.oauth2.service_account import Credentials
import gspread
from fastapi import FastAPI

app = FastAPI()

# Récupère le JSON du compte service depuis Render
creds_info = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
client = gspread.authorize(creds)

sheet_name = os.getenv("SHEET_NAME")
sheet = client.open(sheet_name).sheet1

@app.post("/submit")
async def submit_form(data: dict):
    # Exemple d’ajout dans la feuille
    row = [
        data.get("prenom"),
        data.get("nom"),
        data.get("email"),
        data.get("telephone"),
        data.get("situation"),
        data.get("age_actuel"),
        data.get("age_retraite"),
        data.get("salaire_annuel"),
        data.get("revenu_brut"),
        data.get("salaire_moyen_avs"),
        data.get("annees_avs"),
        data.get("annees_be"),
        data.get("annees_ba"),
        data.get("capital_lpp"),
        data.get("rente_conjoint"),
        data.get("annees_suisse"),
        data.get("canton"),
        data.get("souhaits")
    ]
    sheet.append_row(row)
    return {"status": "success"}
