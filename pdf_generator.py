import os
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
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
WHITE = colors.white

styles = getSampleStyleSheet()

text_style = ParagraphStyle(
    "Body",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=11,
    leading=16,
    textColor=BLACK
)

title_style = ParagraphStyle(
    "Title",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=20,
    leading=24,
    textColor=PRIMARY,
)


# =============================
#  GRAPHIQUE PREMIUM
# =============================

def create_graph(avs, lpp, total):
    plt.figure(figsize=(5.8, 3))

    bars = ["AVS", "LPP", "Total"]
    values = [avs, lpp, total]
    colors_mrs = ["#D61D1D", "#1D1D1F", "#9A0000"]

    plt.bar(bars, values, color=colors_mrs, width=0.55)

    for i, v in enumerate(values):
        plt.text(i, v + v * 0.02, f"{v:,.0f} CHF",
                 ha="center", fontsize=10, fontweight="bold")

    plt.title("Projection annuelle des rentes", fontsize=14, fontweight="bold")
    plt.ylabel("Montants (CHF)")
    plt.grid(axis="y", linestyle="--", alpha=0.35)

    path = "graph_temp.png"
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()
    return path


# =============================
#  TABLEAU
# =============================

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


# =============================
#  PAGE 1 : COUVERTURE PREMIUM
# =============================

def draw_cover_page(c, width, height):
    # ==== Bande diagonale ====
    path = c.beginPath()
    path.moveTo(0, height)
    path.lineTo(width, height - 3 * cm)
    path.lineTo(width, height)
    path.lineTo(0, height)
    path.close()
    c.setFillColor(PRIMARY)
    c.drawPath(path, fill=1, stroke=0)

    # ==== Logo ====
    try:
        logo = ImageReader("logo.png")
        c.drawImage(
            logo,
            1.5 * cm,
            height - 5.2 * cm,
            width=4 * cm,
            preserveAspectRatio=True,
            mask='auto'
        )
    except:
        pass

    # ==== TITRE ====
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(BLACK)
    c.drawString(1.5 * cm, height - 8.5 * cm,
                 "Étude de prévoyance – Ma Retraite Suisse")

    # ==== Sous-titre ====
    c.setFont("Helvetica", 15)
    c.setFillColor(BLACK)
    c.drawString(1.5 * cm, height - 10 * cm,
                 "AVS · LPP · 3e pilier · Projection financière")

    # ==== Année ====
    annee = datetime.datetime.now().year
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(1.5 * cm, height - 11.5 * cm,
                 f"Rapport {annee}")

    # ==== Bannière consulting ====
    try:
        banner = ImageReader("ban.jpg")
        banner_height = height * 0.33  # 33% = bon équilibre

        c.drawImage(
            banner,
            0,
            0,
            width=width,
            height=banner_height,
            preserveAspectRatio=True,
            mask='auto'
        )

        # Overlay rouge léger sans alpha
        c.setFillColorRGB(0.8, 0.05, 0.05)
        c.rect(0, 0, width, banner_height, fill=True, stroke=False)

    except Exception as e:
        print("Erreur bannière:", e)

    c.showPage()

# =============================
#  FONCTION PRINCIPALE
# =============================

def generer_pdf_estimation(donnees, resultats, output=None):
    # === Données ===
    avs_annuel = resultats.get("rente_avs", 0)
    lpp_annuel = resultats.get("rente_lpp", 0)
    conjoint_annuel = resultats.get("rente_conjoint", 0)
    total_annuel = resultats.get("total_retraite", avs_annuel + lpp_annuel + conjoint_annuel)

    avs_mensuel = avs_annuel / 12
    lpp_mensuel = lpp_annuel / 12
    conjoint_mensuel = conjoint_annuel / 12
    total_mensuel = total_annuel / 12

    # === Nom dynamique ===
    nom = donnees.get("nom", "Client").upper()
    annee = datetime.datetime.now().year

    if output is None:
        output = f"estimation_{nom}_{annee}.pdf".replace(" ", "_")

    c = canvas.Canvas(output, pagesize=A4)
    width, height = A4

    # -------------------------
    # PAGE 1 : COUVERTURE
    # -------------------------
    draw_cover_page(c, width, height)

    # -------------------------
    # PAGE 2 : RÉSUMÉ
    # -------------------------

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2 * cm, height - 2.5 * cm, "Résumé de votre situation")

    résumé = [
        ["Élément", "Annuel", "Mensuel"],
        ["Rente AVS", f"{avs_annuel:,.0f} CHF", f"{avs_mensuel:,.0f} CHF"],
        ["Rente LPP", f"{lpp_annuel:,.0f} CHF", f"{lpp_mensuel:,.0f} CHF"],
        ["Rente conjoint", f"{conjoint_annuel:,.0f} CHF", f"{conjoint_mensuel:,.0f} CHF"],
        ["TOTAL", f"{total_annuel:,.0f} CHF", f"{total_mensuel:,.0f} CHF"],
    ]

    table = build_table(résumé, col_widths=[6 * cm, 4.5 * cm, 4.5 * cm])
    table.wrapOn(c, width, height)
    table.drawOn(c, 2 * cm, height - 14 * cm)

    intro = Paragraph(
        f"""
        <b>Analyse financière :</b><br/><br/>
        • Votre revenu estimé est de <b>{total_annuel:,.0f} CHF/an</b> 
          (<b>{total_mensuel:,.0f} CHF/mois</b>).<br/>
        • Répartition actuelle : AVS {avs_annuel / total_annuel * 100:.1f}% —
          LPP {lpp_annuel / total_annuel * 100:.1f}%.<br/><br/>
        """,
        text_style,
    )

    intro.wrapOn(c, width - 4 * cm, height)
    intro.drawOn(c, 2 * cm, height - 18.5 * cm)

    c.showPage()

    # -------------------------
    # PAGE 3 : GRAPHIQUE
    # -------------------------

    graph_path = create_graph(avs_annuel, lpp_annuel, total_annuel)

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2 * cm, height - 2.5 * cm, "Analyse visuelle")

    try:
        c.drawImage(graph_path,
                    2 * cm,
                    height - 16 * cm,
                    width=14 * cm,
                    preserveAspectRatio=True)
    except:
        pass

    analyse = Paragraph(
        f"""
        Votre situation montre une dépendance financière 
        <b>{'forte à l’AVS' if avs_annuel > lpp_annuel else 'forte au 2e pilier'}</b>.
        Une optimisation du 3e pilier améliorerait sensiblement votre stabilité future.
        """,
        text_style,
    )

    analyse.wrapOn(c, width - 4 * cm, height)
    analyse.drawOn(c, 2 * cm, height - 18 * cm)

    c.showPage()

    # -------------------------
    # PAGE 4 : RECOMMANDATIONS
    # -------------------------

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2 * cm, height - 2.5 * cm, "Recommandations professionnelles")

    reco = Paragraph(
        """
        <b>Nos recommandations :</b><br/><br/>
        • Renforcer votre 3e pilier (maximiser l’avantage fiscal).<br/>
        • Envisager un rachat LPP si vos capacités le permettent.<br/>
        • Optimiser la répartition capital/rente selon vos objectifs.<br/>
        • Réévaluer votre situation tous les 12 mois.<br/><br/>
        """,
        text_style,
    )

    reco.wrapOn(c, width - 4 * cm, height)
    reco.drawOn(c, 2 * cm, height - 17 * cm)

    c.showPage()
    c.save()

    if os.path.exists("graph_temp.png"):
        os.remove("graph_temp.png")

    return output
