import os
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import matplotlib.pyplot as plt

# ==========================================
#        COULEURS MA RETRAITE SUISSE
# ==========================================

PRIMARY = colors.HexColor("#D61D1D")
PRIMARY_DARK = colors.HexColor("#9A0000")
BLACK = colors.HexColor("#1D1D1F")
GREY = colors.HexColor("#F5F5F7")
WHITE = colors.white

# ==========================================
#        STYLE GLOBAL PDF
# ==========================================

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    name="TitleStyle",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=22,
    leading=26,
    textColor=PRIMARY,
    spaceAfter=16
)

section_title_style = ParagraphStyle(
    name="SectionTitleStyle",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=16,
    leading=20,
    textColor=BLACK,
    spaceBefore=18,
    spaceAfter=8,
)

text_style = ParagraphStyle(
    name="TextStyle",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=11,
    leading=16,
    textColor=BLACK,
)

# ==========================================
#        TABLEAU PREMIUM
# ==========================================

def build_table(data, col_widths=None):
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), PRIMARY),
        ("TEXTCOLOR", (0,0), (-1,0), WHITE),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 12),
        ("ALIGN", (0,0), (-1,0), "CENTER"),

        ("BACKGROUND", (0,1), (-1,-1), WHITE),
        ("TEXTCOLOR", (0,1), (-1,-1), BLACK),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("FONTSIZE", (0,1), (-1,-1), 11),

        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BOTTOMPADDING", (0,0), (-1,0), 8)
    ]))
    return table

# ==========================================
#        GRAPHIQUE PREMIUM
# ==========================================

def create_graph(avs, lpp, total):
    plt.figure(figsize=(5.5, 3))

    bars = ["AVS", "LPP", "Total"]
    values = [avs, lpp, total]
    colors_mrs = ["#D61D1D", "#1D1D1F", "#9A0000"]

    plt.bar(bars, values, color=colors_mrs)

    for i, val in enumerate(values):
        plt.text(i, val + val * 0.02, f"{val:,.0f} CHF", 
                 ha='center', fontsize=10, fontweight='bold')

    plt.title("Rentes annuelles projetées", fontsize=14, fontweight="bold")
    plt.ylabel("Montants en CHF")
    plt.grid(axis="y", linestyle="--", alpha=0.3)

    graph_path = "graph_temp.png"
    plt.savefig(graph_path, dpi=200, bbox_inches="tight")
    plt.close()
    return graph_path

# ==========================================
#        FONCTION PRINCIPALE
# ==========================================

