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
#   UTILITAIRE : TROUVER L'INDEX D'UN EMAIL DANS LA SHEET
# =========================================================
def find_index_by_email(email: str):
    rows = sheet.get_all_values()
    email = email.strip().lower()

    for i in range(1, len(rows)):  # ignorer header
        if rows[i][2].strip().lower() == email:
            return i  # index de la ligne dans Google Sheet (0-based)
    return -1


# =========================================================
#   ROUTE : RÉCEPTION FORMULAIRE → GOOGLE SHEET
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
        
        # === Colonnes ajoutées (PDF envoyé + date/heure) ===
        "0",        # PDF envoyé ? (0 = non, 1 = oui)
        ""          # date/heure envoi PDF
    ]

    sheet.append_row(row)

    return {"success": True, "message": "Formulaire enregistré."}


# =========================================================
#   ROUTE : LIST (RENVOIE TOUTES LES RÉPONSES)
# =========================================================
@app.get("/list")
def listing():
    rows = sheet.get_all_values()
    results = rows[1:]  # ignorer header
    return {"rows": results}


# =========================================================
#   ROUTE : CALCUL COMPLET RETRAITE → JSON
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

    resultat = calcul_complet_retraite(donnees)

    return resultat


# =========================================================
#   ENVOI EMAIL via BREVO
# =========================================================
def envoyer_email_avec_pdf(destinataire, prenom, pdf_path):

    API_KEY = os.getenv("BREVO_API_KEY")
    if not API_KEY:
        raise Exception("BREVO_API_KEY manquant !")

    with open(pdf_path, "rb") as f:
        pdf_data = base64.b64encode(f.read()).decode()

    url = "https://api.brevo.com/v3/smtp/email"

    payload = {
        "sender": {"email": "theo.maretraitesuisse@gmail.com"},
        "to": [{"email": destinataire}],
        "subject": f"Votre estimation retraite – {prenom}",
        "htmlContent": """
            <p>Bonjour,</p>
            <p>Veuillez trouver ci-joint votre analyse retraite complète.</p>
            <p>Bien cordialement,<br>Ma Retraite Suisse</p>
        """,
        "attachment": [
            {
                "name": "estimation_retraite.pdf",
                "content": pdf_data
            }
        ]
    }

    headers = {
        "accept": "application/json",
        "api-key": API_KEY,
        "content-type": "application/json"
    }

    requests.post(url, json=payload, headers=headers)


# =========================================================
#   ROUTE : GÉNÉRER + ENVOYER PDF + METTRE À JOUR LA SHEET
# =========================================================
@app.post("/envoyer-mail-email")
def envoyer_pdf(email: str):
    index = find_index_by_email(email)
    if index == -1:
        return {"success": False, "error": "email introuvable"}

    row = sheet.get_all_values()[index]

    # Données pour PDF
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

    # Calcul + PDF
    resultat = calcul_complet_retraite(donnees)
    pdf_path = generer_pdf_estimation(donnees, resultat)

    # Envoi email
    envoyer_email_avec_pdf(
        destinataire=donnees["email"],
        prenom=donnees["prenom"],
        pdf_path=pdf_path
    )

    # === Mise à jour Google Sheet ===
    sheet.update_cell(index + 1, 19, "1")  # PDF envoyé (colonne 18 → index 19)
    sheet.update_cell(index + 1, 20, datetime.now().strftime("%d.%m.%Y - %H:%M"))

    return {"success": True, "message": "PDF envoyé au client."}


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
    admin_tokens[token] = time.time() + 600  # expire dans 10 minutes

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
