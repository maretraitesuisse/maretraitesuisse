import json
from pdf_generator import generer_pdf_retraite

# Charge les données de test
with open("debug_donnees.json", "r", encoding="utf-8") as f:
    donnees = json.load(f)

with open("debug_resultats.json", "r", encoding="utf-8") as f:
    resultats = json.load(f)

# Génère le PDF
out = generer_pdf_retraite(donnees=donnees, resultats=resultats, output="preview.pdf")
print("PDF généré :", out)
