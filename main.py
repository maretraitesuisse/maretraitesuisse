print("=== Backend MaretraiteSuisse chargé ===")

import os
import json
import time
import uuid
import requests
import base64
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.service_account import Credentials
import gspread

# === MODULES INTERNES ===
from simulateur_avs_lpp import calcul_complet_retraite
from pdf_generator import generer_pdf_estimation

# =========================================================
#                FASTAPI + CORS
# =========================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
#                GOOGLE SHEET
# =========================================================
creds_json = os.getenv("GOOGLE_SHEET_CREDENTIALS")
if not creds_json:
    raise Exception("⚠ GOOGLE_SHEET_CREDENTIALS manquant dans Render !")

creds_info = json.loads(creds_json)

creds = Credentials.from_service_account_info(
    creds_info,
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)

client = gspread.authorize(creds)
sheet_name = os.getenv("SHEET_NAME", "reponses_clients")
sheet = client.open(sheet_name).sheet1


# =========================================================
#   UTILITAIRE : TROUVER EMAIL
# =========================================================
def find_index_by_email(email: str):
    rows = sheet.get_all_values()
    email = email.strip().lower()

    for i in range(1, len(rows)):
        if rows[i][2].strip().lower() == email:
            return i
    return -1


# =========================================================
#   ENVOI EMAILS BREVO
# =========================================================
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
if not BREVO_API_KEY:
    raise Exception("BREVO_API_KEY manquant !")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"

def envoyer_email_confirmation(destinataire, prenom):
    payload = {
        "templateId": 1,
        "to": [{"email": destinataire}],
        "params": {"prenom": prenom},
        "sender": {"email": "noreply@maretraitesuisse.com", "name": "Ma Retraite Suisse"}
    }
    requests.post(BREVO_URL, json=payload, headers={
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    })


def envoyer_email_resultat(destinataire, prenom, pdf_path):
    with open(pdf_path, "rb") as f:
        pdf_data = base64.b64encode(f.read()).decode()

    payload = {
        "templateId": 2,
        "to": [{"email": destinataire}],
        "params": {"prenom": prenom},
        "attachment": [
            {"name": "estimation_retraite.pdf", "content": pdf_data}
        ],
        "sender": {"email": "noreply@maretraitesuisse.com", "name": "Ma Retraite Suisse"}
    }
    requests.post(BREVO_URL, json=payload, headers={
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    })


def envoyer_email_avis(destinataire, prenom):
    payload = {
        "templateId": 3,
        "to": [{"email": destinataire}],
        "params": {"prenom": prenom},
        "sender": {"email": "noreply@maretraitesuisse.com", "name": "Ma Retraite Suisse"}
    }
    requests.post(BREVO_URL, json=payload, headers={
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    })


# =========================================================
#   ROUTE : FORMULAIRE → SHEET + MAIL CONFIRM
# =========================================================
@app.post("/submit")
def submit(data: dict):

    row = [
        data.get("prenom", ""),
        data.get("nom", ""),
        data.get("email", ""),
        data.get("telephone", ""),
        data.get("statut_civil", ""),
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
        data.get("souhaits", ""),

        "0",  
        "",   
        "0"  
    ]

    sheet.append_row(row)

    envoyer_email_confirmation(data.get("email"), data.get("prenom"))

    return {"success": True}


# =========================================================
#   ROUTE : CALCUL
# =========================================================
@app.get("/calcul-email")
def calcul_email(email: str):
    index = find_index_by_email(email)
    if index == -1:
        return {"error": "email introuvable"}

    row = sheet.get_all_values()[index]

    donnees = {
        "prenom": row[0],
        "nom": row[1],
        "email": row[2],
        "telephone": row[3],
        "statut_civil": row[4],
        "age_actuel": int(row[5]),
        "age_retraite": int(row[6]),
        "salaire_annuel": float(row[7]),
        "revenu_brut": float(row[8]),
        "salaire_moyen_avs": float(row[9]),
        "annees_avs": int(row[10]),
        "annees_be": int(row[11]),
        "annees_ba": int(row[12]),
        "capital_lpp": float(row[13]),
        "rente_conjoint": float(row[14]) if row[14] else 0,
        "annees_suisse": int(row[15]),
        "canton": row[16],
        "souhaits": row[17]
    }

    return calcul_complet_retraite(donnees)


# =========================================================
#   ROUTE : ENVOI PDF
# =========================================================
@app.post("/envoyer-mail-email")
def envoyer_pdf(email: str):
    index = find_index_by_email(email)
    if index == -1:
        return {"success": False}

    row = sheet.get_all_values()[index]

    donnees = {
        "prenom": row[0],
        "nom": row[1],
        "email": row[2],
        "telephone": row[3],
        "statut_civil": row[4],
        "age_actuel": int(row[5]),
        "age_retraite": int(row[6]),
        "salaire_annuel": float(row[7]),
        "revenu_brut": float(row[8]),
        "salaire_moyen_avs": float(row[9]),
        "annees_avs": int(row[10]),
        "annees_be": int(row[11]),
        "annees_ba": int(row[12]),
        "capital_lpp": float(row[13]),
        "rente_conjoint": float(row[14]) if row[14] else 0,
        "annees_suisse": int(row[15]),
        "canton": row[16],
        "souhaits": row[17]
    }

    resultat = calcul_complet_retraite(donnees)
    pdf_path = generer_pdf_estimation(donnees, resultat)

    envoyer_email_resultat(donnees["email"], donnees["prenom"], pdf_path)

    sheet.update_cell(index + 1, 19, "1")
    sheet.update_cell(index + 1, 20, datetime.now().strftime("%d.%m.%Y - %H:%M"))

    return {"success": True}


# =========================================================
#   ROUTE CRON
# =========================================================
@app.get("/cron-avis")
def cron_avis():

    rows = sheet.get_all_values()

    for idx in range(1, len(rows)):
        row = rows[idx]

        pdf_envoye = row[18]
        avis_envoye = row[20]
        email = row[2]
        prenom = row[0]

        if pdf_envoye == "1" and avis_envoye == "0":

            envoyer_email_avis(email, prenom)

            sheet.update_cell(idx + 1, 21, "1")

    return {"success": True}


# =========================================================
#   ADMIN TOKEN
# =========================================================
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ADMIN123")
admin_tokens = {}

@app.get("/admin-login")
def admin_login(password: str):
    if password != ADMIN_PASSWORD:
        return {"success": False}

    token = str(uuid.uuid4())
    admin_tokens[token] = time.time() + 600

    return {"success": True, "token": token}


@app.get("/verify-admin-token")
def verify_token(token: str):
    if token not in admin_tokens:
        return {"allowed": False}

    if time.time() > admin_tokens[token]:
        del admin_tokens[token]
        return {"allowed": False}

    return {"allowed": True}


# =========================================================
#   ROUTE LIST — FORMAT rows POUR TON ADMIN
# =========================================================
@app.get("/list")
def list_clients():
    try:
        rows = sheet.get_all_values()
        return {"rows": rows}
    except Exception as e:
        return {"error": str(e)}


# =========================================================
#   PING
# =========================================================
@app.get("/ping")
def ping():
    return {"status": "alive"}
