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
try:
    creds_info = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
except Exception as e:
    logger.error(f"Impossible de lire GOOGLE_CREDS_JSON: {e}")
    creds_info = None

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(creds)
except Exception as e:
    logger.error(f"Erreur authentification Google Sheets: {e}")
    client = None

sheet_name = os.getenv("SHEET_NAME")
sheet = None
if client:
    try:
        sheet = client.open(sheet_name).sheet1
        logger.info(f"Sheet '{sheet_name}' ouvert avec succès")
    except Exception as e:
        logger.error(f"Erreur ouverture sheet '{sheet_name}': {e}")

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

    if sheet is None:
        logger.error("Sheet non initialisé, impossible d'écrire")
        return {"status": "error", "message": "Sheet not initialized"}

    # =====================
    # GOOGLE SHEET SAFE WRITE AVEC RETRY
    # =====================
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            sheet.append_row(row)
            logger.info(f"Ligne ajoutée avec succès dans '{sheet_name}'")
            break
        except Exception as e:
            logger.error(f"Erreur Google Sheet (tentative {attempt+1}) : {e}")
            time.sleep(1)
            if attempt == max_attempts - 1:
                return {"status": "error", "message": "Sheet error"}

    return {"status": "success"}

