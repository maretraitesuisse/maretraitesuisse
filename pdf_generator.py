# pdf_generator.py
# ===============================================================
# Génération du PDF estimation retraite complète AVS + LPP
# ===============================================================

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

def generer_pdf_estimation(donnees, resultat, output_path="estimation_retraite.pdf"):
    """
    Génère le PDF complet : AVS + LPP + total
    """

    pdf = canvas.Canvas(output_path, pagesize=A4)
    largeur, hauteur = A4

    # ------------------------------------------------------------
    # TITRE
    # ------------------------------------------------------------
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, hauteur - 60, "Estimation retraite complète")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, hauteur - 85, f"Émis le : {datetime.now().strftime('%d.%m.%Y')}")

    # ------------------------------------------------------------
    # IDENTITÉ
    # ------------------------------------------------------------
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, hauteur - 140, "Informations personnelles")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(60, hauteur - 165, f"Nom : {donnees['nom']}")
    pdf.drawString(60, hauteur - 185, f"Prénom : {donnees['prenom']}")
    pdf.drawString(60, hauteur - 205, f"Âge actuel : {donnees['age_actuel']} ans")
    pdf.drawString(60, hauteur - 225, f"Âge de retraite : {donnees['age_retraite']} ans")

    # ------------------------------------------------------------
    # RÉSULTATS AVS
    # ------------------------------------------------------------
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, hauteur - 270, "Rente AVS")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(60, hauteur - 295, f"Rente AVS mensuelle : CHF {resultat['rente_avs']:,}".replace(",", "'"))

    # ------------------------------------------------------------
    # RÉSULTATS LPP
    # ------------------------------------------------------------
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, hauteur - 340, "Rente LPP")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(60, hauteur - 365, f"Rente LPP annuelle : CHF {resultat['rente_lpp']:,}".replace(",", "'"))

    # ------------------------------------------------------------
    # TOTAL
    # ------------------------------------------------------------
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, hauteur - 410, "Total des rentes")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(60, hauteur - 435, f"Total annuel : CHF {resultat['total_retraite']:,}".replace(",", "'"))

    # ------------------------------------------------------------
    # FIN
    # ------------------------------------------------------------
    pdf.showPage()
    pdf.save()

    return output_path
