# ===============================================================
#  Simulateur Retraite Suisse — AVS + LPP
#  Traduction STRICTE du moteur React fourni
#  Base légale : Échelle 44 (2026)
# ===============================================================

from dataclasses import dataclass
from typing import Optional, Dict


# ===============================================================
#  CONSTANTES (identiques au React)
# ===============================================================

AVS_RENTE_MAX = 2520
AVS_RENTE_MIN = 1260
AVS_RENTE_MEDIANE = 1890

SEUIL_MAX_RAMD = 90720
CARRIERE_PLEINE = 44
PLAFOND_COUPLE = 3780

BONIF_CREDIT = 3 * AVS_RENTE_MIN * 12  # Bonification annuelle
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
#  OUTILS
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

def reconstruire_lpp(age_actuel: int, salaire_actuel: float, annees_cotisees: int) -> float:
    age_debut = max(25, age_actuel - annees_cotisees)
    if age_actuel <= age_debut:
        return 0.0

    capital = 0.0
    annees = age_actuel - age_debut
    salaire = salaire_actuel / (1.005 ** annees)

    for age in range(age_debut, age_actuel):
        if age > age_debut:
            salaire *= 1.005
        taux = get_taux_epargne(age)
        salaire_coord = calcul_salaire_coordonne(salaire)
        capital += salaire_coord * taux

    return capital


def calculer_lpp(age_actuel: int, age_retraite: int, salaire_initial: float, capital_initial: float) -> Dict:
    capital = capital_initial
    salaire = salaire_initial

    for age in range(age_actuel, age_retraite):
        salaire *= 1.005
        taux = get_taux_epargne(age)
        salaire_coord = calcul_salaire_coordonne(salaire)
        capital += salaire_coord * taux

    rente_annuelle = capital * TAUX_CONVERSION

    return {
        "capital_final": capital,
        "rente_mensuelle": rente_annuelle / 12
    }


# ===============================================================
#  AVS
# ===============================================================

def calculer_avs(
    salaire_moyen: float,
    annees_total: int,
    annees_be: int = 0,
    annees_ba: int = 0
) -> Dict:

    total_bonif = ((annees_be + annees_ba) * BONIF_CREDIT) / max(annees_total, 1)
    ramd = salaire_moyen + total_bonif

    if ramd >= SEUIL_MAX_RAMD:
        rente_theo = AVS_RENTE_MAX
    elif ramd <= 0:
        rente_theo = AVS_RENTE_MIN
    else:
        rente_theo = AVS_RENTE_MIN + (AVS_RENTE_MAX - AVS_RENTE_MIN) * (ramd / SEUIL_MAX_RAMD)

    if annees_total < CARRIERE_PLEINE:
        reduction = (CARRIERE_PLEINE - annees_total) / CARRIERE_PLEINE
        rente_theo *= (1 - reduction)

    rente_finale = max(rente_theo, AVS_RENTE_MIN)

    return {
        "ramd": ramd,
        "rente_theorique": rente_theo,
        "rente_finale": rente_finale
    }


# ===============================================================
#  SIMULATEUR PRINCIPAL
# ===============================================================

def simulateur_avs_lpp(donnees: Dict) -> Dict:
    age_actuel = int(donnees["age_actuel"])
    age_retraite = int(donnees["age_retraite"])
    salaire_actuel = float(donnees["salaire_actuel"])
    salaire_moyen = float(donnees["salaire_moyen"])
    annees_cotisees = int(donnees["annees_cotisees"])

    annees_be = int(donnees.get("annees_be", 0))
    annees_ba = int(donnees.get("annees_ba", 0))

    statut_pro = donnees["statut_pro"]
    statut_civil = donnees["statut_civil"]

    annees_restantes = age_retraite - age_actuel
    annees_total = annees_cotisees + annees_restantes

    # ================= LPP =================
    capital_initial = float(donnees.get("capital_lpp", 0))
    source_lpp = "Saisie client"

    if statut_pro == "independant":
        if donnees.get("cotise_lpp") == "non":
            capital_initial = 0.0
            source_lpp = "Indépendant sans LPP"
        else:
            annees_lpp = int(donnees.get("annees_lpp_indep", 0))
            if capital_initial == 0 and annees_lpp > 0:
                capital_initial = 0.0
                for age in range(age_actuel - annees_lpp, age_actuel):
                    salaire_coord = calcul_salaire_coordonne(salaire_actuel)
                    taux = get_taux_epargne(age)
                    cotisation = salaire_coord * taux
                    capital_initial += cotisation * (1.01 ** (age_actuel - age))
                source_lpp = f"Estimé ({annees_lpp} ans)"

    else:
        if capital_initial == 0:
            capital_initial = reconstruire_lpp(age_actuel, salaire_actuel, annees_cotisees)
            source_lpp = "Estimé (conservateur)"

    lpp = calculer_lpp(age_actuel, age_retraite, salaire_actuel, capital_initial)

    # ================= AVS =================
    avs = calculer_avs(salaire_moyen, annees_total, annees_be, annees_ba)

    rente_avs = avs["rente_finale"]
    rente_conjoint = 0.0
    plafonnement = None

    if statut_civil == "marie":
        if donnees.get("rente_conjoint"):
            rente_conjoint = float(donnees["rente_conjoint"])
        else:
            rente_conjoint = AVS_RENTE_MEDIANE

        total = rente_avs + rente_conjoint
        if total > PLAFOND_COUPLE:
            excedent = total - PLAFOND_COUPLE
            ratio = rente_avs / total
            rente_avs -= excedent * ratio
            rente_conjoint -= excedent * (1 - ratio)
            plafonnement = True

    rente_totale = rente_avs + lpp["rente_mensuelle"]

    return {
        "avs": avs,
        "lpp": {
            "capital_initial": capital_initial,
            "capital_final": lpp["capital_final"],
            "rente_mensuelle": lpp["rente_mensuelle"],
            "source": source_lpp
        },
        "rente_avs_finale": rente_avs,
        "rente_conjoint": rente_conjoint,
        "rente_totale_mensuelle": rente_totale,
        "annees_total": annees_total,
        "plafonnement_couple": plafonnement
    }
