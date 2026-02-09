from typing import Dict
from calculateur_retraite import calculer_retraite_complete

# Valeurs utilisées dans ton système actuel
LPP_REFERENCE_MENSUELLE = 1500
RENTE_AVS_REFERENCE_CARRIERE_COMPLETE = 2520.0


def calcul_complet_retraite(donnees: Dict) -> Dict:
    age_actuel = int(donnees.get("age_actuel", 0))
    age_retraite = int(donnees.get("age_retraite", 65))

    salaire_actuel = float(donnees.get("salaire_actuel", 0))
    salaire_moyen = float(donnees.get("salaire_moyen", 0))

    annees_cotisees = int(donnees.get("annees_cotisees", 0))
    annees_be = int(donnees.get("annees_be", 0))
    annees_ba = int(donnees.get("annees_ba", 0))

    statut_civil = (donnees.get("statut_civil") or "celibataire").strip().lower()
    statut_pro = (donnees.get("statut_pro") or "salarie").strip().lower()

    capital_lpp = float(donnees.get("capital_lpp", 0))
    rente_conjoint = float(donnees.get("rente_conjoint", 0))

    # ✅ Logique indépendant (comme ton ancien système)
    if statut_pro == "independant":
        capital_lpp_calc = 0.0
    else:
        capital_lpp_calc = capital_lpp

    # ✅ Gestion conjoint (si marié)
    situation_conjoint = None
    rente_conjoint_param = None
    if statut_civil == "marie":
        if rente_conjoint > 0:
            situation_conjoint = "sait"
            rente_conjoint_param = rente_conjoint
        else:
            situation_conjoint = "ne_sait_pas"

    data_calc = calculer_retraite_complete(
        age_actuel=age_actuel,
        age_retraite=age_retraite,
        statut_civil=statut_civil,
        salaire_actuel=salaire_actuel,
        salaire_moyen=salaire_moyen,
        annees_cotisees=annees_cotisees,
        annees_bonif_education=annees_be,
        annees_bonif_assistance=annees_ba,
        capital_lpp=capital_lpp_calc,
        situation_conjoint=situation_conjoint,
        rente_conjoint=rente_conjoint_param,
    )

    avs = data_calc["avs"]
    lpp = data_calc["lpp"]

    rente_avs = float(avs["rente"])
    rente_lpp = float(lpp["rente_mensuelle"])

    # ✅ Référence LPP pour indépendant sans capital (comme avant)
    if statut_pro == "independant" and capital_lpp <= 0:
        lpp_reference = LPP_REFERENCE_MENSUELLE
    else:
        lpp_reference = rente_lpp

    rente_reference_totale = RENTE_AVS_REFERENCE_CARRIERE_COMPLETE + float(lpp_reference)
    rente_reelle_totale = rente_avs + rente_lpp

    perte_mensuelle = rente_reference_totale - rente_reelle_totale
    perte_annuelle = perte_mensuelle * 12
    projection_20_ans = perte_annuelle * 20

    annees_rachables = min(5, int(avs["annees_manquantes"]))
    montant_recuperable = perte_annuelle * annees_rachables
    economie_fiscale = montant_recuperable * 0.25

    total_mensuel = rente_avs + rente_lpp
    total_annuel = total_mensuel * 12

    
    # =========================================================
    # PDF DATA (SOURCE UNIQUE POUR LE PDF)
    # =========================================================

    # --- Bonifications (toujours un nombre)
    bonifications = float(avs.get("bonifications", 0) or 0)

    # --- Salaire moyen de carrière
    # Priorité :
    # 1) salaire_moyen (fourni / calculé)
    # 2) fallback : RAMD - bonifications
    salaire_moyen_carriere = salaire_moyen if salaire_moyen > 0 else None
    if salaire_moyen_carriere is None:
        try:
            salaire_moyen_carriere = max(0.0, float(avs.get("ramd", 0)) - bonifications)
        except Exception:
            salaire_moyen_carriere = 0.0

    pdf_data = {
        "synthese": {
            "avs_mensuel": round(rente_avs, 2),
            "lpp_mensuel": round(rente_lpp, 2),
            "total_mensuel": round(total_mensuel, 2),
            "total_annuel": round(total_annuel, 2),
            "part_avs_pct": round((rente_avs / total_mensuel) * 100, 1) if total_mensuel > 0 else 0,
            "part_lpp_pct": round((rente_lpp / total_mensuel) * 100, 1) if total_mensuel > 0 else 0,
        },

        "avs_detail": {
            "annees_validees": min(int(data_calc["annees_totales"]), 44),
            "annees_manquantes": int(avs.get("annees_manquantes", 0) or 0),
            "ramd": float(avs.get("ramd", 0) or 0),

            # ✅ OBJECTIF PRINCIPAL
            "salaire_moyen_carriere": round(float(salaire_moyen_carriere or 0), 0),

            # ✅ JAMAIS NONE
            "bonifications": round(float(bonifications or 0), 0),

            # ✅ RENTE DE RÉFÉRENCE OFFICIELLE
            "rente_complete": float(RENTE_AVS_REFERENCE_CARRIERE_COMPLETE),

            "rente_finale": float(avs.get("rente", 0) or 0),
            "impact_pct": float(avs.get("taux_reduction", 0) or 0),
        },

        "lpp_detail": {
            "capital_final": lpp.get("capital_final"),
            "rente_mensuelle": lpp.get("rente_mensuelle"),
            "capital_history": [
                {"age": p.get("age"), "capital": p.get("capital_fin")}
                for p in (lpp.get("projection", []) or [])
            ],
            "salaire_coordonne": lpp.get("salaire_coordonne"),
            "total_cotisations": lpp.get("total_cotisations"),
            "total_interets": lpp.get("total_interets"),
        },

        "scenarios": data_calc.get("scenarios", [])
    }

    return {
        "annees_validees": f'{min(int(data_calc["annees_totales"]), 44)}/44',
        "annees_manquantes": int(avs.get("annees_manquantes", 0) or 0),
        "impact_pct": -float(avs.get("taux_reduction", 0) or 0),
        "impact_mensuel": round(-perte_mensuelle, 2),
        "impact_annuel": round(-perte_annuelle, 2),
        "projection_20_ans": round(-projection_20_ans, 2),
        "montant_recuperable": round(montant_recuperable, 2),
        "economie_fiscale": round(economie_fiscale, 2),
        "pdf_data": pdf_data
    }
