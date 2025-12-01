# simulateur.py
# ---------------------------------------------------------
# Module de calcul complet pour AVS + LPP avec gestion
# des valeurs vides, erreurs de conversion, defaults, etc.
# ---------------------------------------------------------

def to_int(v, default=0):
    """Convertit en int sans planter."""
    try:
        if v is None or v == "":
            return default
        return int(v)
    except:
        return default

def to_float(v, default=0.0):
    """Convertit en float sans planter."""
    try:
        if v is None or v == "":
            return default
        return float(v)
    except:
        return default


# ---------------------------------------------------------
# CALCUL DU 1ER PILIER (AVS)
# ---------------------------------------------------------

def calcul_avs(age_actuel, age_retraite, annees_cotisees, ramd, statut_civil="célibataire"):
    """
    Calcule une estimation simplifiée de la rente AVS.
    """

    duree_cotisation_max = 44  # Durée de cotisation maximale AVS
    taux_cotisation = min(annees_cotisees / duree_cotisation_max, 1)

    # Simulation d'une rente basée sur RAMD (salaire annuel moyen)
    rente_max = 2390 * 12  # Approximation rente mensuelle max → annuelle
    rente_estimee = rente_max * taux_cotisation

    return max(0, rente_estimee)


# ---------------------------------------------------------
# CALCUL DU 2E PILIER (LPP)
# ---------------------------------------------------------

def calcul_lpp(capital_lpp, age_actuel, age_retraite):
    """
    Simule la rente LPP basée sur un capital et un taux de conversion.
    """

    # Hypothèse du taux de conversion standard
    taux_conversion = 0.068  # 6.8%

    rente_lpp = capital_lpp * taux_conversion
    return max(0, rente_lpp)


# ---------------------------------------------------------
# CALCUL COMPLET (1er + 2e PILLER)
# ---------------------------------------------------------

def simuler_pilier_complet(data):
    """
    Point d'entrée appelé depuis FastAPI.
    Convertit toutes les données en numériques safely puis lance les calculs.
    """

    age_actuel = to_int(data.get("age_actuel"))
    age_retraite = to_int(data.get("age_retraite"), 65)

    revenu_annuel = to_float(data.get("revenu_annuel"))
    ramd = to_float(data.get("ramd"))

    annees_cotisees = to_int(data.get("annees_cotisees"))
    annees_be = to_int(data.get("annees_be"))
    annees_ba = to_int(data.get("annees_ba"))

    capital_lpp = to_float(data.get("capital_lpp"))
    statut_civil = data.get("statut_civil", "célibataire")

    # Total AVS = AVS + bonifications éducatives + assistance
    total_cotisation = annees_cotisees + annees_be + annees_ba

    rente_avs = calcul_avs(
        age_actuel=age_actuel,
        age_retraite=age_retraite,
        annees_cotisees=total_cotisation,
        ramd=ramd,
        statut_civil=statut_civil
    )

    rente_lpp = calcul_lpp(
        capital_lpp=capital_lpp,
        age_actuel=age_actuel,
        age_retraite=age_retraite
    )

    rente_totale = rente_avs + rente_lpp

    return {
        "rente_avs": rente_avs,
        "rente_lpp": rente_lpp,
        "rente_totale": rente_totale,
        "details": {
            "age_actuel": age_actuel,
            "age_retraite": age_retraite,
            "ramd": ramd,
            "revenu_annuel": revenu_annuel,
            "annees_cotisees": annees_cotisees,
            "annees_be": annees_be,
            "annees_ba": annees_ba,
            "capital_lpp": capital_lpp
        }
    }
