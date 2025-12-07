import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import matplotlib.pyplot as plt

# =============================
#     COULEURS MRS
# =============================

PRIMARY = colors.HexColor("#D61D1D")
PRIMARY_DARK = colors.HexColor("#9A0000")
BLACK = colors.HexColor("#1D1D1F")
GREY = colors.HexColor("#F5F5F7")
WHITE = colors.white

# =============================
#    STYLE GLOBAL DU PDF
# =============================
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    name="TitleStyle",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=20,
    leading=24,
    textColor=PRIMARY,
    spaceAfter=16,
)

section_title_style = ParagraphStyle(
    name="SectionTitleStyle",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=16,
    leading=18,
    textColor=BLACK,
    spaceBefore=18,
    spaceAfter=8,
)

text_style = ParagraphStyle(
    name="TextStyle",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=11,
    leading=14,
    textColor=BLACK,
)

# =============================
#   TABLEAU PREMIUM
# =============================

def build_table(data, col_widths=None):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    return t

# =============================
#  GRAPHIQUE PREMIUM MATPLOTLIB
# =============================

def create_graph(avs, lpp, total):
    plt.figure(figsize=(5, 3))

    bars = ["AVS", "LPP", "Total"]
    values = [avs, lpp, total]
    colors_mrs = ["#D61D1D", "#1D1D1F", "#9A0000"]

    plt.bar(bars, values, color=colors_mrs)

    # Ajout des labels au-dessus
    for i, val in enumerate(values):
        plt.text(i, val + val * 0.03, f"{val:,.0f} CHF", 
                 ha='center', fontsize=10, fontweight='bold')

    plt.title("Rentes annuelles projetées", fontsize=14, fontweight="bold")
    plt.ylabel("Montants en CHF")
    plt.grid(axis="y", linestyle="--", alpha=0.3)

    graph_path = "graph_temp.png"
    plt.savefig(graph_path, dpi=200, bbox_inches="tight")
    plt.close()
    return graph_path

# =============================
#   FONCTION PRINCIPALE
# =============================

def generer_pdf_estimation(donnees, resultats, output="estimation.pdf"):

    # === Données ===
    avs_annuel = resultats.get("rente_avs", 0)
    lpp_annuel = resultats.get("rente_lpp", 0)
    conjoint_annuel = resultats.get("rente_conjoint", 0)
    total_annuel = resultats.get("total_retraite", avs_annuel + lpp_annuel + conjoint_annuel)

    # Mensuel
    avs_mensuel = avs_annuel / 12
    lpp_mensuel = lpp_annuel / 12
    conjoint_mensuel = conjoint_annuel / 12
    total_mensuel = total_annuel / 12

    # === Création PDF ===
    c = canvas.Canvas(output, pagesize=A4)
    width, height = A4

    # =============================
    # HEADER AVEC LOGO
    # =============================

    try:
        logo = ImageReader("logo.png")
        c.drawImage(logo, 2*cm, height - 3.5*cm, width=4*cm, preserveAspectRatio=True)
    except:
        pass

    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 4.5*cm, "Estimation de votre retraite")

    c.setFont("Helvetica", 11)
    c.setFillColor(BLACK)
    c.drawString(2*cm, height - 5.2*cm, f"{donnees['prenom']} {donnees['nom']}")

    # =============================
    # PAGE 1 — RÉSUMÉ
    # =============================

    résumé = [
        ["Élément", "Annuel", "Mensuel"],
        ["Rente AVS", f"{avs_annuel:,.0f} CHF", f"{avs_mensuel:,.0f} CHF"],
        ["Rente LPP", f"{lpp_annuel:,.0f} CHF", f"{lpp_mensuel:,.0f} CHF"],
        ["Rente conjoint", f"{conjoint_annuel:,.0f} CHF", f"{conjoint_mensuel:,.0f} CHF"],
        ["TOTAL", f"{total_annuel:,.0f} CHF", f"{total_mensuel:,.0f} CHF"],
    ]

    table = build_table(résumé, col_widths=[6*cm, 4.5*cm, 4.5*cm])
    table.wrapOn(c, width, height)
    table.drawOn(c, 2*cm, height - 12*cm)

    c.showPage()

    # =============================
    # PAGE 2 — GRAPHIQUE
    # =============================

    graph_path = create_graph(avs_annuel, lpp_annuel, total_annuel)

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 2.5*cm, "Visualisation de votre retraite")

    try:
        c.drawImage(graph_path, 2*cm, height - 15*cm, width=14*cm)
    except:
        pass

    c.showPage()

    # =============================
    # PAGE 3 — CONSEILS PREMIUM
    # =============================

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 2.5*cm, "Recommandations Ma Retraite Suisse")

    texte = Paragraph(
        """
        <b>Votre sérénité financière est notre priorité.</b><br/><br/>

        Voici nos recommandations personnalisées :<br/><br/>

        • Optimiser votre 3ᵉ pilier pour augmenter votre revenu futur.<br/>
        • Vérifier vos cotisations AVS et LPP chaque année.<br/>
        • Évaluer différents scénarios de retraite (âge, capital, rente).<br/><br/>

        Nous restons à votre disposition pour un accompagnement complet et sans engagement.
        """,
        text_style
    )

    texte.wrapOn(c, width - 4*cm, height)
    texte.drawOn(c, 2*cm, height - 12*cm)

    c.showPage()
    c.save()

    # Nettoyage du graphique
    if os.path.exists("graph_temp.png"):
        os.remove("graph_temp.png")

    return output
