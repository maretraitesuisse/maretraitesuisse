print("=== Backend MaretraiteSuisse chargé ===")

# =========================================================
# IMPORTS
# =========================================================
import os
import time
import uuid
import base64
import requests
import hmac
import hashlib
from typing import Optional

from fastapi.responses import FileResponse
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, get_db
from simulateur_avs_lpp import calcul_complet_retraite
from models.models import Base, Client, Simulation
from routes.avis import router as avis_router
from fastapi import Request
from pdf_generator import generer_pdf_retraite





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

def note_attributes_to_dict(note_attrs):
    if isinstance(note_attrs, list):
        out = {}
        for item in note_attrs:
            if isinstance(item, dict) and "name" in item:
                out[item["name"]] = item.get("value")
        return out
    if isinstance(note_attrs, dict):
        return note_attrs
    return {}

def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)

    s = str(value).strip().lower()
    return s in ("1", "true", "vrai", "yes", "y", "oui", "on")


# =========================================================
# WEBHOOK
# =========================================================
@app.post("/webhook/shopify-paid")
async def shopify_paid(request: Request, db: Session = Depends(get_db)):

    # 🔐 Vérification HMAC Shopify
    body = await request.body()

    # =========================
    # DEBUG SHOPIFY HEADERS
    # =========================
    webhook_id = (request.headers.get("X-Shopify-Webhook-Id") or "").strip()
    topic = (request.headers.get("X-Shopify-Topic") or "").strip()
    shop_domain = (request.headers.get("X-Shopify-Shop-Domain") or "").strip()
    print("🔁 Shopify webhook delivery:", {"webhook_id": webhook_id, "topic": topic, "shop": shop_domain})

    
    hmac_header = (request.headers.get("X-Shopify-Hmac-Sha256") or "").strip()

    if not SHOPIFY_WEBHOOK_SECRET:
        print("❌ SHOPIFY_WEBHOOK_SECRET manquant côté Render")
        return {"ok": False}

    if not hmac_header:
        print("❌ Header X-Shopify-Hmac-Sha256 manquant")
        return {"ok": False}

    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()

    computed_hmac = base64.b64encode(digest).decode()

    if not hmac.compare_digest(computed_hmac, hmac_header):
        print("❌ HMAC invalide")
        return {"ok": False}

    # 🔄 Payload
    payload = await request.json()
    order = payload.get("order", payload)

    order_id = order.get("id")
    print("🧾 order_id:", order_id, "| webhook_id:", webhook_id)


    attrs = note_attributes_to_dict(order.get("note_attributes") or [])
    simulation_id_attr = (attrs.get("simulation_id") or "").strip()
    form_email_attr = (attrs.get("form_email") or "").strip().lower()


    # 📧 Email Shopify (fallback)
    email_shopify = (
        order.get("email")
        or order.get("customer", {}).get("email")
        or ""
    ).strip().lower()

    # ✅ email à utiliser en priorité = celui du formulaire (si présent)
    email_final = form_email_attr or email_shopify
    
    if not email_final:
        print("❌ email_final vide (ni form_email ni email shopify)")
        return {"ok": False}


    print("🧾 order_id:", order.get("id"))
    print("🧾 order_name:", order.get("name"))

    print("📦 note_attributes:", attrs)
    print("🆔 simulation_id_attr:", simulation_id_attr)
    print("📧 email_shopify:", email_shopify)
    print("📧 email_final:", email_final)

    simulation = None
    client = None

    # 1) ✅ Chercher directement la simulation via simulation_id (le plus fiable)
    if simulation_id_attr.isdigit():
        simulation = (
            db.query(Simulation)
            .filter(Simulation.id == int(simulation_id_attr))
            .first()
        )
        if simulation:
            client = (
                db.query(Client)
                .filter(Client.id == simulation.client_id)
                .first()
            )

    # 2) Fallback: si pas trouvé via simulation_id, chercher par email_final
    if not simulation:
        if not email_final:
            print("❌ Aucun email exploitable (form_email ou shopify email)")
            return {"ok": False}

        client = (
            db.query(Client)
            .filter(Client.email.ilike(email_final))
            .first()
        )
        if not client:
            print("❌ Client introuvable pour email :", email_final)
            return {"ok": False}

        simulation = (
            db.query(Simulation)
            .filter(Simulation.client_id == client.id)
            .order_by(Simulation.id.desc())
            .first()
        )

    if not simulation:
        print("❌ Aucune simulation trouvée (ni par simulation_id, ni par email)")
        return {"ok": False}


    # 🧾 PDF
    pdf_path = generer_pdf_retraite(
        donnees=simulation.donnees,
        resultats=simulation.resultat
    )

    # 📧 Envoi email premium
    envoyer_email_avec_pdf(
        template_id=2,
        email=email_final,          # ✅ important
        prenom=(client.prenom if client else (attrs.get("form_prenom") or "")).strip(),
        pdf_path=pdf_path
)


    print("✅ PDF envoyé à", email_final)

    return {"ok": True}

# =========================================================
# CONFIG BREVO
# =========================================================
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_URL = "https://api.brevo.com/v3/smtp/email"
SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET")

SENDER = {
    "email": "noreply@maretraitesuisse.ch",
    "name": "Ma Retraite Suisse"
}

def envoyer_email(template_id: int, email: str, prenom: str):
    if not BREVO_API_KEY:
        print("❌ BREVO_API_KEY manquant côté Render")
        return

    payload = {
        "templateId": template_id,
        "to": [{"email": email}],
        "params": {"prenom": prenom},
        "sender": SENDER
    }

    resp = requests.post(
        BREVO_URL,
        json=payload,
        headers={
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }
    )

    print("📨 Brevo status:", resp.status_code)
    try:
        print("📨 Brevo body:", resp.json())
    except Exception:
        print("📨 Brevo body (raw):", resp.text)

    

def envoyer_email_avec_pdf(template_id, email, prenom, pdf_path):
    if not BREVO_API_KEY:
        print("❌ BREVO_API_KEY manquant côté Render")
        return

    with open(pdf_path, "rb") as f:
        pdf_content = base64.b64encode(f.read()).decode()

    payload = {
        "templateId": template_id,
        "to": [{"email": email}],
        "params": {"prenom": prenom},
        "sender": SENDER,
        "attachment": [{
            "content": pdf_content,
            "name": "Projection_Retraite_MaRetraiteSuisse.pdf"
        }]
    }

    resp = requests.post(
        BREVO_URL,
        json=payload,
        headers={
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }
    )

    print("📨 Brevo status:", resp.status_code)
    try:
        print("📨 Brevo body:", resp.json())
    except Exception:
        print("📨 Brevo body (raw):", resp.text)


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

        "capital_lpp": float(payload.get("capital_lpp") or payload.get("capital_LPP") or 0),

        "rente_conjoint": float(payload.get("rente_conjoint") or 0),

        "has_3eme_pilier": parse_bool(payload.get("has_3eme_pilier") or payload.get("has_3eme_Pilier")),
        "type_3eme_pilier": payload.get("type_3eme_pilier") or payload.get("type_3eme_Pilier"),

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


@app.get("/debug/pdf/{simulation_id}")
def debug_pdf(simulation_id: int, db: Session = Depends(get_db)):
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        return {"ok": False, "error": "Simulation introuvable"}

    pdf_path = generer_pdf_retraite(
        donnees=simulation.donnees,
        resultats=simulation.resultat
    )

    return FileResponse(pdf_path, media_type="application/pdf", filename="projection_retraite.pdf")


# =========================================================
# PING
# =========================================================
@app.get("/ping")
def ping():
    return {"status": "alive"}
