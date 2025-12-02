print("=== BACKEND CHARGÉ ===")

import os
import json
import gspread
import uuid
import time
import smtplib
import unicodedata
import re
from fpdf import FPDF
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from google.oauth2.service_account import Credentials

app = FastAPI()

# ============================
# CORS
# ============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================
# GOOGLE SHEETS
# ============================
creds_json = os.getenv("GOOGLE_SHEET_CREDENTIALS")
if not creds_json:
    raise Exception("⚠ GOOGLE_SHEET_CREDENTIALS manquant dans Render")

creds_info = json.loads(creds_json)

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
client = gspread.authorize(creds)

sheet_name = os.getenv("SHEET_NAME", "reponses_clients")
sheet = client.open(sheet_name).sheet1


# ============================
# MÉMOIRE INTERNE
# ============================
form_data = []
form_status = []
admin_tokens = {}

@app.get("/ping")
def ping():
    return {"status": "alive"}


# ============================
# SUBMIT FORM
# ============================
@app.post("/submit")
async def submit_form(data: dict):

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

    sheet.append_row(row)

    form_data.append(data)
    form_status.append("pending")

    return {"success": True}


# ============================
# ADMIN LIST
# ============================
@app.get("/list")
def listing():
    return {"rows": sheet.get_all_values()}


# ============================
# UTIL : nettoyeur UTF-8
# ============================
def clean(s: str):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^ -~]", "", s)
    return s.strip().lower()


# ============================
# TROUVER INDEX PAR EMAIL
# ============================
def index_from_email(email: str):
    email_clean = clean(email)
    rows = sheet.get_all_values()

    for i in range(1, len(rows)):
        if len(rows[i]) < 3:
            continue

        email_sheet = clean(rows[i][2])
        if email_clean == email_sheet:
            return i

    return -1


# ============================
# CALCUL PAR EMAIL
# ============================
@app.get("/calcul-email")
def calcul_email(email: str):
    idx = index_from_email(email)
    if idx == -1:
        return {"error": "email introuvable"}

    row = sheet.get_all_values()[idx]

    # ICI tu peux brancher ton vrai calcul Python
    # Pour l'instant version simple :
    return {
        "prenom": row[0],
        "nom": row[1],
        "email": row[2],
        "rente_avs": 1800,
        "rente_lpp": 1200,
        "rente_totale": 3000
    }


# ============================
# GÉNÉRATION PDF
# ============================
def make_pdf(data: dict, filepath: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "", 14)

    pdf.cell(0, 10, "Estimation Retraite - S-Heat / MaRetraiteSuisse", ln=1)
    pdf.ln(5)

    pdf.set_font("Arial", "", 12)
    for k, v in data.items():
        pdf.cell(0, 8, f"{k} : {v}", ln=1)

    pdf.output(filepath)


# ============================
# ENVOI EMAIL AVEC PDF
# ============================
def envoyer_email_pdf(prenom, email, pdf_path):

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USER = "theo.maretraitesuisse@gmail.com"
    SMTP_PASS = "gkta owql oiou bbac"

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = email
    msg["Subject"] = f"Votre estimation retraite, {prenom}"

    msg.attach(MIMEText("Veuillez trouver ci-joint votre estimation retraite en PDF.", "plain"))

    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), Name="estimation.pdf")
        part["Content-Disposition"] = 'attachment; filename="estimation.pdf"'
        msg.attach(part)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


# ============================
# API : créer PDF + envoyer mail
# ============================
@app.post("/generer-pdf-email")
def generer_pdf_email(email: str):

    idx = index_from_email(email)
    if idx == -1:
        return {"success": False, "error": "email introuvable"}

    row = sheet.get_all_values()[idx]

    data = {
        "Prenom": row[0],
        "Nom": row[1],
        "Email": row[2],
        "Rente AVS": "1800 CHF / mois",
        "Rente LPP": "1200 CHF / mois",
        "Total": "3000 CHF / mois"
    }

    pdf_path = "/tmp/estimation.pdf"
    make_pdf(data, pdf_path)

    envoyer_email_pdf(row[0], row[2], pdf_path)

    return {"success": True}


# ============================
# ADMIN LOGIN
# ============================
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ADMIN123")

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



