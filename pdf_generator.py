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
DARK_GREY = colors.HexColor("#4A4A4A")
WHITE = colors.white

styles = getSampleStyleSheet()

paragraph = ParagraphStyle(
    "paragraph",
    fontName="Helvetica",
    fontSize=11,
    leading=16,
    textColor=BLACK,
)

title_style = ParagraphStyle(
    "title",
    fontName="Helvetica-Bold",
    fontSize=26,
    leading=30,
    textColor=WHITE,
    alignment=1
)


# ==========================================
#        GRAPHIQUE PREMIUM
# ==========================================

def create_graph(avs, lpp, total):
    plt.figure(figsize=(6, 3))

    bars = ["AVS", "LPP", "Total"]
    values = [avs, lpp, total]
    colors_mrs = ["#D61D1D", "#1D1D1F", "#9A0000"]

    plt.bar(bars, values, color=colors_mrs, width=0.55)

    for i, val in enumerate(values):
        plt.text(i, val + val * 0.02, f"{val:,.0f} CHF",
                 ha='center', fontsize=10, fontweight='bold')

    plt.title("Projection annuelle des rentes", fontsize=14, fontweight="bold")
    plt.ylabel("Montants (CHF)")
    plt.grid(axis="y", linestyle="--", alpha=0.35)

    graph_path = "graph_temp.png"
    plt.savefig(graph_path, dpi=240, bbox_inches="tight")
    plt.close()
    return graph_path


# ==========================================
#        TABLEAU PREMIUM
# ==========================================

def build_table(data, col_widths=None):
    table = Table(data, colWidths=col_widths)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),

        ("BACKGROUND", (0, 1), (-1, -1), WHITE),
        ("TEXTCOLOR", (0, 1), (-1, -1), BLACK),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),

        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


# ==========================================
#        PAGE 1 — COUVERTURE PREMIUM
# ==========================================

def draw_cover_page(c, width, height):
    # ---- Bandeau diagonal premium compatible Render ----
    path = c.beginPath()
    path.moveTo(0, height)
    path.lineTo(width, height - 4*cm)
    path.lineTo(width, height)
    path.lineTo(0, height)
    path.close()

    c.setFillColor(PRIMARY)
    c.drawPath(path, fill=1, stroke=0)

    # ---- Logo ----
    try:
        logo = ImageReader("logo.png")
        c.drawImage(logo, 1.5*cm, height - 3.8*cm, width=4.2*cm, preserveAspectRatio=True)
    except:
        pass

    # ---- Titre premium ----
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(WHITE)
    c.drawCentredString(width/2, height - 7*cm, "Analyse personnalisée")

    # ---- Sous-titre ----
    c.setFont("Helvetica", 14)
    c.setFillColor(WHITE)
    c.drawCentredString(width/2, height - 8.3*cm, "AVS · LPP · 3ᵉ pilier · Projection financière")

    # ---- Bande graphique bas ----
    c.setFillColor(PRIMARY)
    c.rect(0, 0, width, 1.2*cm, fill=True, stroke=False)

    c.setFillColor(PRIMARY_DARK)
    c.rect(0, 1.2*cm, width, 0.4*cm, fill=True, stroke=False)

    c.showPage()


# ==========================================
#        FONCTION PRINCIPALE
# ==========================================

