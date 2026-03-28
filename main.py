print("=== Backend MaretraiteSuisse chargé ===")

# =========================================================
# IMPORTS
# =========================================================
import os
import base64
import requests
import hmac
import hashlib

from fastapi import FastAPI, Depends, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import engine, get_db, SessionLocal
from simulateur_avs_lpp import calcul_complet_retraite
from models.models import Base, Client, Simulation, WebhookDelivery
from routes.avis import router as avis_router
from pdf_generator import generer_pdf_retraite
from rate_limit import is_rate_limited
from schemas import SubmitPayload

import time
from sqlalchemy import text

ENV = os.getenv("ENV", "production").lower()

def generate_secure_token(simulation_id: int) -> str:
    secret = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")
    msg = str(simulation_id).encode()

    return hmac.new(
        secret.encode(),
        msg,
        hashlib.sha256
    ).hexdigest()
# =========================================================
# FASTAPI APP
# =========================================================
app = FastAPI(
    docs_url=None if ENV == "production" else "/docs",
    redoc_url=None if ENV == "production" else "/redoc",
    openapi_url=None if ENV == "production" else "/openapi.json",
)

@app.on_event("startup")
def startup_db():
    """
    Objectif:
    - éviter que l'app crashe si Supabase/pooler met quelques secondes à répondre
    - s'assurer que la DB est joignable
    - créer les tables (si tu relies vraiment sur create_all)
    """
    for attempt in range(1, 11):  # 10 tentatives
        try:
            # 1) Ping DB (force une vraie connexion)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            # 2) Create tables (si nécessaire)
            Base.metadata.create_all(bind=engine)

            print("✅ DB OK + tables ensured")
            return

        except Exception as e:
            print(f"⚠️ DB not ready (attempt {attempt}/10): {e}")
            time.sleep(2)

    # Si on arrive ici, la DB est toujours down après ~20s
    raise RuntimeError("❌ DB unreachable after retries")

# =========================================================
# CORS
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://maretraitesuisse.ch",
        "https://www.maretraitesuisse.ch",
        "https://cdn.shopify.com",
    ],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Authorization"],
)
MAX_BODY_SIZE = 1024 * 1024  # 1 MB

@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")

    if content_length:
        try:
            if int(content_length) > MAX_BODY_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"ok": False, "error": "Request too large"}
                )
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "Invalid content-length"}
            )

    return await call_next(request)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    if ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    return response

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

def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return ""
    name, domain = email.split("@", 1)

    name_mask = name[0] + "***" if len(name) > 1 else "***"
    domain_mask = domain[0] + "***" if len(domain) > 1 else "***"

    return f"{name_mask}@{domain_mask}"

