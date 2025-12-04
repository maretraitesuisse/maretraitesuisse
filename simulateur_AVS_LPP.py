# ================================================================
#       SIMULATEUR COMPLET AVS + LPP — Version API
# ================================================================
# Ton script original a été transformé en une fonction web :
# calcul_complet_retraite(donnees)
# qui retourne un dictionnaire propre pour le PDF et l’admin.
# ================================================================

import math

# === CONSTANTES AVS ===
AVS_RENTE_MAX_MENSUELLE = 2520.00
AVS_RENTE_MIN_MENSUELLE = 1260.00
SEUIL_MAX_RAMD = 90720.00
CARRIERE_PLEINE = 44
BONIF_CREDIT_ANNUEL = 3 * AVS_RENTE_MIN_MENSUELLE * 12
PLAFOND_COUPLE = 3780.00

# === CONSTANTES LPP ===
DEDUCTION_COORDINATION = 26460
SEUIL_ENTREE_LPP = 22680
TAUX_CONVERSION = 0.058
TAUX_CROISSANCE_PASSE = 0.005
TAUX_CROISSANCE_FUTUR = 0.005
TAUX_RENDEMENT = 0.00  # projection ultra conservatrice

TAUX_LPP = {
    25: 0.07,
    35: 0.10,
    45: 0.15,
    55: 0.18
}


# ================================================================
# FONCTIONS UTILITAIRES
# ================================================================
def salaire_coordonne(salaire):
    if salaire <= SEUIL_ENTREE_LPP:
        return 0
    return max(0, min(salaire - DEDUCTION_COORDINATION, 62475))


def taux_epargne(age):
    if age < 25:
        return 0
    if age <= 34:
        return TAUX_LPP[25]
    if age <= 44:
        return TAUX_LPP[35]
    if age <= 54:
        return TAUX_LPP[45]
    return TAUX_LPP[55]


# ================================================================
# RECONSTRUCTION LPP SI CAPITAL INCONNU
# ================================================================
def reconstruire_capital_lpp(age_actuel, salaire_actuel, annees_avs):
    age_debut = max(25, age_actuel - annees_avs)
    if age_actuel <= age_debut:
        return 0

    capital = 0
    salaire_estime = salaire_actuel / ((1 + TAUX_CROISSANCE_PASSE) ** (age_actuel - age_debut))

    for age in range(age_debut, age_actuel):
        if age > age_debut:
            salaire_estime *= (1 + TAUX_CROISSANCE_PASSE)

        sc = salaire_coordonne(salaire_estime)
        capital = capital * (1 + TAUX_RENDEMENT) + sc * taux_epargne(age)

    return capital


# ================================================================
# CALCUL AVS
# ================================================================
def calcul_avs(salaire_moyen, annees_cotisees, annees_be, annees_ba):
    annees = max(1, annees_cotisees)
    bonification = ((annees_be + annees_ba) * BONIF_CREDIT_ANNUEL) / annees
    ramd = salaire_moyen + bonification

    if ramd >= SEUIL_MAX_RAMD:
        rente_theo = AVS_RENTE_MAX_MENSUELLE
    else:
        ratio = max(0, min(1, ramd / SEUIL_MAX_RAMD))
        rente_theo = AVS_RENTE_MIN_MENSUELLE + ratio * (AVS_RENTE_MAX_MENSUELLE - AVS_RENTE_MIN_MENSUELLE)

    if annees >= CARRIERE_PLEINE:
        rente_finale = rente_theo
    else:
        manque = CARRIERE_PLEINE - annees
        reduction = rente_theo * (manque / CARRIERE_PLEINE)
        rente_finale = max(AVS_RENTE_MIN_MENSUELLE, rente_theo - reduction)

    return rente_finale, rente_theo, ramd, annees


# ================================================================
# CALCUL LPP FUTUR
# ================================================================
def projection_lpp(age_actuel, age_retraite, salaire, capital_initial):
    capital = capital_initial
    salaire_annuel = salaire

    for age in range(age_actuel, age_retraite):
        salaire_annuel *= (1 + TAUX_CROISSANCE_FUTUR)
        sc = salaire_coordonne(salaire_annuel)
        capital = capital * (1 + TAUX_RENDEMENT) + sc * taux_epargne(age)

    rente_mensuelle = (capital * TAUX_CONVERSION) / 12
    return capital, rente_mensuelle


# ================================================================
# FONCTION PRINCIPALE – API
# ================================================================
def calcul_complet_retraite(d):
    # Extraction données
    age = d["age_actuel"]
    age_r = d["age_retraite"]
    salaire = d["salaire_annuel"]
    salaire_moyen = d["salaire_moyen_avs"]
    annees_avs = d["annees_avs"]
    annees_be = d["annees_be"]
    annees_ba = d["annees_ba"]
    statut = d["statut_civil"]
    capital_lpp = d["capital_lpp"]
    rente_conjoint = d["rente_conjoint"]

    # CAPITAL LPP – fallback si client n’a pas de chiffre
    if capital_lpp in ["", None, 0, "0"]:
        capital_lpp = reconstruire_capital_lpp(age, salaire, annees_avs)
        source_lpp = "Reconstruit"
    else:
        capital_lpp = float(capital_lpp)
        source_lpp = "Déclaré"

    # CALCUL LPP
    capital_final, rente_lpp = projection_lpp(age, age_r, salaire, capital_lpp)

    # CALCUL AVS
    annees_totales = annees_avs + (age_r - age)
    rente_avs_finale, rente_theo, ramd, annees_calc = calcul_avs(
        salaire_moyen, annees_totales, annees_be, annees_ba
    )

    rente_avs_user = rente_avs_finale
    rente_conjoint_final = rente_conjoint

    # PLAFONNEMENT AVS COUPLE
    if statut.lower() == "marié":
        total_theorique = rente_avs_user + rente_conjoint
        if total_theorique > PLAFOND_COUPLE:
            excedent = total_theorique - PLAFOND_COUPLE
            ratio = rente_avs_user / total_theorique
            rente_avs_user -= excedent * ratio
            rente_conjoint_final -= excedent * (1 - ratio)

    # TOTAL
    total = rente_avs_user + rente_lpp

    # PRI (Analyse ton B, professionnelle + chaleureuse)
    diagnostic = []
    if annees_totales < 30:
        diagnostic.append("Vos années AVS cotisées sont en-dessous de la moyenne ; une vérification auprès de la caisse AVS est conseillée.")
    else:
        diagnostic.append("Vos années AVS semblent cohérentes pour une carrière stable.")

    if capital_lpp < 50000 and age > 35:
        diagnostic.append("Votre capital LPP semble faible par rapport à votre âge. Un audit de votre caisse pourrait optimiser votre avenir.")
    else:
        diagnostic.append("Votre capital LPP est dans une zone cohérente pour votre âge.")

    if total < 3000:
        diagnostic.append("Votre rente totale estimée est relativement basse ; une stratégie d'épargne complémentaire peut être pertinente.")

    return {
        "prenom": d["prenom"],
        "nom": d["nom"],
        "email": d["email"],
        "capital_lpp_initial": capital_lpp,
        "capital_lpp_source": source_lpp,
        "capital_lpp_final": capital_final,
        "rente_lpp": rente_lpp,
        "rente_avs": rente_avs_user,
        "rente_conjoint": rente_conjoint_final,
        "total_retraite": total,
        "ramd": ramd,
        "diagnostic": diagnostic
    }
