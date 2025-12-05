# ===============================================================
# Génération du PDF Pro — 4 pages
# ===============================================================

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime


# ---------------------------------------------------------------
# OUTILS GRAPHIQUES
# ---------------------------------------------------------------
def titre(pdf, txt, y, size=22):
    pdf.setFont("Helvetica-Bold", size)
    pdf.setFillColor(colors.black)
    pdf.drawString(2*cm, y, txt)


def sous_titre(pdf, txt, y, size=14):
    pdf.setFont("Helvetica-Bold", size)
    pdf.setFillColor(colors.HexColor("#444444"))
    pdf.drawString(2*cm, y, txt)


def texte(pdf, txt, y, size=12):
    pdf.setFont("Helvetica", size)
    pdf.setFillColor(colors.black)
    pdf.drawString(2*cm, y, txt)


def block_info(pdf, label, value, y):
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2*cm, y, label)

    pdf.setFont("Helvetica", 12)
    pdf.drawString(8*cm, y, str(value))


# ---------------------------------------------------------------
# PAGE 1 — Couverture
# ---------------------------------------------------------------
def page_couverture(pdf, donnees):

    largeur, hauteur = A4

    # Bande large haute
    pdf.setFillColor(colors.HexColor("#E8E8E8"))
    pdf.rect(0, hauteur - 4*cm, largeur, 4*cm, fill=True, stroke=False)

    # Titre principal
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(2*cm, hauteur - 2.5*cm, "Analyse Retraite Complète")

    # Sous-titre + date
    pdf.setFont("Helvetica", 14)
    pdf.drawString(2*cm, hauteur - 3.5*cm, f"Émis le : {datetime.now().strftime('%d.%m.%Y')}")

    # Informations client
    sous_titre(pdf, "Informations personnelles", hauteur - 6*cm)

    pdf.setFont("Helvetica", 12)
    pdf.drawString(2*cm, hauteur - 7*cm, f"Nom : {donnees['nom']}")
    pdf.drawString(2*cm, hauteur - 8*cm, f"Prénom : {donnees['prenom']}")
    pdf.drawString(2*cm, hauteur - 9*cm, f"Âge actuel : {donnees['age_actuel']} ans")
    pdf.drawString(2*cm, hauteur - 10*cm, f"Départ prévu : {donnees['age_retraite']} ans")


# ---------------------------------------------------------------
# PAGE 2 — Résultats AVS
# ---------------------------------------------------------------
def page_avs(pdf, donnees, resultat):

    largeur, hauteur = A4

    titre(pdf, "Analyse de la rente AVS", hauteur - 2*cm)

    sous_titre(pdf, "Rappel des paramètres", hauteur - 4*cm)
    block_info(pdf, "Salaire moyen AVS (RAMD) :", f"CHF {donnees['salaire_moyen_avs']:,}".replace(",", "'"), hauteur - 5*cm)
    block_info(pdf, "Années cotisées AVS :", donnees["annees_avs"], hauteur - 6*cm)
    block_info(pdf, "Statut civil :", donnees["statut_civil"], hauteur - 7*cm)

    sous_titre(pdf, "Résultat AVS", hauteur - 9*cm)
    block_info(pdf, "Rente AVS annuelle :", f"CHF {resultat['rente_avs']:,}".replace(",", "'"), hauteur - 10*cm)


# ---------------------------------------------------------------
# PAGE 3 — Résultats LPP
# ---------------------------------------------------------------
def page_lpp(pdf, donnees, resultat):

    largeur, hauteur = A4

    titre(pdf, "Analyse du 2ème pilier (LPP)", hauteur - 2*cm)

    sous_titre(pdf, "Paramètres", hauteur - 4*cm)
    block_info(pdf, "Capital LPP :", f"CHF {donnees['capital_lpp']:,}".replace(",", "'"), hauteur - 5*cm)
    block_info(pdf, "Âge de retraite :", donnees["age_retraite"], hauteur - 6*cm)

    sous_titre(pdf, "Résultat LPP", hauteur - 8*cm)
    block_info(pdf, "Rente annuelle LPP :", f"CHF {resultat['rente_lpp']:,}".replace(",", "'"), hauteur - 9*cm)


# ---------------------------------------------------------------
# PAGE 4 — Synthèse finale
# ---------------------------------------------------------------
def page_synthese(pdf, donnees, resultat):

    largeur, hauteur = A4

    titre(pdf, "Synthèse finale", hauteur - 2*cm)

    sous_titre(pdf, "Résumé des prestations", hauteur - 4*cm)

    block_info(pdf, "Rente AVS :", f"CHF {resultat['rente_avs']:,}".replace(",", "'"), hauteur - 5*cm)
    block_info(pdf, "Rente LPP :", f"CHF {resultat['rente_lpp']:,}".replace(",", "'"), hauteur - 6*cm)
    block_info(pdf, "Rente conjoint :", f"CHF {resultat['rente_conjoint']:,}".replace(",", "'"), hauteur - 7*cm)

    pdf.setFont("Helvetica-Bold", 14)
    pdf.setFillColor(colors.HexColor("#1A75E8"))
    pdf.drawString(2*cm, hauteur - 9*cm, f"→ Total annuel : CHF {resultat['total_retraite']:,}".replace(",", "'"))


# ---------------------------------------------------------------
# FONCTION PRINCIPALE
# ---------------------------------------------------------------
def generer_pdf_estimation(donnees, resultat, output_path="estimation_retraite.pdf"):

    pdf = canvas.Canvas(output_path, pagesize=A4)

    # — Page 1 : Couverture —
    page_couverture(pdf, donnees)
    pdf.showPage()

    # — Page 2 : AVS —
    page_avs(pdf, donnees, resultat)
    pdf.showPage()

    # — Page 3 : LPP —
    page_lpp(pdf, donnees, resultat)
    pdf.showPage()

    # — Page 4 : Synthèse —
    page_synthese(pdf, donnees, resultat)
    pdf.showPage()

    pdf.save()
    return output_path
