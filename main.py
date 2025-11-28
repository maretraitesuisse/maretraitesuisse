import os
import json
import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.service_account import Credentials
import gspread

# =====================
# LOGS
# =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simulateur")

# =====================
# GOOGLE SHEETS via ENV
# =====================
creds_info = json.loads(os.getenv("GOOGLE_CREDS_JSON"))

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
client = gspread.authorize(creds)

sheet_name = os.getenv("SHEET_NAME")
sheet = client.open(sheet_name).sheet1

# =====================
# FASTAPI
# =====================
app = FastAPI()

# =====================
# CORS Shopify
# =====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "https://maretraitesuisse.myshopify.com",
        "https://maretraitesuisse.ch",
        "https://www.maretraitesuisse.ch"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# ENDPOINT PING
# =====================
@app.get("/ping")
def ping():
    return {"status": "alive"}

# =====================
# DEBUG
# =====================
@app.post("/debug")
async def debug(request: Request):
    body = await request.body()
    logger.info(f"Body: {body}")
    logger.info("=====================================")
    return {"status": "received"}

# =====================
# SUBMIT FORMULAIRE
# =====================
@app.post("/submit")
async def submit_form(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Erreur JSON Shopify : {e}")
        return {"status": "error", "message": "Invalid JSON"}

    logger.info("===== Nouveau formulaire reçu =====")
    logger.info(data)

    row = [
        data.get("prenom", ""),
        data.get("nom", ""),
        data.get("email", ""),
        data.get("telephone", ""),
        data.get("situation", ""),
        data.get("age_actuel", ""),
        data.get("age_retraite", ""),
        data.get("salaire_annuel", ""),
        data.get("revenu_brut", ""),
        data.get("salaire_moyen_avs", ""),
        data.get("annees_avs", ""),
        data.get("annees_be", ""),
        data.get("annees_ba", ""),
        data.get("capital_lpp", ""),
        data.get("rente_conjoint", ""),
        data.get("annees_suisse", ""),
        data.get("canton", ""),
        data.get("souhaits", "")
    ]

    # =====================
    # GOOGLE SHEET SAFE WRITE AVEC RETRY
    # =====================
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            sheet.append_row(row)
            break
        except Exception as e:
            logger.error(f"Erreur Google Sheet (tentative {attempt+1}) : {e}")
            time.sleep(1)
            if attempt == max_attempts - 1:
                return {"status": "error", "message": "Sheet error"}

    return {"status": "success"}

