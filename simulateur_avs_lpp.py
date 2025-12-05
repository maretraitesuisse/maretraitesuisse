# simulateur_avs_lpp.py
# ===============================================================
#  Module central : Calcul complet retraite AVS + LPP
#  Version PRO — Stable et optimisée
# ===============================================================

def calcul_rente_avs(donnees):
    """
    Calcule la rente AVS théorique :
    - salaire moyen AVS
    - années AVS cotisées
    - statut civil
    """

    salaire_moyen = float(donnees["salaire_moyen_avs"])
    annees = int(donnees["annees_avs"])
    statut = donnees["statut_civil"].strip().lower()

    # Taux de cotisation AVS — années cotisées (max 44 ans)
    taux_cotisation = min(annees / 44, 1)

    # Barème AVS 2024
    if statut == "marié" or statut == "marie":
        rente_max = 1785 * 12
        rente_min = 1195 * 12
    else:
        rente_max = 2390 * 12
        rente_min = 1195 * 12

    # Calcul du facteur AVS selon le RAMD
    facteur = salaire_moyen / 86400  
    facteur = max(0.25, min(facteur, 1))  # min 25%, max 100%

    rente = rente_min + (rente_max - rente_min) * facteur
    rente *= taux_cotisation

    return round(rente)


def calcul_rente_lpp(donnees):
    """
    Calcule la rente LPP annuelle selon le capital accumulé 
    et le taux de conversion (selon âge légal).
    """

    capital = float(donnees["capital_lpp"])
    age = int(donnees["age_retraite"])

    # Barème taux Suisse
    if age >= 65:
        taux = 0.068
    elif age == 64:
        taux = 0.065
    elif age == 63:
        taux = 0.063
    else:
        taux = 0.06

    rente = capital * taux
    return round(rente)


def calcul_complet_retraite(donnees):
    """
    Combine :
    - Rente AVS
    - Rente LPP
    - Rente conjoint éventuelle
    """

    avs = calcul_rente_avs(donnees)
    lpp = calcul_rente_lpp(donnees)
    conjoint = float(donnees.get("rente_conjoint", 0))

    total = avs + lpp + conjoint

    return {
        "rente_avs": avs,
        "rente_lpp": lpp,
        "rente_conjoint": conjoint,
        "total_retraite": total
    }
