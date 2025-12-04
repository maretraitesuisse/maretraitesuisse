# ================================================================
#      PDF GENERATOR – STYLE PREMIUM ROUGE & GRIS
# ================================================================
# Produit un PDF multi-pages à partir des résultats du calcul :
# - Page 1 : Résumé visuel + identité client
# - Page 2 : Détails AVS
# - Page 3 : Détails LPP
# - Page 4 : Diagnostic ton B + contact
# ================================================================

from fpdf import FPDF
import os


class PDFRetraite(FPDF):
    def header(self):
        # Bandeau rouge
        self.set_fill_color(180, 0, 0)
        self.rect(0, 0, 210, 22, 'F')

        # Logo (à déposer dans /static/logo.png)
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 4, 22)

        # Titre
        self.set_xy(40, 6)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "Ma Retraite Suisse – Rapport Officiel", border=0, ln=1)

        # Ligne rouge/grise
        self.set_draw_color(180, 0, 0)
        self.set_line_width(0.7)
        self.line(10, 22, 200, 22)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")


def ligne_titre(pdf, titre):
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(180, 0, 0)
    pdf.ln(8)
    pdf.cell(0, 10, titre, ln=1)


def ligne_valeur(pdf, label, valeur):
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(0)
    pdf.multi_cell(0, 7, f"{label} : {valeur}")


# ---------------------------------------------------------------
# FONCTION DE GÉNÉRATION DU PDF
# ---------------------------------------------------------------
def generer_pdf(data, filename="rapport_retraite.pdf"):
    pdf = PDFRetraite()
    pdf.set_auto_page_break(auto=True, margin=15)

    # ---------------------------------------------------------------
    # PAGE 1 – Résumé
    # ---------------------------------------------------------------
    pdf.add_page()

    ligne_titre(pdf, "Résumé de votre prévoyance")
    pdf.ln(4)

    ligne_valeur(pdf, "Prénom", data["prenom"])
    ligne_valeur(pdf, "Nom", data["nom"])
    ligne_valeur(pdf, "Email", data["email"])

    pdf.ln(4)
    ligne_valeur(pdf, "Rente AVS estimée", f"{data['rente_avs']:,.2f} CHF / mois")
    ligne_valeur(pdf, "Rente LPP estimée", f"{data['rente_lpp']:,.2f} CHF / mois")
    ligne_valeur(pdf, "TOTAL AVS + LPP", f"{data['total_retraite']:,.2f} CHF / mois")

    pdf.ln(5)
    ligne_valeur(pdf, "RAMD estimé", f"{data['ramd']:,.2f} CHF")

    # ---------------------------------------------------------------
    # PAGE 2 – AVS
    # ---------------------------------------------------------------
    pdf.add_page()
    ligne_titre(pdf, "Analyse AVS – 1er Pilier")
    pdf.ln(4)

    ligne_valeur(pdf, "Rente AVS finale", f"{data['rente_avs']:,.2f} CHF / mois")
    ligne_valeur(pdf, "Bonifications (BE + BA)", "Automatiquement intégrées")
    ligne_valeur(pdf, "RAMD", f"{data['ramd']:,.2f} CHF")

    if data["rente_conjoint"] > 0:
        ligne_valeur(pdf, "Rente AVS conjoint (après plafonnement éventuel)",
                     f"{data['rente_conjoint']:,.2f} CHF / mois")

    # ---------------------------------------------------------------
    # PAGE 3 – LPP
    # ---------------------------------------------------------------
    pdf.add_page()
    ligne_titre(pdf, "Analyse LPP – 2e Pilier")

    ligne_valeur(pdf, "Capital LPP initial",
                 f"{data['capital_lpp_initial']:,.2f} CHF ({data['capital_lpp_source']})")

    ligne_valeur(pdf, "Capital LPP projeté à la retraite",
                 f"{data['capital_lpp_final']:,.2f} CHF")

    ligne_valeur(pdf, "Rente LPP projetée",
                 f"{data['rente_lpp']:,.2f} CHF / mois")

    # ---------------------------------------------------------------
    # PAGE 4 – Diagnostic
    # ---------------------------------------------------------------
    pdf.add_page()
    ligne_titre(pdf, "Diagnostic général – Ton professionnel & chaleureux")

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(0)

    for point in data["diagnostic"]:
        pdf.multi_cell(0, 7, f"• {point}")
        pdf.ln(2)

    # BLOC CONTACT
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(180, 0, 0)
    pdf.cell(0, 10, "Pour toute question :", ln=1)

    pdf.set_text_color(0)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, "Ma Retraite Suisse – Service Analyse", ln=1)
    pdf.cell(0, 6, "Email : theo.maretraitesuisse@gmail.com", ln=1)

    pdf.output(filename)

    return filename
