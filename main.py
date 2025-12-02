print("=== BACKEND AVS/LPP CHARGÉ ===")

import os
import json
import gspread
import uuid
import time
import smtplib
import unicodedata
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.service_account import Credentials


app = FastAPI()

# --------------------------
# CORS
# --------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------
# GOOGLE SHEETS
# --------------------------
creds_json = os.getenv("GOOGLE_SHEET_CREDENTIALS")
if not creds_json:
    raise Exception("⚠ GOOGLE_SHEET_CREDENTIALS manquant dans Render")

creds_info = json.loads(creds_json)

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
client = gspread.authorize(creds)

sheet_name = os.getenv("SHEET_NAME", "reponses_clients")
sheet = client.open(sheet_name).sheet1


# ==========================================================
# 🧠 UTILITAIRES
# ==========================================================
def clean(s: str):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^ -~]", "", s).strip().lower()


def index_from_email(email: str):
    rows = sheet.get_all_values()
    email_clean = clean(email)

    for i in range(1, len(rows)):
        row_email = clean(rows[i][2])
        if row_email == email_clean:
            return i

    return -1


# ==========================================================
# 🧮 CONSTANTES AVS & LPP (officielles 2025)
# ==========================================================
AVS_MAX = 2520
AVS_MIN = 1260
SEUIL_MAX_RAMD = 90720
CARRIERE_PLEINE = 44
PLAFOND_COUPLE = 3780

BONIF_CREDIT_ANNUEL = 3 * AVS_MIN * 12

TAUX_CONVERSION_LPP = 0.058
TAUX_RENDEMENT = 0.0

DEDUCTION_COORDINATION = 26460
SEUIL_ENTREE_LPP = 22680


def taux_epargne(age):
    if age < 25:
        return 0
    if age <= 34:
        return 0.07
    if age <= 44:
        return 0.10
    if age <= 54:
        return 0.15
    return 0.18


def salaire_coordonne(salaire):
    if salaire <= SEUIL_ENTREE_LPP:
        return 0
    return max(0, min(salaire - DEDUCTION_COORDINATION, 62475))


# ==========================================================
# 🧮 RECONSTRUCTION LPP SI INCONNU
# ==========================================================
def reconstruire_lpp(age_actuel, salaire_actuel, annees_avs):
    age_debut = max(25, age_actuel - annees_avs)
    if age_actuel <= age_debut:
        return 0

    capital = 0
    salaire = salaire_actuel

    for age in range(age_debut, age_actuel):
        t = taux_epargne(age)
        sc = salaire_coordonne(salaire)
        cot = sc * t
        capital = capital * (1 + TAUX_RENDEMENT) + cot
        salaire *= 1.005

    return capital


# ==========================================================
# 🧮 CALCUL LPP FUTUR
# ==========================================================
def projection_lpp(age_actuel, age_retraite, salaire_initial, capital_initial):
    capital = capital_initial
    salaire = salaire_initial

    for age in range(age_actuel, age_retraite):
        salaire *= 1.005
        sc = salaire_coordonne(salaire)
        cot = sc * taux_epargne(age)
        capital = capital * (1 + TAUX_RENDEMENT) + cot

    rente_lpp = (capital * TAUX_CONVERSION_LPP) / 12
    return capital, rente_lpp


# ==========================================================
# 🧮 CALCUL AVS
# ==========================================================
def calcul_avs(ramd, annees_cotisees, annees_be, annees_ba):
    bonif = ((annees_be + annees_ba) * BONIF_CREDIT_ANNUEL) / max(1, annees_cotisees)
    ramd_corr = ramd + bonif

    if ramd_corr >= SEUIL_MAX_RAMD:
        rente_theo = AVS_MAX
    else:
        rente_theo = AVS_MIN + (AVS_MAX - AVS_MIN) * (ramd_corr / SEUIL_MAX_RAMD)
        rente_theo = min(rente_theo, AVS_MAX)

    # Lacunes
    if annees_cotisees >= CARRIERE_PLEINE:
        rente_final = rente_theo
    else:
        manque = CARRIERE_PLEINE - annees_cotisees
        reduction = rente_theo * (manque / CARRIERE_PLEINE)
        rente_final = max(AVS_MIN, rente_theo - reduction)

    return rente_final


