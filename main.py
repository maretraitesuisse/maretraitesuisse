import os
import json
import gspread
from fastapi import FastAPI, Request
from google.oauth2.service_account import Credentials
from fastapi.middleware.cors import CORSMiddleware
import logging

# =====================
# LOGGING
# =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simulateur")

# =====================
# APP FastAPI
# =====================
app = FastAPI()

# Autoriser le frontend Shopify à parler au backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # on peut restreindre plus tard
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# =====================
# AUTH GOOGLE SHEETS
# =====================
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
SHEET_NAME = os.getenv("SHEET_NAME", "reponses_clients")

creds_info = json.loads(GOOGLE_CREDS_JSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
client = gspread.authorize(creds)

# Ouvrir le sheet et pointer sur l'onglet "Feuille 1"
sheet = client.open(SHEET_NAME).worksheet("Feuille 1")

# =====================
# ROUTES
# =====================
@app.get("/ping")
def ping():
    return {"status": "alive"}

@app.post("/submit")
async def submit_form(request: Request):
    data = await request.json()
    logger.info("===== Nouveau formulaire reçu =====")
    logger.info(data)

    # Préparer la ligne à écrire
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
        logger.info(f"Ligne ajoutée avec succès dans l'onglet 'Feuille 1'")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Erreur ajout ligne : {e}")
        return {"status": "error", "detail": str(e)}

