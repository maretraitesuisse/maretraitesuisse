import os
import json
import gspread
import uuid
import time
import smtplib
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.service_account import Credentials

app = FastAPI()

# ---- CORS (Shopify + Render)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Google Sheets (Render ENV)
creds_info = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open(os.getenv("SHEET_NAME")).sheet1

# ---- Mémoire interne (cache simple)
admin_tokens = {}  # {token: expiration_timestamp}
form_data = []     # données envoyées par Shopify
form_status = []   # sent/pending

@app.get("/ping")
def ping():
    return {"status": "alive"}


# --------------------------
# 1️⃣ FORMULAIRE CLIENT
# --------------------------
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

    return {"success": True, "message": "Données enregistrées"}


# --------------------------
# 2️⃣ LISTE DES FORMULAIRES
# --------------------------
@app.get("/list")
def listing():
    return {"rows": sheet.get_all_values()}


# --------------------------
# 3️⃣ CALCUL (faux pour l'instant)
# --------------------------
@app.get("/calcul/{index}")
def calcul(index: int):
    if index >= len(form_data):
        return {"error": "Index invalide"}

    d = form_data[index]

    # Exemple temporaire
    return {
        "prenom": d["prenom"],
        "nom": d["nom"],
        "rente_avs": 1800,
        "rente_lpp": 1200,
        "rente_totale": 3000
    }


# --------------------------
# 4️⃣ ENVOI D’EMAIL
# --------------------------
def envoyer_email(prenom, destinataire, texte):
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USER = "theo.maretraitesuisse@gmail.com"
    SMTP_PASS = "gkta owql oiou bbac"

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = destinataire
    msg["Subject"] = f"Votre simulation retraite, {prenom}"
    msg.attach(MIMEText(texte, "plain"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


@app.post("/envoyer-mail/{index}")
def envoyer(index: int):
    if index >= len(form_data):
        return {"error": "index invalide"}

    d = form_data[index]
    texte = f"Votre estimation : AVS 1800, LPP 1200, Total 3000 CHF/mois."

    envoyer_email(d["prenom"], d["email"], texte)
    form_status[index] = "sent"

    return {"status": "ok"}


# --------------------------
# 5️⃣ ADMIN — LOGIN → TOKEN
# --------------------------
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ADMIN123")


@app.get("/admin-login")
def admin_login(password: str):
    if password != ADMIN_PASSWORD:
        return {"success": False, "error": "Mot de passe incorrect"}

    token = str(uuid.uuid4())
    expiration = time.time() + 600  # 10 minutes

    admin_tokens[token] = expiration
    return {"success": True, "token": token}


# --------------------------
# 6️⃣ ADMIN — VALIDATION DU TOKEN
# --------------------------
@app.get("/verify-admin-token")
def verify_token(token: str):
    if token not in admin_tokens:
        return {"allowed": False}

    if time.time() > admin_tokens[token]:
        del admin_tokens[token]
        return {"allowed": False}

    return {"allowed": True}
