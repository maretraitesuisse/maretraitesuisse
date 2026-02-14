from simulateur_avs_lpp import calcul_complet_retraite
from pdf_generator import generer_pdf_retraite

donnees_test = {
    "prenom": "Theo",
    "nom": "Test",
    "age_actuel": 40,
    "age_retraite": 65,
    "salaire_actuel": 80000,
    "salaire_moyen": 75000,
    "annees_cotisees": 30,
    "annees_be": 0,
    "annees_ba": 0,
    "statut_civil": "celibataire",
    "statut_pro": "salarie",
    "capital_lpp": 100000,
    "rente_conjoint": 0,
}

resultats = calcul_complet_retraite(donnees_test)

print("RESULTATS KEYS:", resultats.keys())
print("PDF_DATA KEYS:", resultats.get("pdf_data", {}).keys())
print("SYNTHÈSE:", resultats["pdf_data"]["synthese"])
print("AVS DETAIL:", resultats["pdf_data"]["avs_detail"])
print("LPP DETAIL:", resultats["pdf_data"]["lpp_detail"])

generer_pdf_retraite(donnees_test, resultats, output="TEST_DEBUG.pdf")
