import os
import json
import gspread
from fastapi import FastAPI
from google.oauth2.service_account import Credentials
from fastapi.middleware.cors import CORSMiddleware


@app.get("/")
def root():
    return {"status": "ok"}

app = FastAPI()

# Autoriser Shopify (frontend) à contacter ton backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# Charger les credentials Google depuis Render (.env)
creds_info = json.loads(os.getenv("GOOGLE_CREDS_JSON"))

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
client = gspread.authorize(creds)

# Nom de ton Google Sheet (dans Render)
sheet_name = os.getenv("SHEET_NAME")
sheet = client.open(sheet_name).sheet1

@app.get("/ping")
def ping():
    return {"status": "alive"}

@app.post("/submit")
async def submit_form(data: dict):

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
        data.get("souhaits"),
    ]

    sheet.append_row(row)
    return {"status": "success"}