def generer_pdf_estimation(donnees, resultats, output=None):

    # === Valeurs retraite ===
    avs_annuel = resultats.get("rente_avs", 0)
    lpp_annuel = resultats.get("rente_lpp", 0)
    conjoint_annuel = resultats.get("rente_conjoint", 0)
    total_annuel = resultats.get("total_retraite", avs_annuel + lpp_annuel + conjoint_annuel)

    avs_mensuel = avs_annuel / 12
    lpp_mensuel = lpp_annuel / 12
    conjoint_mensuel = conjoint_annuel / 12
    total_mensuel = total_annuel / 12

    # === Nom dynamique du fichier ===
    nom = donnees.get("nom", "Client").upper()
    annee = datetime.datetime.now().year
    filename = f"estimation_{nom}_{annee}.pdf".replace(" ", "_")

    if output is None:
        output = filename

    c = canvas.Canvas(output, pagesize=A4)
    width, height = A4

    # ----------------------------------
    # PAGE 1 — Couverture premium
    # ----------------------------------
    draw_cover_page(c, width, height)

    # ----------------------------------
    # PAGE 2 — Résumé + Tableau
    # ----------------------------------

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 2.5*cm, "Résumé de votre situation")

    résumé = [
        ["Élément", "Annuel", "Mensuel"],
        ["Rente AVS", f"{avs_annuel:,.0f} CHF", f"{avs_mensuel:,.0f} CHF"],
        ["Rente LPP", f"{lpp_annuel:,.0f} CHF", f"{lpp_mensuel:,.0f} CHF"],
        ["Rente conjoint", f"{conjoint_annuel:,.0f} CHF", f"{conjoint_mensuel:,.0f} CHF"],
        ["TOTAL", f"{total_annuel:,.0f} CHF", f"{total_mensuel:,.0f} CHF"],
    ]

    table = build_table(résumé, col_widths=[6*cm, 4.5*cm, 4.5*cm])
    table.wrapOn(c, width, height)
    table.drawOn(c, 2*cm, height - 14*cm)

    intro = Paragraph(
        f"""
        <b>Votre situation :</b><br/><br/>
        • Votre revenu total projeté est de <b>{total_annuel:,.0f} CHF/an</b>
          (<b>{total_mensuel:,.0f} CHF/mois</b>).<br/>
        • Répartition : AVS <b>{(avs_annuel/total_annuel*100):.1f}%</b> —
          LPP <b>{(lpp_annuel/total_annuel*100):.1f}%</b>.<br/><br/>
        Cette estimation vous offre une vision claire et structurée de vos droits actuels.
        """,
        paragraph
    )

    intro.wrapOn(c, width - 4*cm, height)
    intro.drawOn(c, 2*cm, height - 18.5*cm)

    c.showPage()

    # ----------------------------------
    # PAGE 3 — Graphique + Analyse
    # ----------------------------------

    graph_path = create_graph(avs_annuel, lpp_annuel, total_annuel)

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 2.5*cm, "Analyse de vos rentes")

    try:
        c.drawImage(graph_path, 2*cm, height - 15*cm, width=14*cm, preserveAspectRatio=True)
    except:
        pass

    analyse = Paragraph(
        f"""
        <b>Interprétation :</b><br/><br/>
        • Votre revenu futur repose principalement sur 
          {"l’AVS" if avs_annuel > lpp_annuel else "le 2ᵉ pilier"}.<br/>
        • Votre niveau de rente est de <b>{total_mensuel:,.0f} CHF/mois</b>,
          ce qui est {"inférieur" if total_mensuel < 3200 else "cohérent"} avec le niveau de vie moyen en Suisse.<br/>
        • Une optimisation du 3ᵉ pilier renforcerait votre stabilité financière à long terme.<br/><br/>
        """,
        paragraph
    )

    analyse.wrapOn(c, width - 4*cm, height)
    analyse.drawOn(c, 2*cm, height - 18*cm)

    c.showPage()

    # ----------------------------------
    # PAGE 4 — Recommandations
    # ----------------------------------

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 2.5*cm, "Recommandations professionnelles")

    reco = Paragraph(
        """
        <b>Nos recommandations :</b><br/><br/>

        • Optimiser votre 3ᵉ pilier (A/B) pour augmenter votre rente future.<br/>
        • Envisager un rachat LPP si votre situation le permet.<br/>
        • Ajuster votre stratégie selon vos besoins (anticipation, capital ou rente).<br/>
        • Réévaluer votre planification chaque année pour intégrer vos évolutions.<br/><br/>

        <b>Conclusion :</b><br/>
        Ma Retraite Suisse reste à votre disposition pour un accompagnement personnalisé,
        sans engagement, afin d'améliorer et sécuriser votre situation financière future.
        """,
        paragraph
    )

    reco.wrapOn(c, width - 4*cm, height)
    reco.drawOn(c, 2*cm, height - 18*cm)

    c.showPage()

    # ----------------------------------
    # FIN & CLEAN
    # ----------------------------------

    c.save()

    if os.path.exists("graph_temp.png"):
        os.remove("graph_temp.png")

    return output
