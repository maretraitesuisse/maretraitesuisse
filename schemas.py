from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional


class SubmitPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    prenom: str
    nom: str
    email: str
    telephone: Optional[str] = None

    statut_civil: str
    statut_pro: str

    age_actuel: int
    age_retraite: int

    salaire_actuel: float
    salaire_moyen: float

    annees_cotisees: int
    annees_cotisees_lpp: int
    annees_be: int
    annees_ba: int

    capital_lpp: float = 0
    rente_conjoint: float = 0

    has_3eme_pilier: bool = False
    type_3eme_pilier: Optional[str] = None

    @field_validator("prenom", "nom")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or len(v) < 2 or len(v) > 80:
            raise ValueError("Longueur invalide")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if len(v) > 254 or "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email invalide")
        return v

    @field_validator("telephone")
    @classmethod
    def validate_telephone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if len(v) > 30:
            raise ValueError("Téléphone invalide")
        return v

    @field_validator("statut_civil")
    @classmethod
    def validate_statut_civil(cls, v: str) -> str:
        allowed = {"celibataire", "marie", "divorce", "veuf"}
        v = v.strip().lower()
        if v not in allowed:
            raise ValueError("statut_civil invalide")
        return v

    @field_validator("statut_pro")
    @classmethod
    def validate_statut_pro(cls, v: str) -> str:
        allowed = {"salarie", "independant"}
        v = v.strip().lower()
        if v not in allowed:
            raise ValueError("statut_pro invalide")
        return v

    @field_validator("age_actuel")
    @classmethod
    def validate_age_actuel(cls, v: int) -> int:
        if v < 16 or v > 100:
            raise ValueError("age_actuel invalide")
        return v

    @field_validator("age_retraite")
    @classmethod
    def validate_age_retraite(cls, v: int) -> int:
        if v < 18 or v > 80:
            raise ValueError("age_retraite invalide")
        return v

    @field_validator("salaire_actuel", "salaire_moyen")
    @classmethod
    def validate_salaire(cls, v: float) -> float:
        if v < 0 or v > 10000000:
            raise ValueError("Salaire invalide")
        return v

    @field_validator("annees_cotisees", "annees_cotisees_lpp", "annees_be", "annees_ba")
    @classmethod
    def validate_years(cls, v: int) -> int:
        if v < 0 or v > 60:
            raise ValueError("Nombre d'années invalide")
        return v

    @field_validator("capital_lpp", "rente_conjoint")
    @classmethod
    def validate_amounts(cls, v: float) -> float:
        if v < 0 or v > 100000000:
            raise ValueError("Montant invalide")
        return v

    @field_validator("type_3eme_pilier")
    @classmethod
    def validate_type_3eme_pilier(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        allowed = {"a", "b", "3a", "3b"}
        v = v.strip().lower()
        if v not in allowed:
            raise ValueError("type_3eme_pilier invalide")
        return v
