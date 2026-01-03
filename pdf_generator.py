import os
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import matplotlib.pyplot as plt

# ===============================================================
# COULEURS & STYLES
# ===============================================================

PRIMARY = colors.HexColor("#2563eb")
BLACK = colors.HexColor("#111827")
GRAY = colors.HexColor("#6b7280")

styles = getSampleStyleSheet()

TITLE = ParagraphStyle(
    "Title",
    fontName="Helvetica-Bold",
    fontSize=20,
    leading=24,
    textColor=PRIMARY
)

TEXT = ParagraphStyle(
    "Text",
    fontName="Helvetica",
    fontSize=11,
    leading=15,
    textColor=BLACK
)

SMALL = ParagraphStyle(
    "Small",
    fontName="Helvetica",
    fontSize=9,
    leading=12,
    textColor=GRAY
)

# ===============================================================
# GRAPHIQUE CAPITAL LPP
# ===============================================================

def draw_capital_graph(capital_history):
    ages = [x["age"] for x in capital_history]
    capitals = [x["capital"] for x in capital_history]

    plt.figure(figsize=(6, 3))
    plt.plot(ages, capitals, linewidth=2)
    plt.fill_between(ages, capitals, alpha=0.15)
    plt.title("Évolution du capital LPP")
    plt.xlabel("Âge")
    plt.ylabel("CHF")
    plt.grid(alpha=0.3)

    path = "capital_lpp.png"
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()
    return path

# ===============================================================
# PAGES
# ===============================================================

def page_cover(c, donnees):
    width, height = A4

    prenom = donnees.get("prenom", "")
    nom = donnees.get("nom", "")
    canton = donnees.get("canton", "")
    annee = datetime.datetime.now().year

    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 4*cm, "Projection retraite complète")

    c.setFont("Helvetica", 16)
    c.setFillColor(BLACK)
    c.drawString(2*cm, height - 6*cm,
                 f"{annee} — {prenom} {nom} ({canton})")

    c.setFont("Helvetica", 10)
    c.setFillColor(GRAY)
    c.drawString(2*cm, 2*cm,
                 "Document confidentiel — Ma Retraite Suisse")

    c.showPage()


def page_synthese(c, pdf):
    width, height = A4
    s = pdf["synthese"]

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 2.5*cm, "Synthèse globale")

    c.setFont("Helvetica", 12)
    c.setFillColor(BLACK)

    c.drawString(2*cm, height - 5*cm,
                 f"Revenu total mensuel : {s['total_mensuel']:,.0f} CHF")

    c.drawString(2*cm, height - 6.5*cm,
                 f"AVS : {s['avs_mensuel']:,.0f} CHF ({s['part_avs_pct']} %)")

    c.drawString(2*cm, height - 8*cm,
                 f"LPP : {s['lpp_mensuel']:,.0f} CHF ({s['part_lpp_pct']} %)")

    c.showPage()


def page_avs(c, avs):
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 2.5*cm, "Détail AVS")

    c.setFont("Helvetica", 11)
    c.setFillColor(BLACK)

    y = height - 5*cm
    for label, value in [
        ("Années validées", avs["annees_validees"]),
        ("Années manquantes", avs["annees_manquantes"]),
        ("RAMD", f"{avs['ramd']:,.0f} CHF"),
        ("Rente complète", f"{avs['rente_complete']:,.0f} CHF"),
        ("Rente finale", f"{avs['rente_finale']:,.0f} CHF"),
        ("Impact", f"{avs['impact_pct']} %"),
    ]:
        c.drawString(2*cm, y, f"{label} : {value}")
        y -= 1.2*cm

    c.showPage()


def page_lpp(c, lpp):
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 2.5*cm, "Détail LPP")

    c.setFont("Helvetica", 11)
    c.setFillColor(BLACK)

    c.drawString(2*cm, height - 5*cm,
                 f"Capital projeté : {lpp['capital_final']:,.0f} CHF")

    c.drawString(2*cm, height - 6.5*cm,
                 f"Rente mensuelle : {lpp['rente_mensuelle']:,.0f} CHF")

    graph = draw_capital_graph(lpp["capital_history"])
    c.drawImage(graph, 2*cm, height - 15*cm, width=16*cm)

    c.showPage()

    if os.path.exists(graph):
        os.remove(graph)


def page_scenarios(c, s):
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(PRIMARY)
    c.drawString(2*cm, height - 2.5*cm, "Scénarios")

    c.setFont("Helvetica", 11)
    c.setFillColor(BLACK)

    c.drawString(2*cm, height - 5*cm,
                 "Sans rachat : situation actuelle projetée")

    c.drawString(2*cm, height - 7*cm,
                 "Avec rachat LPP : hypothèse indicative")

    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(GRAY)
    c.drawString(2*cm, 2*cm,
                 "Les montants exacts seront déterminés lors d’un entretien personnalisé.")

    c.showPage()

# ===============================================================
# GÉNÉRATEUR PRINCIPAL
# ===============================================================

def generer_pdf_retraite(donnees, resultats, output="projection_retraite.pdf"):

    pdf = resultats["pdf_data"]

    c = canvas.Canvas(output, pagesize=A4)

    page_cover(c, donnees)
    page_synthese(c, pdf)
    page_avs(c, pdf["avs_detail"])
    page_lpp(c, pdf["lpp_detail"])
    page_scenarios(c, pdf)

    c.save()
    return output
