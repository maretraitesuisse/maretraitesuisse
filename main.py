print("=== Backend MaretraiteSuisse chargé ===")

import os
import json
import time
import uuid
import smtplib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
#                CONNEXION GOOGLE SHEET
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
#         FONCTION UTILITAIRE : TROUVER LIGNE EMAIL
# =========================================================
def find_index_by_email(email: str):
    rows = sheet.get_all_values()
    email = email.strip().lower()

    for i in range(1, len(rows)):  # commencer après l’en-tête
        if rows[i][2].strip().lower() == email:
            return i

    return -1


# =========================================================
#                    ROUTE : LIST
# =========================================================
@app.get("/list")
def listing():
    return {"rows": sheet.get_all_values()}


# =========================================================
#   ROUTE CALCUL PAR EMAIL → CALCUL COMPLET AVS + LPP
# =========================================================
@app.get("/calcul-email")
def calcul_email(email: str):
    index = find_index_by_email(email)
    if index == -1:
        return {"error": "email introuvable dans Google Sheet"}

    row = sheet.get_all_values()[index]

    # On mappe les colonnes Google Sheet → variables Python
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
#     SMTP — envoyer email avec le PDF en pièce jointe
# =========================================================
def envoyer_email_avec_pdf(destinataire, prenom, pdf_path):

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USER = "theo.maretraitesuisse@gmail.com"
    SMTP_PASS = "gkta owql oiou bbac"

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = destinataire
    msg["Subject"] = f"Votre estimation retraite – {prenom}"

    corps = (
        f"Bonjour {prenom},\n\n"
        "Veuillez trouver ci-joint votre analyse retraite complète.\n"
        "N'hésitez pas à répondre à cet email pour toute question.\n\n"
        "Bien cordialement,\n"
        "Ma Retraite Suisse\n"
        "Service d’analyse retraite\n"
        "theo.maretraitesuisse@gmail.com"
    )

    msg.attach(MIMEText(corps, "plain"))

    # Charger le fichier PDF
    with open(pdf_path, "rb") as f:
        from email.mime.application import MIMEApplication
        part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename="estimation_retraite.pdf")
        msg.attach(part)

    # Envoi SMTP
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


# =========================================================
#     ROUTE : générer + envoyer PDF
# =========================================================
@app.post("/envoyer-mail-email")
def envoyer_pdf(email: str):
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

    pdf_path = generer_pdf_estimation(donnees, resultat)

    envoyer_email_avec_pdf(
        destinataire=donnees["email"],
        prenom=donnees["prenom"],
        pdf_path=pdf_path
    )

    return {"success": True, "message": "PDF envoyé au client."}


# =========================================================
#     ADMIN LOGIN (Render token)
# =========================================================
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ADMIN123")
admin_tokens = {}


@app.get("/admin-login")
def admin_login(password: str):
    if password != ADMIN_PASSWORD:
        return {"success": False}

    token = str(uuid.uuid4())
    expiration = time.time() + 600

    admin_tokens[token] = expiration
    return {"success": True, "token": token}


@app.get("/verify-admin-token")
def verify_token(token: str):
    if token not in admin_tokens:
        return {"allowed": False}

    if time.time() > admin_tokens[token]:
        del admin_tokens[token]
        return {"allowed": False}

    return {"allowed": True}


@app.get("/ping")
def ping():
    return {"status": "alive"}
