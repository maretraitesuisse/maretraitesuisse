# =========================================================
# ROUTES AVIS — BACKEND MARETRAITESUISSE
# =========================================================

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models.avis import Avis

# =========================================================
# ROUTER
# =========================================================

router = APIRouter()

# =========================================================
# PUBLIC — SOUMISSION D’UN AVIS
# =========================================================

@router.post("/submit")
def submit_avis(data: dict, db: Session = Depends(get_db)):
    """
    Réception d’un avis client (non publié par défaut)
    """

    avis = Avis(
        prenom=data["prenom"],
        nom=data["nom"],
        email=data["email"],
        canton=data.get("canton"),
        ville=data.get("ville"),
        note=int(data["note"]),
        message=data["message"],
        is_published=False,
    )

    db.add(avis)
    db.commit()
    db.refresh(avis)

    return {
        "success": True,
        "message": "Avis reçu avec succès"
    }

# =========================================================
# PUBLIC — AVIS PUBLIÉS
# =========================================================

@router.get("/published")
def get_published_avis(db: Session = Depends(get_db)):
    """
    Liste des avis validés (affichage site)
    """

    avis = (
        db.query(Avis)
        .filter(Avis.is_published == True)
        .order_by(Avis.published_at.desc())
        .all()
    )

    return [
        {
            "id": a.id,
            "prenom": a.prenom,
            "nom": a.nom[0] + ".",  # anonymisation
            "note": a.note,
            "message": a.message,
            "canton": a.canton,
            "ville": a.ville,
            "published_at": a.published_at.strftime("%d/%m/%Y") if a.published_at else None,
        }
        for a in avis
    ]

# =========================================================
# ADMIN — AVIS EN ATTENTE
# =========================================================

@router.get("/admin/pending")
def get_pending_avis(db: Session = Depends(get_db)):
    """
    Avis reçus mais non publiés (admin)
    """

    avis = (
        db.query(Avis)
        .filter(Avis.is_published == False)
        .order_by(Avis.created_at.desc())
        .all()
    )

    return avis

# =========================================================
# ADMIN — PUBLIER UN AVIS
# =========================================================

@router.post("/admin/{avis_id}/publish")
def publish_avis(avis_id: int, db: Session = Depends(get_db)):
    avis = db.query(Avis).filter(Avis.id == avis_id).first()

    if not avis:
        return {"success": False, "error": "Avis introuvable"}

    avis.is_published = True
    avis.published_at = datetime.utcnow()

    db.commit()

    return {"success": True}

# =========================================================
# ADMIN — SUPPRIMER UN AVIS
# =========================================================

@router.delete("/admin/{avis_id}")
def delete_avis(avis_id: int, db: Session = Depends(get_db)):
    avis = db.query(Avis).filter(Avis.id == avis_id).first()

    if not avis:
        return {"success": False, "error": "Avis introuvable"}

    db.delete(avis)
    db.commit()

    return {"success": True}
