print("=== Backend MaretraiteSuisse chargé ===")

# =========================================================
# IMPORTS
# =========================================================
import os
import time
import uuid
import base64
import requests
from typing import Optional

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, get_db
from models import Base, Client, Simulation

from simulateur_avs_lpp import calcul_complet_retraite
from pdf_generator import generer_pdf_estimation
from database import engine
from models import Base, Simulation

print("⚠️ RESET DB : DROP TABLE simulations")

Simulation.__table__.drop(bind=engine, checkfirst=True)

print("✅ TABLE simulations supprimée")

# =========================================================
# INITIALISATION DB
# =========================================================
Base.metadata.create_all(bind=engine)

# =========================================================
# FASTAPI APP
# =========================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://maretraitesuisse.ch",
        "https://www.maretraitesuisse.ch",
        "https://admin.shopify.com",
        "https://*.myshopify.com",
    ],
    allow_credentials=True,
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
SENDER = {"email": "noreply@maretraitesuisse.ch", "name": "Ma Retraite Suisse"}

def envoyer_email(
    template_id: int,
    email: str,
    prenom: str,
    attachment_path: Optional[str] = None
):
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
# ROUTE : SUBMIT FORMULAIRE
# =========================================================
@app.post("/submit")
def submit(data: dict, db: Session = Depends(get_db)):

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

    resultat = calcul_complet_retraite(data)

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
        donnees=data,
        resultat=resultat
    )

    db.add(simulation)
    db.commit()
    db.refresh(simulation)

    envoyer_email(1, client.email, client.prenom)

    return {
        "success": True,
        "simulation_id": simulation.id,
        "resultat": resultat
    }

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
# ADMIN — LISTE DES SIMULATIONS
# =========================================================
@app.get("/admin/simulations")
def admin_simulations(token: str, db: Session = Depends(get_db)):

    if token not in admin_tokens or time.time() > admin_tokens[token]:
        return {"success": False, "error": "unauthorized"}

    rows = (
        db.query(Simulation, Client)
        .join(Client, Client.id == Simulation.client_id)
        .order_by(Simulation.created_at.desc())
        .all()
    )

    return {
        "success": True,
        "rows": [
            {
                "simulation_id": sim.id,
                "created_at": sim.created_at.isoformat(),
                "client": {
                    "prenom": cli.prenom,
                    "nom": cli.nom,
                    "email": cli.email,
                    "telephone": cli.telephone,
                },
                "donnees": sim.donnees,
                "resultat": sim.resultat
            }
            for sim, cli in rows
        ]
    }

# =========================================================
# PING / DEBUG
# =========================================================
@app.get("/ping")
def ping():
    return {"status": "alive"}
