# simulateur.py
# -------------------------------------------------------------------
# Ce fichier contient TOUTE la logique du simulateur AVS + LPP.
# Il convertit tes données du Google Sheet en un résultat de calcul.
#
# Le but : exposer une fonction simple
#
#     def simuler_pilier_complet(data):
#
# qui renvoie un dictionnaire prêt à afficher ou à envoyer par email.
# -------------------------------------------------------------------

def calcul_rente_avs(
    age_actuel,
    age_retraite,
    salaire_moyen_avs,
    annees_avs_cotisees,
    be,
    ba,
    statut_civil,
    rente_conjoint_actuelle
):
    """
    Simule la rente AVS basée sur les données fournies.
    Ce modèle est simplifié mais structure le calcul correctement.

    1. Salaire moyen AVS (RAMD) influence la rente de base
    2. Nombre d’années AVS → pénalités ou bonifications
    3. BE / BA → majorations
    4. Statut civil → plafonnement des couples
    """

    # Valeurs AVS officielles 2024 approximées pour une personne seule
    RENTE_MAX = 2450
    RENTE_MIN = 1225
    ANNEES_PLEINES = 44  # pour un homme ou femme

    # Ratio d'années cotisées
    ratio_cotisation = min(annees_avs_cotisees / ANNEES_PLEINES, 1)

    # Calcul rente de base selon RAMD
    if salaire_moyen_avs < 43000:
        rente_base = RENTE_MIN
    elif salaire_moyen_avs > 86000:
        rente_base = RENTE_MAX
    else:
        # interpolation linéaire entre min et max
        rente_base = RENTE_MIN + (RENTE_MAX - RENTE_MIN) * (
            (salaire_moyen_avs - 43000) / (86000 - 43000)
        )

    # On applique la proportion des années cotisées
    rente = rente_base * ratio_cotisation

    # Ajout BE / BA
    rente += be * 40  # valeur indicative
    rente += ba * 50  # valeur indicative

    # Plafonnement couples AVS
    if statut_civil.lower() == "marié" or statut_civil.lower() == "marie":
        total_couple = rente + rente_conjoint_actuelle
        plafond_couple = RENTE_MAX * 1.5
        if total_couple > plafond_couple:
            excedent = total_couple - plafond_couple
            rente -= excedent

    return round(rente, 2)


def calcul_rente_lpp(capital_lpp, age_retraite):
    """
    Calcule la rente LPP à partir du capital en appliquant
    le taux de conversion approximatif basé sur l’âge.
    """

    if age_retraite <= 62:
        taux = 0.052
    elif age_retraite == 63:
        taux = 0.055
    elif age_retraite == 64:
        taux = 0.057
    else:
        taux = 0.060

    rente = capital_lpp * taux
    return round(rente, 2)


def simuler_pilier_complet(data):
    """
    Fonction principale appelée par l'API.
    Elle prend un dictionnaire contenant toutes les valeurs du Google Sheet.

    Retourne : {
        "rente_avs": ...,
        "rente_lpp": ...,
        "rente_totale": ...,
        "details": "Texte humain pour email"
    }
    """

    rente_avs = calcul_rente_avs(
        age_actuel=int(data["age_actuel"]),
        age_retraite=int(data["age_retraite"]),
        salaire_moyen_avs=float(data["salaire_moyen_avs"]),
        annees_avs_cotisees=int(data["annees_cotisees"]),
        be=int(data["be"]),
        ba=int(data["ba"]),
        statut_civil=data["statut_civil"],
        rente_conjoint_actuelle=float(data["rente_conjoint"])
    )

    rente_lpp = calcul_rente_lpp(
        capital_lpp=float(data["capital_lpp"]),
        age_retraite=int(data["age_retraite"])
    )

    total = rente_avs + rente_lpp

    # Texte explicatif
    texte = f"""
    Simulation de retraite complète :

    • Rente AVS estimée : CHF {rente_avs}
    • Rente LPP estimée : CHF {rente_lpp}
    • Total mensuel estimé : CHF {total}

    Basé sur :
    - {data['annees_cotisees']} années AVS cotisées
    - Salaire moyen AVS (RAMD) : {data['salaire_moyen_avs']} CHF/an
    - Capital LPP actuel : {data['capital_lpp']} CHF

    Cette simulation reste indicative selon les valeurs officielles AVS/LPP.
    """

    return {
        "rente_avs": rente_avs,
        "rente_lpp": rente_lpp,
        "rente_totale": total,
        "details": texte
    }

