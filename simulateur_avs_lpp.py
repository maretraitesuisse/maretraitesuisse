# ===============================================================
#  Simulateur Retraite Suisse — AVS + LPP
#  Moteur métier central — VERSION STABLE
# ===============================================================

from typing import Dict

# ===============================================================
#  CONSTANTES AVS
# ===============================================================

AVS_RENTE_MAX = 2520
AVS_RENTE_MIN = 1260
AVS_RENTE_MEDIANE = 1890

SEUIL_MAX_RAMD = 90720
CARRIERE_PLEINE = 44
PLAFOND_COUPLE = 3780

BONIF_CREDIT = 3 * AVS_RENTE_MIN * 12  # bonification éducative / assistance

# ===============================================================
#  CONSTANTES LPP
# ===============================================================

DEDUCTION_COORD = 26460
SEUIL_ENTREE_LPP = 22680
TAUX_CONVERSION = 0.058

TAUX_EPARGNE = {
    "25-34": 0.07,
    "35-44": 0.10,
    "45-54": 0.15,
    "55+": 0.18,
}

# ===============================================================
#  OUTILS GÉNÉRAUX
# ===============================================================

def get_taux_epargne(age: int) -> float:
    if age < 25:
        return 0.0
    if age <= 34:
        return TAUX_EPARGNE["25-34"]
    if age <= 44:
        return TAUX_EPARGNE["35-44"]
    if age <= 54:
        return TAUX_EPARGNE["45-54"]
    return TAUX_EPARGNE["55+"]


def calcul_salaire_coordonne(salaire: float) -> float:
    if salaire <= SEUIL_ENTREE_LPP:
        return 0.0
    return max(0.0, min(salaire - DEDUCTION_COORD, 62475))


# ===============================================================
#  LPP
# ===============================================================

def reconstruire_lpp(age_actuel: int, salaire: float, annees: int) -> float:
    """
    Reconstruit un capital LPP passé si non fourni
    """
    age_debut = max(25, age_actuel - annees)
    capital = 0.0
    salaire_base = salaire / (1.005 ** max(annees, 1))

    for age in range(age_debut, age_actuel):
        taux = get_taux_epargne(age)
        salaire_coord = calcul_salaire_coordonne(salaire_base)
        capital += salaire_coord * taux
        salaire_base *= 1.005

    return round(capital, 2)


def calculer_lpp(age_actuel: int, age_retraite: int, salaire: float, capital: float) -> Dict:
    """
    Projection LPP jusqu'à l'âge de retraite
    """
    salaire_courant = salaire

    for age in range(age_actuel, age_retraite):
        taux = get_taux_epargne(age)
        salaire_coord = calcul_salaire_coordonne(salaire_courant)
        capital += salaire_coord * taux
        salaire_courant *= 1.005

    rente_mensuelle = (capital * TAUX_CONVERSION) / 12

    return {
        "capital_final": round(capital, 2),
        "rente_mensuelle": round(rente_mensuelle, 2)
    }


# ===============================================================
#  AVS
# ===============================================================

def calculer_avs(
    salaire_moyen: float,
    annees_total: int,
    annees_be: int,
    annees_ba: int
) -> Dict:
    """
    Calcul AVS selon RAMD et carrière
    """
    bonifs = (annees_be + annees_ba) * BONIF_CREDIT / max(annees_total, 1)
    ramd = salaire_moyen + bonifs

    if ramd >= SEUIL_MAX_RAMD:
        rente = AVS_RENTE_MAX
    else:
        rente = AVS_RENTE_MIN + (AVS_RENTE_MAX - AVS_RENTE_MIN) * max(0, ramd) / SEUIL_MAX_RAMD

    if annees_total < CARRIERE_PLEINE:
        rente *= annees_total / CARRIERE_PLEINE

    rente = max(rente, AVS_RENTE_MIN)

    return {
        "ramd": round(ramd, 2),
        "rente_finale": round(rente, 2)
    }


