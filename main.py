print("=== Backend MaretraiteSuisse chargé ===")

# =========================================================
# IMPORTS
# =========================================================
import os
import time
import uuid
import base64
import requests
from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, get_db
from models import Base, Client, Simulation

from simulateur_avs_lpp import calcul_complet_retraite
from pdf_generator import generer_pdf_estimation

# =========================================================
# INITIALISATION DB
# =========================================================
Base.metadata.create_all(bind=engine)

# =========================================================
# FASTAPI
# =========================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# CONFIG BREVO
# =========================================================
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
if not BREVO_API_KEY:
    raise Exception("BREVO_API_KEY manquant")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
SENDER = {"email": "noreply@maretraitesuisse.com", "name": "Ma Retraite Suisse"}

def envoyer_email(template_id: int, email: str, prenom: str, attachment_path: str | None = None):
    payload = {
        "templateId": template_id,
        "to": [{"email": email}],
        "params": {"prenom": prenom},
        "sender": SENDER
    }

    if attachment_path:
        with open(attachment_path, "rb") as f:
            payload["attachment"] = [{
                "name": "estimation_retraite.pdf",
                "content": base64.b64encode(f.read()).decode()
            }]

    requests.post(
        BREVO_URL,
        json=payload,
        headers={
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }
    )

# =========================================================
# ROUTE : SUBMIT FORMULAIRE (CLIENT + SIMULATION)
# =========================================================
@app.post("/submit")
def submit(data: dict, db: Session = Depends(get_db)):

    # 1️⃣ CLIENT
    client = db.query(Client).filter(Client.email == data["email"]).first()

    if not client:
        client = Client(
            prenom=data["prenom"],
            nom=data["nom"],
            email=data["email"],
            telephone=data.get("telephone")
        )
        db.add(client)
        db.commit()
        db.refresh(client)

    # 2️⃣ CALCUL
    resultat = calcul_complet_retraite(data)

    # 3️⃣ SIMULATION
    simulation = Simulation(
        client_id=client.id,
        statut_civil=data.get("statut_civil"),
        statut_pro=data.get("statut_pro"),
        age_actuel=data.get("age_actuel"),
        age_retraite=data.get("age_retraite"),
        salaire_actuel=data.get("salaire_actuel"),
        salaire_moyen=data.get("salaire_moyen"),
        annees_cotisees=data.get("annees_cotisees"),
        annees_be=data.get("annees_be"),
        annees_ba=data.get("annees_ba"),
        capital_lpp=data.get("capital_lpp"),
        rente_conjoint=data.get("rente_conjoint"),
        resultat=resultat
    )

    db.add(simulation)
    db.commit()

    # 4️⃣ EMAIL CONFIRMATION
    envoyer_email(template_id=1, email=client.email, prenom=client.prenom)

    return {
        "success": True,
        "simulation_id": simulation.id,
        "resultat": resultat
    }

# =========================================================
# ROUTE : GENERATION + ENVOI PDF
# =========================================================
@app.post("/envoyer-pdf")
def envoyer_pdf(simulation_id: int, db: Session = Depends(get_db)):

    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        return {"success": False, "error": "Simulation introuvable"}

    client = db.query(Client).filter(Client.id == simulation.client_id).first()

    data = simulation.resultat
    pdf_path = generer_pdf_estimation(data, simulation.resultat)

    envoyer_email(
        template_id=2,
        email=client.email,
        prenom=client.prenom,
        attachment_path=pdf_path
    )

    return {"success": True}

# =========================================================
# ROUTE CRON (AVIS)
# =========================================================
@app.post("/cron-avis")
def cron_avis(email: str, prenom: str):
    envoyer_email(template_id=3, email=email, prenom=prenom)
    return {"success": True}

# =========================================================
# ADMIN AUTH
# =========================================================
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ADMIN123")
admin_tokens: dict[str, float] = {}

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
# DEBUG / PING
# =========================================================
@app.get("/ping")
def ping():
    return {"status": "alive"}

@app.get("/debug/clients")
def debug_clients(db: Session = Depends(get_db)):
    return db.query(Client).all()
