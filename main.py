import os
import json
import gspread
from fastapi import FastAPI, Request
from google.oauth2.service_account import Credentials
from fastapi.middleware.cors import CORSMiddleware
import logging

# ======================================================
# LOGGING POUR DEBUG SHOPIFY
# ======================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simulateur")

app = FastAPI()

# ======================================================
# CORS – COMPATIBLE SHOPIFY AVEC PREFLIGHT COMPLET
# ======================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tu pourras restreindre plus tard à ton domaine Shopify
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# CHARGEMENT GOOGLE SHEET
# ======================================================
creds_info = json.loads(os.getenv("GOOGLE_CREDS_JSON"))

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
client = gspread.authorize(creds)

sheet_name = os.getenv("SHEET_NAME")
sheet = client.open(sheet_name).sheet1

# ======================================================
# ENDPOINTS
# ======================================================

@app.get("/ping")
def ping():
    return {"status": "alive"}


# ----------- DEBUG : VOIR CE QUE SHOPIFY ENVOIE ----------- #
@app.post("/debug")
async def debug(request: Request):
    body = await request.body()
    logger.info("========== REQUÊTE SHOPIFY ==========")
    logger.info(f"Headers: {request.headers}")
    logger.info(f"Body: {body}")
    logger.info("=====================================")
    return {"received": True, "raw_body": body.decode()}


# ----------- SUBMIT FORMULAIRE ----------- #
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

    try:
        sheet.append_row(row)
    except Exception as e:
        logger.error(f"Erreur Google Sheet : {e}")
        return {"status": "error", "message": "Sheet error"}

    return {"status": "success"}

