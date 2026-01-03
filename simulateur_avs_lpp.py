# ===============================================================
#  Simulateur Retraite Suisse — AVS + LPP
#  Moteur OFFICIEL BACKEND — VERSION FINALE
# ===============================================================

from typing import Dict

# ===============================================================
# CONSTANTES AVS
# ===============================================================

AVS_RENTE_MAX = 2520
AVS_RENTE_MIN = 1260
AVS_RENTE_MEDIANE = 1890
LPP_REFERENCE_MENSUELLE = 1500  # rente mensuelle LPP "saine" de référence
RAMD_MAX = 90720
CARRIERE_PLEINE = 44
REDUCTION_PAR_ANNEE = 0.0227  # 2.27%
BONIF_ANNUEL = 45360         # 3 × rente min × 12
PLAFOND_COUPLE = 3780        # 150% rente max

# ===============================================================
# CONSTANTES LPP
# ===============================================================

DEDUCTION_COORD = 26460
SEUIL_ENTREE_LPP = 22680
SALAIRE_MAX_LPP = 88200
TAUX_CONVERSION_LPP = 0.058

TAUX_EPARGNE = {
    "25-34": 0.07,
    "35-44": 0.10,
    "45-54": 0.15,
    "55+": 0.18,
}

# ===============================================================
# OUTILS
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


def salaire_coordonne(salaire: float) -> float:
    if salaire < SEUIL_ENTREE_LPP:
        return 0.0
    salaire_assure = min(salaire, SALAIRE_MAX_LPP)
    return max(0.0, salaire_assure - DEDUCTION_COORD)


def rente_complete_avs(ramd: float) -> float:
    if ramd >= RAMD_MAX:
        return AVS_RENTE_MAX
    ratio = max(0.0, ramd / RAMD_MAX)
    return AVS_RENTE_MIN + (AVS_RENTE_MAX - AVS_RENTE_MIN) * ratio


# ===============================================================
# AVS
# ===============================================================

def calcul_avs(
    salaire_moyen: float,
    annees_cotisees: int,
    annees_be: int,
    annees_ba: int
) -> Dict:

    annees_validees = min(annees_cotisees, CARRIERE_PLEINE)
    annees_manquantes = max(0, CARRIERE_PLEINE - annees_validees)

    bonifications = (
        (annees_be + annees_ba) * BONIF_ANNUEL / max(annees_validees, 1)
    )

    ramd = salaire_moyen + bonifications
    rente_complete = rente_complete_avs(ramd)

    taux_reduction = annees_manquantes * REDUCTION_PAR_ANNEE
    rente_finale = rente_complete * (1 - min(taux_reduction, 1))

    return {
        "annees_validees": annees_validees,
        "annees_manquantes": annees_manquantes,
        "ramd": round(ramd, 2),
        "rente_complete": round(rente_complete, 2),
        "rente_finale": round(rente_finale, 2),
        "impact_pct": round(taux_reduction * 100, 1)
    }


# ===============================================================
# LPP
# ===============================================================
def calcul_lpp(
    age_actuel: int,
    age_retraite: int,
    salaire_actuel: float,
    capital_initial: float,
    statut_pro: str
) -> Dict:

    if statut_pro == "independant":
        return {
            "capital_final": capital_initial,
            "rente_mensuelle": 0.0
        }

    capital = capital_initial
    salaire = salaire_actuel

    # === AJOUT PDF PREMIUM (SANS IMPACT CALCUL) ===
    capital_history = []
    # ============================================

    for age in range(age_actuel, age_retraite):
        taux = get_taux_epargne(age)
        sc = salaire_coordonne(salaire)
        capital += sc * taux
        salaire *= 1.005  # progression salariale prudente

        # === AJOUT PDF PREMIUM (COPIE PASSIVE) ===
        capital_history.append({
            "age": age,
            "capital": round(capital, 2)
        })
        # ========================================

    rente_mensuelle = (capital * TAUX_CONVERSION_LPP) / 12

    return {
        "capital_final": round(capital, 2),
        "rente_mensuelle": round(rente_mensuelle, 2),

        # === AJOUT PDF PREMIUM ===
        "capital_history": capital_history
        # ========================
    }



