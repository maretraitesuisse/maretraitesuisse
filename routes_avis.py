# routes_avis.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import time

from database import get_db
from models.avis import Avis

router = APIRouter()

# --- Helpers: admin token (utilise EXACTEMENT la même logique que ton main.py) ---
def require_admin_token(token: str, admin_tokens: dict[str, float]):
    if token not in admin_tokens:
        raise HTTPException(status_code=401, detail="unauthorized")
    if time.time() > admin_tokens[token]:
        # token expiré -> on le supprime
        del admin_tokens[token]
        raise HTTPException(status_code=401, detail="token expired")


# ✅ Public: soumettre un avis
@router.post("")
def submit_avis(data: dict, db: Session = Depends(get_db)):
    required = ["prenom", "nom", "email", "ville", "canton", "note", "message"]
    for k in required:
        if k not in data or data[k] in (None, ""):
            raise HTTPException(status_code=400, detail=f"missing {k}")

    note = int(data["note"])
    if note < 1 or note > 5:
        raise HTTPException(status_code=400, detail="note must be 1..5")

    avis = Avis(
        prenom=data["prenom"].strip(),
        nom=data["nom"].strip(),
        email=data["email"].strip(),
        ville=data["ville"].strip(),
        canton=data["canton"].strip(),
        note=note,
        message=data["message"].strip(),
        status="pending",
    )
    db.add(avis)
    db.commit()
    return {"success": True}


# ✅ Public: afficher avis approuvés
@router.get("/public")
def get_public_avis(db: Session = Depends(get_db)):
    rows = (
        db.query(Avis)
        .filter(Avis.status == "approved")
        .order_by(Avis.published_at.desc())
        .all()
    )

    # on renvoie seulement ce qui est public
    return [
        {
            "id": r.id,
            "prenom": r.prenom,
            "nom": r.nom[0] + "." if r.nom else "",
            "note": r.note,
            "message": r.message,
            "published_at": r.published_at.isoformat() if r.published_at else None,
        }
        for r in rows
    ]


# ✅ Admin: lister les avis en attente (email / ville / canton visibles seulement admin)
@router.get("/admin")
def get_admin_avis(token: str, admin_tokens: dict[str, float], db: Session = Depends(get_db)):
    require_admin_token(token, admin_tokens)

    rows = (
        db.query(Avis)
        .filter(Avis.status == "pending")
        .order_by(Avis.created_at.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "prenom": r.prenom,
            "nom": r.nom,
            "email": r.email,
            "ville": r.ville,
            "canton": r.canton,
            "note": r.note,
            "message": r.message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ✅ Admin: approuver
@router.post("/{avis_id}/approve")
def approve_avis(
    avis_id: int,
    token: str,
    admin_tokens: dict[str, float],
    db: Session = Depends(get_db)
):
    require_admin_token(token, admin_tokens)

    avis = db.query(Avis).filter(Avis.id == avis_id).first()
    if not avis:
        raise HTTPException(status_code=404, detail="not found")

    avis.status = "approved"
    avis.published_at = datetime.utcnow()
    db.commit()
    return {"success": True}


# ✅ Admin: refuser (= suppression définitive comme demandé)
@router.delete("/{avis_id}")
def delete_avis(
    avis_id: int,
    token: str,
    admin_tokens: dict[str, float],
    db: Session = Depends(get_db)
):
    require_admin_token(token, admin_tokens)

    avis = db.query(Avis).filter(Avis.id == avis_id).first()
    if not avis:
        raise HTTPException(status_code=404, detail="not found")

    db.delete(avis)
    db.commit()
    return {"success": True}