# =========================================================
# CONFIG BREVO
# =========================================================
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_URL = "https://api.brevo.com/v3/smtp/email"
SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET")
EXPECTED_SHOP_DOMAIN = os.getenv("SHOPIFY_SHOP_DOMAIN", "").strip().lower()
EXPECTED_PRODUCT_ID = int(os.getenv("SHOPIFY_PRODUCT_ID", "0"))

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
# WEBHOOK
# =========================================================
@app.post("/webhook/shopify-paid")
async def shopify_paid(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):


    # 🔐 Vérification HMAC Shopify
    body = await request.body()

    # =========================
    # DEBUG SHOPIFY HEADERS
    # =========================
    webhook_id = (request.headers.get("X-Shopify-Webhook-Id") or "").strip()
    topic = (request.headers.get("X-Shopify-Topic") or "").strip()
    shop_domain = (request.headers.get("X-Shopify-Shop-Domain") or "").strip()
    
    if topic != "orders/paid":
        print("❌ Topic Shopify inattendu:", topic)
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Invalid webhook topic"}
    )

    if not EXPECTED_SHOP_DOMAIN:
        print("❌ SHOPIFY_SHOP_DOMAIN non configuré")
        return JSONResponse(status_code=500, content={"ok": False})

    if shop_domain.lower() != EXPECTED_SHOP_DOMAIN:
        print("❌ Webhook envoyé par un shop inconnu:", shop_domain)
        return JSONResponse(
            status_code=403,
            content={"ok": False, "error": "Invalid shop"}
        )
    
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
    
    if not order_id:
        print("❌ order_id manquant")
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Missing order id"}
        )

    financial_status = (order.get("financial_status") or "").lower()

    if financial_status != "paid":
        print("❌ Commande non payée ignorée:", financial_status)
        return {"ok": True}

    line_items = order.get("line_items") or []

    if not line_items:
        print("❌ Commande sans produits")
        return {"ok": False}
    
    product_ok = False

    for item in line_items:
        product_id = item.get("product_id")

        if product_id and int(product_id) == EXPECTED_PRODUCT_ID:
            product_ok = True
            break

    if not product_ok:
        print("❌ Produit inattendu dans la commande")
        return {"ok": True}
    
    print("🧾 order_id:", order_id, "| webhook_id:", webhook_id)

    if not webhook_id:
        print("❌ Webhook sans ID — refusé")
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Missing webhook id"}
        )


    # =========================================================
    # LECTURE DES ATTRIBUTS SHOPIFY (cart attributes / note_attributes)
    # =========================================================
    raw_note_attributes = order.get("note_attributes") or order.get("attributes") or {}
    attrs = note_attributes_to_dict(raw_note_attributes)

    print("📦 raw_note_attributes Shopify:", raw_note_attributes)
    print("📦 attrs Shopify:", attrs)

    simulation_id_attr = str(attrs.get("simulation_id", "")).strip()
    form_email_attr = str(attrs.get("form_email", "")).strip().lower()
    form_prenom_attr = str(attrs.get("form_prenom", "")).strip()
    secure_token_attr = str(attrs.get("secure_token", "")).strip()

    # =========================================================
    # SÉCURITÉ — simulation_id obligatoire
    # =========================================================
    if not simulation_id_attr or not simulation_id_attr.isdigit():
        print("❌ simulation_id manquant ou invalide dans note_attributes")
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Missing simulation_id"}
        )

    # =========================================================
    # SÉCURITÉ — secure_token obligatoire et valide
    # =========================================================
    expected_token = generate_secure_token(int(simulation_id_attr))

    if not secure_token_attr:
        print("❌ secure_token manquant dans note_attributes")
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Missing secure_token"}
        )

    if not hmac.compare_digest(secure_token_attr, expected_token):
        print("❌ secure_token invalide")
        return JSONResponse(
            status_code=403,
            content={"ok": False, "error": "Invalid secure_token"}
        )

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
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Missing email"}
        )

    print("🧾 order_name:", order.get("name"))
    print("📦 note_attributes keys:", list(attrs.keys()))
    print("🆔 simulation_id_attr:", simulation_id_attr)
    print("🔐 secure_token reçu:", secure_token_attr[:12] + "..." if secure_token_attr else "")
    print("📧 email_shopify:", mask_email(email_shopify))
    print("📧 email_final:", mask_email(email_final))

    simulation = (
        db.query(Simulation)
        .filter(Simulation.id == int(simulation_id_attr))
        .first()
    )

    if not simulation:
        print("❌ simulation_id introuvable:", simulation_id_attr)
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": "Simulation not found"}
        )

    client = (
        db.query(Client)
        .filter(Client.id == simulation.client_id)
        .first()
    )

    if not client:
        print("❌ Client introuvable pour simulation:", simulation_id_attr)
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "Client not found"}
        )

    # =========================================================
    # IDEMPOTENCE — seulement APRÈS validations sécurité
    # =========================================================
    try:
        db.add(WebhookDelivery(webhook_id=webhook_id, order_id=str(order_id)))
        db.commit()
    except IntegrityError:
        db.rollback()

        existing_same_order = (
            db.query(WebhookDelivery)
            .filter(WebhookDelivery.order_id == str(order_id))
            .first()
        )

        if existing_same_order:
            print("🟡 Commande déjà traitée:", order_id)
            return {"ok": True}

        existing_same_webhook = (
            db.query(WebhookDelivery)
            .filter(WebhookDelivery.webhook_id == webhook_id)
            .first()
        )

        if existing_same_webhook:
            print("🟡 Webhook déjà traité, on ignore :", webhook_id)
            return {"ok": True}

        print("❌ IntegrityError inattendue sur WebhookDelivery")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "Webhook persistence error"}
        )

    prenom = (form_prenom_attr or client.prenom or "").strip()

    background_tasks.add_task(
        process_paid_order,
        simulation.id,
        email_final,
        prenom
    )

    return {"ok": True}
    
