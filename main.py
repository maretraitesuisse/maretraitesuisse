print("=== Backend MaretraiteSuisse chargé ===")

import os
import time
import uuid
import base64
import requests
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
#                EMAILS BREVO
# =========================================================
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
if not BREVO_API_KEY:
    raise Exception("BREVO_API_KEY manquant")

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
#   ROUTE : SUBMIT FORMULAIRE
# =========================================================
@app.post("/submit")
def submit(data: dict):
    """
    À terme : insertion en base SQL
    Pour l'instant : simple validation + mail
    """
    envoyer_email_confirmation(data.get("email"), data.get("prenom"))
    return {"success": True}

# =========================================================
#   ROUTE : CALCUL RETRAITE
# =========================================================
@app.post("/calcul")
def calcul(data: dict):
    """
    Appel direct du moteur AVS/LPP
    """
    resultat = calcul_complet_retraite(data)
    return resultat

# =========================================================
#   ROUTE : GENERATION + ENVOI PDF
# =========================================================
@app.post("/envoyer-pdf")
def envoyer_pdf(data: dict):
    resultat = calcul_complet_retraite(data)
    pdf_path = generer_pdf_estimation(data, resultat)
    envoyer_email_resultat(data["email"], data["prenom"], pdf_path)
    return {"success": True}

# =========================================================
#   ROUTE CRON (avis)
# =========================================================
@app.post("/cron-avis")
def cron_avis(data: dict):
    envoyer_email_avis(data["email"], data["prenom"])
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
#   PING
# =========================================================
@app.get("/ping")
def ping():
    return {"status": "alive"}
