from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from datetime import datetime

# ===============================
#   PALETTE DE COULEURS MRS
# ===============================
ROUGE = HexColor("#D61D1D")
ROUGE_FONCE = HexColor("#9A0000")
GRIS_CLAIR = HexColor("#F5F5F7")
NOIR = HexColor("#1D1D1F")

# ===============================
#   UTILITAIRES DE STYLE
# ===============================

def draw_title(c, text, y):
    """Titre section premium + barre rouge"""
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(NOIR)
    c.drawString(2*cm, y, text)

    # Barre rouge
    c.setFillColor(ROUGE)
    c.rect(2*cm, y - 6, 55, 3, fill=1, stroke=0)


def draw_card(c, x, y, w, h):
    """Bloc blanc arrondi style premium"""
    c.setFillColor(HexColor("#FFFFFF"))
    c.roundRect(x, y - h, w, h, 16, fill=1, stroke=0)


def txt(c, x, y, text, size=12, bold=False, color=NOIR):
    """Texte normal / bold"""
    c.setFillColor(color)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.drawString(x, y, text)


def wrap_text(c, x, y, text, size=12, max_width=500):
    """Texte multilignes"""
    c.setFillColor(NOIR)
    c.setFont("Helvetica", size)
    for line in split_text(text, max_width, c, size):
        c.drawString(x, y, line)
        y -= size + 3


def split_text(text, max_width, c, size):
    """Coupe les lignes trop longues proprement"""
    words = text.split()
    lines, line = [], ""

    for w in words:
        if c.stringWidth(line + " " + w, "Helvetica", size) < max_width:
            line += " " + w
        else:
            lines.append(line.strip())
            line = w
    lines.append(line.strip())
    return lines


# ===============================
#   GÉNERATION PDF ULTRA-PRO
# ===============================
def generer_pdf_estimation(donnees, resultats):

    filename = f"estimation_{donnees['nom']}_{donnees['prenom']}.pdf"

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # ----------------------------------------------------------
    #   PAGE 1 — COUVERTURE PRO
    # ----------------------------------------------------------
    c.setFillColor(GRIS_CLAIR)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Logo centré
    try:
        logo = ImageReader("logo.png")
        c.drawImage(
            logo,
            width/2 - 3*cm,
            height - 10*cm,
            width=6*cm,
            preserveAspectRatio=True,
            mask="auto"
        )
    except:
        pass

    # Titre
    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width/2, height - 12.5*cm, "Estimation Personnalisée de Retraite")

    # Sous-titre
    c.setFont("Helvetica", 16)
    c.drawCentredString(width/2, height - 14*cm, f"{donnees['prenom']} {donnees['nom']}")
    c.drawCentredString(width/2, height - 15*cm, f"Rapport du {datetime.now().strftime('%d.%m.%Y')}")

    c.showPage()

    # ----------------------------------------------------------
    #   PAGE 2 — SYNTHÈSE PREMIUM
    # ----------------------------------------------------------
    draw_title(c, "Synthèse des Résultats", height - 3*cm)

    card_y = height - 5*cm
    draw_card(c, 2*cm, card_y, width - 4*cm, 11*cm)

    synth = [
        ("Rente AVS estimée :", f"{resultats['avs_mensuel']:.0f} CHF / mois"),
        ("Rente LPP estimée :", f"{resultats['lpp_mensuelle']:.0f} CHF / mois"),
        ("Total estimé :", f"{resultats['total_rente']:.0f} CHF / mois"),
        ("Taux de remplacement :", f"{resultats['taux_remplacement']:.1f} %"),
    ]

    y = card_y - 2*cm
    for label, val in synth:
        txt(c, 3*cm, y, label, bold=True)
        txt(c, 10*cm, y, val, bold=False, color=ROUGE)
        y -= 1.3*cm

    # Analyse automatique premium
    analyse = (
        "Votre situation semble stable et permet de maintenir un niveau de vie satisfaisant."
        if resultats["taux_remplacement"] >= 60
        else "Votre revenu de retraite présente un risque de baisse notable ; une optimisation est recommandée."
    )

    wrap_text(c, 3*cm, y, analyse, size=12)

    c.showPage()

    # ----------------------------------------------------------
    #   PAGE 3 — AVS & LPP
    # ----------------------------------------------------------
    draw_title(c, "Détails AVS", height - 3*cm)

    y = height - 5*cm
    avs = [
        ("Salaire moyen AVS :", f"{donnees['salaire_moyen_avs']} CHF"),
        ("Années cotisées :", f"{donnees['annees_avs']} ans"),
        ("Années manquantes :", f"{resultats['avs_manquantes']} ans"),
    ]

    for label, val in avs:
        txt(c, 2.5*cm, y, label, bold=True)
        txt(c, 10*cm, y, val)
        y -= 1.2*cm

    # LPP
    draw_title(c, "Détails LPP", y - 1*cm)
    y -= 3*cm

    lpp = [
        ("Capital LPP actuel :", f"{donnees['capital_lpp']} CHF"),
        ("Taux de conversion :", f"{resultats['taux_conversion']} %"),
        ("Rente LPP mensuelle :", f"{resultats['lpp_mensuelle']:.0f} CHF"),
    ]

    for label, val in lpp:
        txt(c, 2.5*cm, y, label, bold=True)
        txt(c, 10*cm, y, val)
        y -= 1.2*cm

    c.showPage()

    # ----------------------------------------------------------
    #   PAGE 4 — RECOMMANDATIONS CLAIRES & PROS
    # ----------------------------------------------------------
    draw_title(c, "Recommandations Personnalisées", height - 3*cm)

    recommandations = [
        "Optimiser la fiscalité en renforçant votre pilier 3a.",
        "Étudier les opportunités de rachat AVS ou LPP selon votre situation.",
        "Analyser votre futur niveau de vie et ajuster votre stratégie d’épargne.",
        "Adapter votre planification en fonction des règles de votre canton.",
    ]

    y = height - 5*cm
    for r in recommandations:
        wrap_text(c, 2.5*cm, y, f"• {r}", size=12)
        y -= 1.7*cm

    c.showPage()

    # Finalisation
    c.save()

    return filename