# ===============================================================
#  POINT D’ENTRÉE BACKEND — STABLE
# ===============================================================

def calcul_complet_retraite(donnees: Dict) -> Dict:
    """
    Fonction appelée par FastAPI
    ⚠️ Interface STABLE — ne pas casser
    """

    # ===== DONNÉES DE BASE =====

    age_actuel = int(donnees.get("age_actuel", 0))
    age_retraite = int(donnees.get("age_retraite", 0))

    salaire_actuel = float(donnees.get("salaire_actuel", 0))
    salaire_moyen = float(
        donnees.get("salaire_moyen_avs", donnees.get("salaire_moyen", 0))
    )

    annees_avs = int(donnees.get("annees_avs", donnees.get("annees_cotisees", 0)))
    annees_be = int(donnees.get("annees_be", 0))
    annees_ba = int(donnees.get("annees_ba", 0))

    statut_civil = donnees.get("statut_civil", "celibataire")
    statut_pro = donnees.get("statut_pro", "salarie")

    capital_lpp = float(donnees.get("capital_lpp", 0))
    rente_conjoint = float(donnees.get("rente_conjoint", 0))

    # ===== CARRIÈRE =====

    annees_futures = max(0, age_retraite - age_actuel)
    annees_total = annees_avs + annees_futures

    # ===== AVS =====

    avs = calculer_avs(
        salaire_moyen=salaire_moyen,
        annees_total=annees_total,
        annees_be=annees_be,
        annees_ba=annees_ba
    )

    rente_avs = avs["rente_finale"]

    # ===== LPP =====

    if capital_lpp == 0 and statut_pro != "independant":
        capital_lpp = reconstruire_lpp(age_actuel, salaire_actuel, annees_avs)

    lpp = calculer_lpp(
        age_actuel=age_actuel,
        age_retraite=age_retraite,
        salaire=salaire_actuel,
        capital=capital_lpp
    )

    # ===== COUPLE =====

    if statut_civil == "marie":
        if rente_conjoint <= 0:
            rente_conjoint = AVS_RENTE_MEDIANE

        total = rente_avs + rente_conjoint
        if total > PLAFOND_COUPLE:
            excedent = total - PLAFOND_COUPLE
            ratio = rente_avs / total
            rente_avs -= excedent * ratio
            rente_conjoint -= excedent * (1 - ratio)

    # ===============================================================
    #  ANALYSE PATRIMONIALE (pré-paiement)
    # ===============================================================

    annees_validees = min(annees_avs, CARRIERE_PLEINE)
    annees_manquantes = max(0, CARRIERE_PLEINE - annees_validees)

    perte_pct = annees_manquantes / CARRIERE_PLEINE if CARRIERE_PLEINE else 0

    impact_mensuel = AVS_RENTE_MAX * perte_pct
    impact_annuel = impact_mensuel * 12
    projection_20_ans = impact_annuel * 20

    montant_recuperable = projection_20_ans * 0.6  # hypothèse prudente

    # ===== RETURN FINAL =====

    return {
        # rentes
        "rente_avs": round(rente_avs, 2),
        "rente_lpp": lpp["rente_mensuelle"],
        "rente_conjoint": round(rente_conjoint, 2),
        "total_retraite": round(rente_avs + lpp["rente_mensuelle"] + rente_conjoint, 2),

        # prépaiement
        "annees_validees": annees_validees,
        "annees_manquantes": annees_manquantes,
        "impact_pct": round(perte_pct * 100, 1),
        "impact_mensuel": round(impact_mensuel, 2),
        "impact_annuel": round(impact_annuel, 2),
        "projection_20_ans": round(projection_20_ans, 2),
        "montant_recuperable": round(montant_recuperable, 2),

        # détails
        "details": {
            "avs": avs,
            "lpp": lpp,
            "annees_total": annees_total
        }
    }