def generer_pdf_estimation(donnees, resultats, output=None):

    # Extraction valeurs
    avs_annuel = resultats.get("rente_avs", 0)
    lpp_annuel = resultats.get("rente_lpp", 0)
    conjoint_annuel = resultats.get("rente_conjoint", 0)
    total_annuel = resultats.get("total_retraite", avs_annuel + lpp_annuel + conjoint_annuel)

    # Mensuel
    avs_mensuel = avs_annuel / 12
    lpp_mensuel = lpp_annuel / 12
    conjoint_mensuel = conjoint_annuel / 12
    total_mensuel = total_annuel / 12

    # ==========================================
    # NOM DYNAMIQUE DU PDF
    # ==========================================

    nom = donnees.get("nom", "Client").upper()
    annee = datetime.datetime.now().year
    file_name = f"estimation_{nom}_{annee}.pdf".replace(" ", "_")

    if output is None:
        output = file_name

    c = canvas.Canvas(output, pagesize=A4)
    width, height = A4

    # ==========================================
    # PAGE 1 — TITRE + RÉSUMÉ
    # ==========================================

    try:
        logo = ImageReader("logo.png")
        c.drawImage(logo, 2*cm, height - 4*cm, width=4*cm, preserveAspectRatio=True)
    except:
        pass

    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 5.2*cm, "Estimation personnalisée de votre retraite")

    c.setFont("Helvetica", 12)
    c.setFillColor(BLACK)
    c.drawString(2*cm, height - 6.1*cm, f"Client : {donnees.get('prenom', '')} {donnees.get('nom', '')}")

    # Tableau résumé
    résumé = [
        ["Élément", "Annuel", "Mensuel"],
        ["Rente AVS", f"{avs_annuel:,.0f} CHF", f"{avs_mensuel:,.0f} CHF"],
        ["Rente LPP", f"{lpp_annuel:,.0f} CHF", f"{lpp_mensuel:,.0f} CHF"],
        ["Rente conjoint", f"{conjoint_annuel:,.0f} CHF", f"{conjoint_mensuel:,.0f} CHF"],
        ["TOTAL", f"{total_annuel:,.0f} CHF", f"{total_mensuel:,.0f} CHF"],
    ]

    table = build_table(résumé, col_widths=[6*cm, 4.5*cm, 4.5*cm])
    table.wrapOn(c, width, height)
    table.drawOn(c, 2*cm, height - 15*cm)

    # Encadré premium — résumé
    texte_intro = Paragraph(
        f"""
        <b>Votre situation en un coup d'œil :</b><br/><br/>
        • Votre revenu total projeté s’élève à <b>{total_annuel:,.0f} CHF/an</b>
          (<b>{total_mensuel:,.0f} CHF/mois</b>).<br/>
        • L’AVS représente <b>{(avs_annuel/total_annuel*100):.1f}%</b> de vos revenus.<br/>
        • Le 2ᵉ pilier représente <b>{(lpp_annuel/total_annuel*100):.1f}%</b> de vos revenus.<br/><br/>
        Cette première estimation vous offre une vision claire de vos droits actuels.
        """,
        text_style
    )

    texte_intro.wrapOn(c, width - 4*cm, height)
    texte_intro.drawOn(c, 2*cm, height - 20*cm)

    c.showPage()

    # ==========================================
    # PAGE 2 — GRAPHIQUE + ANALYSE
    # ==========================================

    graph_path = create_graph(avs_annuel, lpp_annuel, total_annuel)

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 2.5*cm, "Analyse de votre situation")

    try:
        c.drawImage(graph_path, 2*cm, height - 14.5*cm, width=14*cm)
    except:
        pass

    # Analyse dynamique
    texte_analyse = Paragraph(
        f"""
        <b>Points clés :</b><br/><br/>

        • Votre revenu futur repose majoritairement sur 
          {"l’AVS" if avs_annuel > lpp_annuel else "le 2ᵉ pilier"}.<br/>
        • Votre niveau de rente est évalué à <b>{total_mensuel:,.0f} CHF/mois</b>,
          ce qui est {"inférieur" if total_mensuel < 3000 else "cohérent"} au maintien du niveau de vie moyen en Suisse.<br/>
        • Une optimisation du 3ᵉ pilier pourrait améliorer significativement votre stabilité financière à long terme.<br/><br/>

        Cette analyse met en lumière les axes prioritaires pour sécuriser votre retraite.
        """,
        text_style
    )

    texte_analyse.wrapOn(c, width - 4*cm, height)
    texte_analyse.drawOn(c, 2*cm, height - 18*cm)

    c.showPage()

    # ==========================================
    # PAGE 3 — RECOMMANDATIONS PREMIUM
    # ==========================================

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 2.5*cm, "Recommandations Ma Retraite Suisse")

    texte_reco = Paragraph(
        """
        <b>Nos recommandations prioritaires :</b><br/><br/>

        • Optimiser votre 3ᵉ pilier afin d’augmenter votre rente future.<br/>
        • Consolider votre 2ᵉ pilier avec un rachat partiel si éligible.<br/>
        • Comparer différents scénarios de retraite (âge légal, anticipation, capital vs rente).<br/>
        • Réévaluer votre planification tous les 12 mois pour suivre l’évolution de votre situation.<br/><br/>

        <b>Conclusion :</b><br/>
        Ma Retraite Suisse vous accompagne dans une stratégie personnalisée, 
        adaptée à vos besoins et à vos objectifs. 
        Un conseiller peut vous contacter pour approfondir cette analyse et optimiser votre planning.
        """,
        text_style
    )

    texte_reco.wrapOn(c, width - 4*cm, height)
    texte_reco.drawOn(c, 2*cm, height - 18*cm)

    c.showPage()

    # FIN
    c.save()

    # Nettoyage
    if os.path.exists("graph_temp.png"):
        os.remove("graph_temp.png")

    return output
