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
from pdf_generator import generer_pdf_estimation

from models.models import Base, Client, Simulation
from models.avis import Avis
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
# CORS — TEMPORAIRE (DEBUG)
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
if not BREVO_API_KEY:
    raise Exception("BREVO_API_KEY manquant")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
SENDER = {
    "email": "noreply@maretraitesuisse.ch",
    "name": "Ma Retraite Suisse"
}

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
def submit(payload: dict, db: Session = Depends(get_db)):

    # =====================================================
    # 🔄 NORMALISATION FRONT (camelCase) → BACK (snake_case)
    # =====================================================
    data = {
        "prenom": payload.get("prenom"),
        "nom": payload.get("nom"),
        "email": payload.get("email"),
        "telephone": payload.get("telephone"),

        "statut_civil": payload.get("statutCivil"),
        "statut_pro": payload.get("statutPro"),

        "age_actuel": payload.get("ageActuel"),
        "age_retraite": payload.get("ageRetraite"),

        "salaire_actuel": payload.get("salaireActuel"),
        "salaire_moyen": payload.get("salaireMoyen"),

        "annees_cotisees": payload.get("anneesCotisees"),

        "capital_lpp": payload.get("capitalLPP"),
        "rente_conjoint": payload.get("renteConjoint"),

        # valeurs optionnelles
        "annees_be": payload.get("annees_be", 0),
        "annees_ba": payload.get("annees_ba", 0),
    }

    # =====================================================
    # CLIENT
    # =====================================================
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

    # =====================================================
    # 🧮 CALCUL MÉTIER (AVS + LPP)
    # =====================================================
    resultat = calcul_complet_retraite(data)

    # =====================================================
    # SAUVEGARDE SIMULATION
    # =====================================================
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

    # =====================================================
    # 📧 EMAIL CONFIRMATION
    # =====================================================
    envoyer_email(1, client.email, client.prenom)

    # =====================================================
    # RÉPONSE FRONTEND
    # =====================================================
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

# =========================================================
# ROUTES AVIS
# =========================================================
app.include_router(
    avis_router,
    prefix="/api/avis",
    dependencies=[],
)

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