# ===============================================================
# POINT D’ENTRÉE — UTILISÉ PAR main.py
# ===============================================================

def calcul_complet_retraite(donnees: Dict) -> Dict:

    # ===== EXTRACTION =====

    age_actuel = int(donnees.get("age_actuel", 0))
    age_retraite = int(donnees.get("age_retraite", 65))

    salaire_actuel = float(donnees.get("salaire_actuel", 0))
    salaire_moyen = float(donnees.get("salaire_moyen", 0))

    annees_cotisees = int(donnees.get("annees_cotisees", 0))
    annees_be = int(donnees.get("annees_be", 0))
    annees_ba = int(donnees.get("annees_ba", 0))

    statut_civil = donnees.get("statut_civil", "celibataire")
    statut_pro = donnees.get("statut_pro", "salarie")

    capital_lpp = float(donnees.get("capital_lpp", 0))
    rente_conjoint = float(donnees.get("rente_conjoint", 0))

    # ===== AVS =====

    avs = calcul_avs(
        salaire_moyen,
        annees_cotisees,
        annees_be,
        annees_ba
    )

    rente_avs = avs["rente_finale"]

    # ===== LPP =====

    lpp = calcul_lpp(
        age_actuel,
        age_retraite,
        salaire_actuel,
        capital_lpp,
        statut_pro
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

        
    # ===== PRÉPAIEMENT / MANQUE À GAGNER GLOBAL =====

    # Référence LPP selon statut
    if statut_pro == "independant" and capital_lpp <= 0:
        lpp_reference = LPP_REFERENCE_MENSUELLE
    else:
        lpp_reference = lpp["rente_mensuelle"]

    rente_reference_totale = avs["rente_complete"] + lpp_reference
    rente_reelle_totale = rente_avs + lpp["rente_mensuelle"]

    perte_mensuelle = rente_reference_totale - rente_reelle_totale
    perte_annuelle = perte_mensuelle * 12
    projection_20_ans = perte_annuelle * 20


    # ===== OPTIMISATION =====

    annees_rachables = min(5, avs["annees_manquantes"])
    montant_recuperable = perte_annuelle * annees_rachables
    economie_fiscale = montant_recuperable * 0.25

    # === AJOUT PDF PREMIUM (SANS IMPACT FRONT) ===

    total_mensuel = rente_avs + lpp["rente_mensuelle"]
    total_annuel = total_mensuel * 12

    pdf_data = {
        "synthese": {
            "avs_mensuel": round(rente_avs, 2),
            "lpp_mensuel": round(lpp["rente_mensuelle"], 2),
            "total_mensuel": round(total_mensuel, 2),
            "total_annuel": round(total_annuel, 2),
            "part_avs_pct": round((rente_avs / total_mensuel) * 100, 1) if total_mensuel > 0 else 0,
            "part_lpp_pct": round((lpp["rente_mensuelle"] / total_mensuel) * 100, 1) if total_mensuel > 0 else 0,
        },
        "avs_detail": avs,
        "lpp_detail": {
            "capital_final": lpp["capital_final"],
            "rente_mensuelle": lpp["rente_mensuelle"],
            "capital_history": lpp.get("capital_history", [])
        }
    }

    # ============================================


# ============================================


    # ===== RETURN =====

    return {
        "annees_validees": f'{avs["annees_validees"]}/44',
        "annees_manquantes": avs["annees_manquantes"],
        "impact_pct": -avs["impact_pct"],
        "impact_mensuel": round(-perte_mensuelle, 2),
        "impact_annuel": round(-perte_annuelle, 2),
        "projection_20_ans": round(-projection_20_ans, 2),
        "montant_recuperable": round(montant_recuperable, 2),
        "economie_fiscale": round(economie_fiscale, 2),
        "pdf_data": pdf_data
    }
