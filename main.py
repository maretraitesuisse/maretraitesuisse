# main.py
# ---------------------------------------------------------------------
# Backend FastAPI pour MARETRAITE SUISSE
# Gère :
#  - soumission de formulaire
#  - communication avec Google Sheets
#  - simulation AVS + LPP
#  - envoi d'email
#  - consultation des données pour l'admin Shopify
# ---------------------------------------------------------------------

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from simulateur import simuler_pilier_complet
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ---------------------------------------------------------------------
# INITIALISATION FASTAPI
# ---------------------------------------------------------------------

app = FastAPI()

# Autorise Shopify + navigateur
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

# Racine pour Render
@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"status": "alive"}


# ---------------------------------------------------------------------
# PARTIE GOOGLE SHEETS
# ---------------------------------------------------------------------

# Identifiants dans variable d'environnement RENDER
SHEET_CREDENTIALS = os.getenv("GOOGLE_SHEET_CREDENTIALS")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

if not SHEET_CREDENTIALS:
    raise Exception("⚠ GOOGLE_SHEET_CREDENTIALS n'est pas configuré dans Render.")

# Convertit la variable d'environnement JSON → dictionnaire
import json
service_account_info = json.loads(SHEET_CREDENTIALS)

# Scopes Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# On construit le client Google
credentials = Credentials.from_service_account_info(
    service_account_info, scopes=SCOPES
)

service = build("sheets", "v4", credentials=credentials)
sheet = service.spreadsheets()


def append_to_sheet(values):
    """
    Ajoute une ligne complète au Google Sheet.
    `values` doit être une liste ordonnée correspondant aux colonnes.
    """
    result = sheet.values().append(
        spreadsheetId=SHEET_ID,
        range="A:Z",
        valueInputOption="RAW",
        body={"values": [values]}
    ).execute()
    return result


def read_sheet():
    """
    Lit toutes les lignes du Google Sheet
    Retourne une liste de lignes
    """
    result = sheet.values().get(
        spreadsheetId=SHEET_ID,
        range="A:Z"
    ).execute()

    return result.get("values", [])


# ---------------------------------------------------------------------
# /submit — Sauvegarde du formulaire Shopify dans Google Sheets
# ---------------------------------------------------------------------
@app.post("/submit")
async def submit_form(data: dict):

    # Harmonisation automatique des noms Shopify → Backend
    statut = data.get("situation", data.get("statut_civil", ""))
    revenu_annuel_brut = data.get("revenu_brut", data.get("revenu_annuel_brut", ""))
    annees_cotisees = data.get("annees_avs", data.get("annees_cotisees", ""))
    be = data.get("annees_be", data.get("be", ""))
    ba = data.get("annees_ba", data.get("ba", ""))

    row = [
        data.get("prenom", ""),
        data.get("nom", ""),
        data.get("email", ""),
        data.get("telephone", ""),
        statut,
        data.get("age_actuel", ""),
        data.get("age_retraite", ""),
        data.get("salaire_annuel", ""),
        revenu_annuel_brut,
        data.get("salaire_moyen_avs", ""),
        annees_cotisees,
        be,
        ba,
        data.get("capital_lpp", ""),
        data.get("rente_conjoint", ""),
        data.get("annees_suisse", ""),
        data.get("canton", ""),
        data.get("souhaits", "")
    ]

    append_to_sheet(row)

    # Shopify adore recevoir success:true
    return {"success": True, "message": "Données enregistrées"}


# ---------------------------------------------------------------------
# /list — Liste les entrées pour la page admin Shopify
# ---------------------------------------------------------------------

@app.get("/list")
def list_entries():
    rows = read_sheet()
    return {"rows": rows}


# ---------------------------------------------------------------------
# /calcul/{row} — Lance le simulateur AVS + LPP
# ---------------------------------------------------------------------

@app.get("/calcul/{row_index}")
def calcul(row_index: int):
    rows = read_sheet()

    if row_index >= len(rows):
        raise HTTPException(404, "Index hors limite")

    row = rows[row_index]

    # On mappe chaque colonne → variable pour le simulateur
    data = {
        "prenom": row[0],
        "nom": row[1],
        "email": row[2],
        "telephone": row[3],
        "statut_civil": row[4],
        "age_actuel": row[5],
        "age_retraite": row[6],
        "salaire_annuel": row[7],
        "revenu_annuel_brut": row[8],
        "salaire_moyen_avs": row[9],
        "annees_cotisees": row[10],
        "be": row[11],
        "ba": row[12],
        "capital_lpp": row[13],
        "rente_conjoint": row[14],
        "annees_suisse": row[15],
        "canton": row[16],
        "souhaits": row[17],
    }

    resultat = simuler_pilier_complet(data)

    return {
        "status": "ok",
        "resultat": resultat
    }


# ---------------------------------------------------------------------
# /envoyer-mail/{row} — Envoie un email pro avec la simulation
# ---------------------------------------------------------------------

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")


@app.post("/envoyer-mail/{row_index}")
def envoyer_mail(row_index: int):
    rows = read_sheet()

    if row_index >= len(rows):
        raise HTTPException(404, "Index hors limite")

    row = rows[row_index]

    data = {
        "prenom": row[0],
        "nom": row[1],
        "email": row[2],
        "telephone": row[3],
        "statut_civil": row[4],
        "age_actuel": row[5],
        "age_retraite": row[6],
        "salaire_annuel": row[7],
        "revenu_annuel_brut": row[8],
        "salaire_moyen_avs": row[9],
        "annees_cotisees": row[10],
        "be": row[11],
        "ba": row[12],
        "capital_lpp": row[13],
        "rente_conjoint": row[14],
        "annees_suisse": row[15],
        "canton": row[16],
        "souhaits": row[17],
    }

    result = simuler_pilier_complet(data)

    # Construction du mail
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = data["email"]
    msg["Subject"] = "Votre simulation de retraite"

    body = result["details"]
    msg.attach(MIMEText(body, "plain"))

    # Envoi
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

    return {"status": "ok", "message": "Email envoyé"}


# ---------------------------------------------------------------------
# TEST EMAIL
# ---------------------------------------------------------------------

@app.get("/test-email")
def test_email():
    return {
        "host": SMTP_HOST,
        "user": SMTP_USER,
        "port": SMTP_PORT
    }
