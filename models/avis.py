# routes/avis.py

import time
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from database import get_db
from models.avis import Avis


router = APIRouter()


# =========================================================
# HELPERS
# =========================================================
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _check_admin_token(token: str) -> None:
    """
    Utilise EXACTEMENT le même store de tokens que ton main.py
    (sans import circulaire au démarrage).
    """
    try:
        # Import lazy (au moment de l'appel) pour éviter les boucles
        from main import admin_tokens  # type: ignore
    except Exception:
        raise HTTPException(status_code=500, detail="admin token store unavailable")

    if not token or token not in admin_tokens:
        raise HTTPException(status_code=401, detail="unauthorized")

    if time.time() > admin_tokens[token]:
        # token expiré -> purge
        try:
            del admin_tokens[token]
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="token expired")


def _format_date_fr(d: datetime) -> str:
    # format demandé: 12/03/2025
    return d.astimezone(timezone.utc).strftime("%d/%m/%Y")


# =========================================================
# SCHEMAS (Pydantic)
# =========================================================
class AvisCreate(BaseModel):
    prenom: str = Field(..., min_length=1, max_length=60)
    nom: str = Field(..., min_length=1, max_length=60)
    email: EmailStr
    canton: str = Field(..., min_length=2, max_length=60)
    ville: str = Field(..., min_length=1, max_length=80)
    note: int = Field(..., ge=1, le=5)
    message: str = Field(..., min_length=10, max_length=600)


class AvisPublicOut(BaseModel):
    id: int
    note: int
    message: str
    prenom: str
    nom_initiale: str
    ville: str
    published_at: str  # "12/03/2025"

    class Config:
        from_attributes = True


class AvisAdminOut(BaseModel):
    id: int
    created_at: str
    prenom: str
    nom: str
    email: str
    canton: str
    ville: str
    note: int
    message: str

    class Config:
        from_attributes = True


# =========================================================
# ROUTES — PUBLIC
# =========================================================
@router.post("/submit")
def submit_avis(payload: AvisCreate, db: Session = Depends(get_db)):
    """
    Crée un avis en attente de validation (pending).
    """
    avis = Avis(
        prenom=payload.prenom.strip(),
        nom=payload.nom.strip(),
        email=str(payload.email).strip().lower(),
        canton=payload.canton.strip(),
        ville=payload.ville.strip(),
        note=int(payload.note),
        message=payload.message.strip(),
        status="pending",
        is_published=False,
        created_at=_now_utc(),
        published_at=None,
    )

    db.add(avis)
    db.commit()
    db.refresh(avis)

    return {"success": True, "message": "avis received"}


@router.get("/published", response_model=List[AvisPublicOut])
def list_published(db: Session = Depends(get_db)):
    """
    Liste publique : uniquement les avis publiés, du plus récent au plus ancien.
    """
    rows = (
        db.query(Avis)
        .filter(Avis.is_published == True)  # noqa: E712
        .order_by(Avis.published_at.desc())
        .all()
    )

    out: List[AvisPublicOut] = []
    for a in rows:
        nom_initiale = (a.nom[:1].upper() + ".") if a.nom else ""
        published_at = _format_date_fr(a.published_at or a.created_at)

        out.append(
            AvisPublicOut(
                id=a.id,
                note=a.note,
                message=a.message,
                prenom=a.prenom,
                nom_initiale=nom_initiale,
                ville=a.ville,
                published_at=published_at,
            )
        )

    return out


# =========================================================
# ROUTES — ADMIN
# =========================================================
@router.get("/admin/pending", response_model=List[AvisAdminOut])
def admin_list_pending(token: str, db: Session = Depends(get_db)):
    """
    Liste admin : avis en attente (pending).
    """
    _check_admin_token(token)

    rows = (
        db.query(Avis)
        .filter(Avis.is_published == False)  # noqa: E712
        .order_by(Avis.created_at.desc())
        .all()
    )

    out: List[AvisAdminOut] = []
    for a in rows:
        out.append(
            AvisAdminOut(
                id=a.id,
                created_at=_format_date_fr(a.created_at),
                prenom=a.prenom,
                nom=a.nom,
                email=a.email,
                canton=a.canton,
                ville=a.ville,
                note=a.note,
                message=a.message,
            )
        )
    return out


@router.post("/admin/{avis_id}/publish")
def admin_publish(avis_id: int, token: str, db: Session = Depends(get_db)):
    """
    Publie un avis : il apparaîtra immédiatement côté public.
    """
    _check_admin_token(token)

    avis = db.query(Avis).filter(Avis.id == avis_id).first()
    if not avis:
        raise HTTPException(status_code=404, detail="avis not found")

    avis.is_published = True
    avis.status = "published"
    avis.published_at = _now_utc()

    db.add(avis)
    db.commit()

    return {"success": True}


@router.delete("/admin/{avis_id}")
def admin_delete(avis_id: int, token: str, db: Session = Depends(get_db)):
    """
    Refuser / supprimer définitivement un avis (comme demandé).
    """
    _check_admin_token(token)

    avis = db.query(Avis).filter(Avis.id == avis_id).first()
    if not avis:
        raise HTTPException(status_code=404, detail="avis not found")

    db.delete(avis)
    db.commit()

    return {"success": True}
