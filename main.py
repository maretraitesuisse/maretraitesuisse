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
from simulateur_avs_lpp import calcul_complet_retraite
from models.models import Base, Client, Simulation
from routes.avis import router as avis_router

# =========================================================
# INITIALISATION DB
# =========================================================
Base.metadata.create_all(bind=engine)

# =========================================================
# FASTAPI APP
# =========================================================
app = FastAPI()

# =========================================================
# CORS
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# CONFIG BREVO
# =========================================================
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_URL = "https://api.brevo.com/v3/smtp/email"

SENDER = {
    "email": "noreply@maretraitesuisse.ch",
    "name": "Ma Retraite Suisse"
}

def envoyer_email(template_id: int, email: str, prenom: str):
    payload = {
        "templateId": template_id,
        "to": [{"email": email}],
        "params": {"prenom": prenom},
        "sender": SENDER
    }

    requests.post(
        BREVO_URL,
        json=payload,
        headers={
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }
    )
@app.get("/ping")
def ping():
    return {"ok": True}

# =========================================================
# ROUTE : SUBMIT
# =========================================================
@app.post("/submit")
def submit(payload: dict, db: Session = Depends(get_db)):

    data = {
        "prenom": payload.get("prenom"),
        "nom": payload.get("nom"),
        "email": payload.get("email"),
        "telephone": payload.get("telephone"),

        "statut_civil": payload.get("statut_civil"),
        "statut_pro": payload.get("statut_pro"),

        "age_actuel": int(payload.get("age_actuel") or 0),
        "age_retraite": int(payload.get("age_retraite") or 0),

        "salaire_actuel": float(payload.get("salaire_actuel") or 0),
        "salaire_moyen": float(payload.get("salaire_moyen") or 0),

        "annees_cotisees": int(payload.get("annees_cotisees") or 0),
        "annees_be": int(payload.get("annees_be") or 0),
        "annees_ba": int(payload.get("annees_ba") or 0),

        "capital_lpp": float(payload.get("capital_lpp") or 0),
        "rente_conjoint": float(payload.get("rente_conjoint") or 0),

        "has_3eme_pilier": payload.get("has_3eme_pilier"),
        "type_3eme_pilier": payload.get("type_3eme_pilier"),
    }


    # CLIENT
    client = db.query(Client).filter(Client.email == data["email"]).first()
    if not client:
        client = Client(
            prenom=data["prenom"],
            nom=data["nom"],
            email=data["email"],
            telephone=data["telephone"]
        )
        db.add(client)
        db.commit()
        db.refresh(client)

    # CALCUL
    resultat = calcul_complet_retraite(data)

    # SIMULATION
    simulation = Simulation(
        client_id=client.id,
        statut_civil=data["statut_civil"],
        statut_pro=data["statut_pro"],
        age_actuel=data["age_actuel"],
        age_retraite=data["age_retraite"],
        salaire_actuel=data["salaire_actuel"],
        salaire_moyen=data["salaire_moyen"],
        annees_cotisees=data["annees_cotisees"],
        annees_be=data["annees_be"],
        annees_ba=data["annees_ba"],
        capital_lpp=data["capital_lpp"],
        rente_conjoint=data["rente_conjoint"],
        has_3eme_pilier=data["has_3eme_pilier"],
        type_3eme_pilier=data["type_3eme_pilier"],
        donnees=data,
        resultat=resultat
    )

    db.add(simulation)
    db.commit()
    db.refresh(simulation)

    # EMAIL (⬅️ INDENTATION CORRECTE)
    envoyer_email(1, client.email, client.prenom)

    return {
        "success": True,
        "simulation_id": simulation.id,
        "resultat": resultat
    }

# =========================================================
# ROUTES AVIS
# =========================================================
app.include_router(avis_router, prefix="/api/avis")

# =========================================================
# PING
# =========================================================
@app.get("/ping")
def ping():
    return {"status": "alive"}
