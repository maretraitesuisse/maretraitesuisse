# simulateur_avs_lpp.py
# ===============================================================
#  Module central : Calcul complet retraite AVS + LPP
# ===============================================================

def calcul_rente_avs(donnees):
    """
    Calcule la rente AVS théorique selon :
    - salaire moyen AVS
    - années AVS cotisées
    - statut civil
    """

    salaire_moyen = donnees["salaire_moyen_avs"]
    annees = donnees["annees_avs"]
    statut = donnees["statut_civil"].lower()

    # Taux plein AVS pour 44 ans
    taux_cotisation = min(annees / 44, 1)

    # Barème AVS 2024
    if statut == "marie":
        rente_max = 1785 * 12
        rente_min = 1195 * 12
    else:
        rente_max = 2390 * 12
        rente_min = 1195 * 12

    # Salaire moyen → rente théorique
    # Approximatif mais conforme aux calculs AVS communs
    facteur = salaire_moyen / 86400  # Valeur moyenne AVS
    facteur = max(0.25, min(facteur, 1))  # plafonné entre 25% et 100%

    rente = rente_min + (rente_max - rente_min) * facteur

    # Ajustement selon années cotisées
    rente *= taux_cotisation

    return round(rente)


def calcul_rente_lpp(donnees):
    """
    Calcule la rente LPP selon le capital et le taux de conversion.
    """

    capital = donnees["capital_lpp"]
    age = donnees["age_retraite"]

    # Barème taux conversion Suisse
    if age >= 65:
        taux = 0.068
    elif age >= 64:
        taux = 0.065
    elif age >= 63:
        taux = 0.063
    else:
        taux = 0.06

    rente = capital * taux
    return round(rente)


def calcul_complet_retraite(donnees):
    """
    Combine :
    - AVS
    - LPP
    - + options conjoints
    """

    avs = calcul_rente_avs(donnees)
    lpp = calcul_rente_lpp(donnees)

    total = avs + lpp + donnees.get("rente_conjoint", 0)

    return {
        "rente_avs": avs,
        "rente_lpp": lpp,
        "rente_conjoint": donnees.get("rente_conjoint", 0),
        "total_retraite": total
    }