# =========================================================
# ROUTE : SUBMIT
# =========================================================
@app.post("/submit")
def submit(payload: SubmitPayload, request: Request, db: Session = Depends(get_db)):

    origin = (request.headers.get("origin") or "").lower()
    referer = (request.headers.get("referer") or "").lower()

    allowed = [
        "https://maretraitesuisse.ch",
        "https://www.maretraitesuisse.ch"
    ]

    if not any(origin.startswith(a) for a in allowed) and not any(referer.startswith(a) for a in allowed):
        print("❌ Requête /submit bloquée (origin non autorisé)", origin, referer)
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "Forbidden"}
        )
    
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or request.client.host

    rate_key = f"submit:{client_ip}"

    if is_rate_limited(rate_key, limit=10, window_seconds=60):
        return JSONResponse(
            status_code=429,
            content={"success": False, "error": "Trop de requêtes"}
        )

    data = payload.model_dump()


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
        annees_cotisees_lpp=data["annees_cotisees_lpp"],
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

    

    token = generate_secure_token(simulation.id)

    return {
        "success": True,
        "simulation_id": simulation.id,
        "secure_token": token,
        "resultat": resultat
    }

# =========================================================
# ROUTES AVIS
# =========================================================
app.include_router(avis_router, prefix="/api/avis")

# =========================================================
# BACKGROUND TASK PAIEMENT
# =========================================================
def process_paid_order(simulation_id: int, email_final: str, prenom: str):
    db = SessionLocal()
    pdf_path = None

    try:
        print(f"🚀 process_paid_order START | simulation_id={simulation_id} | email={email_final} | prenom={prenom}")

        simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not simulation:
            print("❌ simulation introuvable en background")
            return

        print("✅ simulation récupérée")

        pdf_path = generer_pdf_retraite(
            donnees=simulation.donnees,
            resultats=simulation.resultat
        )
        print("✅ PDF généré :", pdf_path)

        envoyer_email(1, email_final, prenom)
        print("✅ email confirmation envoyé")

        envoyer_email_avec_pdf(2, email_final, prenom, pdf_path)
        print("✅ email PDF envoyé")

        print("✅ process_paid_order terminé")

    except Exception as e:
        print("❌ ERREUR process_paid_order :", repr(e))
        import traceback
        traceback.print_exc()

    finally:
        try:
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
                print("🧹 PDF supprimé :", pdf_path)
        except Exception as e:
            print("⚠️ Erreur suppression PDF :", str(e))

        db.close()

@app.get("/admin/regenerate-pdf/{simulation_id}")
def regenerate_pdf(simulation_id: int, db: Session = Depends(get_db)):
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()

    if not simulation:
        return {"error": "Simulation not found"}

    pdf_path = generer_pdf_retraite(
        donnees=simulation.donnees,
        resultats=simulation.resultat
    )

    return FileResponse(pdf_path, filename="simulation.pdf")
# =========================================================
# PING
# =========================================================
@app.get("/ping")
def ping():
    return {"status": "alive"}