# ==========================================================
# 🧮 CALCUL COMPLET RETRAITE D’UN CLIENT
# ==========================================================
def calculer_retraite(row):
    """
    row = ligne Google Sheet :
    [prenom, nom, email, tel, statut, age_actuel, age_ret, salaire, brut, ramd_avs,
     annees_avs, be, ba, capital_lpp, rente_conjoint, annees_suisse, canton, souhaits]
    """

    try:
        statut = clean(row[4])
        age_actuel = int(row[5])
        age_ret = int(row[6])
        salaire = float(row[7])
        ramd = float(row[9])
        annees_avs = int(row[10])
        be = int(row[11])
        ba = int(row[12])
        capital_lpp = float(row[13]) if row[13].strip() != "" else 0
        rente_conjoint = float(row[14]) if row[14].strip() != "" else 0
    except:
        return {"error": "format invalide"}

    # Reconstruction si capital LPP = 0 ou vide
    if capital_lpp == 0:
        capital_lpp = reconstruire_lpp(age_actuel, salaire, annees_avs)

    # Projection LPP future
    capital_final, lpp_mensuelle = projection_lpp(age_actuel, age_ret, salaire, capital_lpp)

    # Calcul AVS
    annees_totales = annees_avs + (age_ret - age_actuel)
    avs_user = calcul_avs(ramd, annees_totales, be, ba)

    # Plafonnement AVS (si marié)
    if statut == "marie":
        total_theorique = avs_user + rente_conjoint
        if total_theorique > PLAFOND_COUPLE:
            ratio = avs_user / total_theorique
            excedent = total_theorique - PLAFOND_COUPLE
            avs_user -= excedent * ratio

    total = avs_user + lpp_mensuelle

    return {
        "prenom": row[0],
        "nom": row[1],
        "email": row[2],
        "rente_avs": round(avs_user, 2),
        "rente_lpp": round(lpp_mensuelle, 2),
        "rente_totale": round(total, 2),
    }


# ==========================================================
# 🔵 ENDPOINTS
# ==========================================================

@app.get("/ping")
def ping():
    return {"status": "alive"}


@app.get("/list")
def listing():
    return {"rows": sheet.get_all_values()}


@app.get("/calcul-email")
def calcul_email(email: str):
    idx = index_from_email(email)
    if idx == -1:
        return {"error": "email introuvable"}

    row = sheet.get_all_values()[idx]
    result = calculer_retraite(row)
    return result


# --------------------------
# ENVOI MAIL
# --------------------------
def envoyer_email(prenom, email, texte):
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USER = "theo.maretraitesuisse@gmail.com"
    SMTP_PASS = "gkta owql oiou bbac"

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = email
    msg["Subject"] = f"Votre estimation retraite, {prenom}"
    msg.attach(MIMEText(texte, "plain"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)


@app.post("/envoyer-mail-email")
def envoyer_mail(email: str):
    idx = index_from_email(email)
    if idx == -1:
        return {"error": "email introuvable"}

    row = sheet.get_all_values()[idx]
    r = calculer_retraite(row)

    texte = (
        f"Bonjour {r['prenom']},\n\n"
        f"Voici votre estimation de retraite :\n"
        f"- AVS : {r['rente_avs']} CHF/mois\n"
        f"- LPP : {r['rente_lpp']} CHF/mois\n"
        f"- Total : {r['rente_totale']} CHF/mois\n\n"
        f"Cordialement,\nMaRetraiteSuisse"
    )

    envoyer_email(r["prenom"], r["email"], texte)
    return {"status": "email envoyé"}


# --------------------------
# ADMIN LOGIN
# --------------------------
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
        return {"allowed": False"}
    if time.time() > admin_tokens[token]:
        del admin_tokens[token]
        return {"allowed": False}
    return {"allowed": True}
