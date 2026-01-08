# pdf_generator.py
import os
import datetime
import math
import base64

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ===============================================================
# THEME (plus "cabinet" que UI)
# ===============================================================

PRIMARY = colors.HexColor("#1F3C88")   # bleu plus pro
UI_BLUE = colors.HexColor("#2563EB")  # bleu UI si besoin
BLACK   = colors.HexColor("#111827")
GRAY    = colors.HexColor("#6b7280")
LIGHT   = colors.HexColor("#e5e7eb")
MUTED   = colors.HexColor("#f3f4f6")
WHITE   = colors.white
BG      = colors.HexColor("#F5F7FA")  # gris très clair (pro, imprimable)


SUCCESS_BG = colors.HexColor("#16a34a")
SUCCESS_TX = colors.white

WARN_BG = colors.HexColor("#FEF3C7")
WARN_TX = colors.HexColor("#92400E")
DANGER  = colors.HexColor("#dc2626")


# ===============================================================
# UTILS
# ===============================================================

def asset_path(*parts):
    """assets/... relative to this file."""
    return os.path.join(os.path.dirname(__file__), "assets", *parts)

def _to_float(x):
    """
    Convertit proprement vers float même si x contient:
    - espaces (ex: "1 887")
    - virgule décimale (ex: "12,5")
    - suffixe CHF/% (ex: "1 200 CHF")
    """
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)

    s = str(x).strip().lower()
    s = s.replace("chf", "").replace("%", "").strip()
    s = s.replace(" ", "")              # enlève séparateurs de milliers
    s = s.replace("\u00a0", "")         # espace insécable
    s = s.replace(",", ".")             # virgule -> point

    if s == "":
        return None

    try:
        return float(s)
    except Exception:
        return None

def fmt_int(n):
    v = _to_float(n)
    if v is None:
        return "—" if n is None else str(n)
    return f"{int(round(v)):,}".replace(",", " ")

def fmt_chf(n, decimals=0):
    v = _to_float(n)
    if v is None:
        return "—" if n is None else f"{n} CHF"

    if decimals == 0:
        return f"{int(round(v)):,}".replace(",", " ") + " CHF"
    return f"{v:,.{decimals}f}".replace(",", " ").replace(".", ",") + " CHF"

def fmt_pct(x, decimals=1):
    v = _to_float(x)
    if v is None:
        return "—" if x is None else f"{x} %"
    return f"{v:.{decimals}f} %".replace(".", ",")

def safe_get(d, path, default=None):
    """safe_get(d, ['a','b','c'])"""
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
    return cur if cur is not None else default


# ===============================================================
# DRAW PRIMITIVES (ReportLab)
# ===============================================================

def draw_shadow_card(c, x, y, w, h, r=12, fill=MUTED, stroke=LIGHT):
    """Simple shadow simulation: draw gray offset rect then main rect."""
    # shadow
    c.setFillColor(colors.HexColor("#d1d5db"))
    c.setStrokeColor(colors.HexColor("#d1d5db"))
    c.roundRect(x + 2, y - 2, w, h, r, stroke=0, fill=1)

    # main
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(1)
    c.roundRect(x, y, w, h, r, stroke=1, fill=1)

def draw_card(c, x, y, w, h, r=12, fill=WHITE, stroke=LIGHT):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(1)
    c.roundRect(x, y, w, h, r, stroke=1, fill=1)

def draw_h1(c, text, x, y, color=UI_BLUE):
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(color)
    c.drawString(x, y, text)

def draw_h2(c, text, x, y, color=BLACK):
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(color)
    c.drawString(x, y, text)

def draw_p(c, text, x, y, size=12, color=BLACK):
    c.setFont("Helvetica", size)
    c.setFillColor(color)
    c.drawString(x, y, text)

def draw_small(c, text, x, y, color=GRAY):
    c.setFont("Helvetica", 9.5)
    c.setFillColor(color)
    c.drawString(x, y, text)

def draw_top_confidential(c, width, height):
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, height - 1.2*cm, "Document confidentiel — Ma Retraite Suisse")

def draw_footer(c, width):
    year = datetime.datetime.now().year
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 9)
    c.drawCentredString(width/2, 1.2*cm, f"www.maretraitesuisse.ch — © {year} Ma Retraite Suisse")

def draw_divider(c, x1, y, x2, color=LIGHT):
    c.setStrokeColor(color)
    c.setLineWidth(1)
    c.line(x1, y, x2, y)
    
def draw_gradient_bar(c, x, y, w, h, left_hex="#2563EB", right_hex="#60A5FA", steps=60, radius=6):
    """
    Simule un dégradé horizontal en dessinant des petits rectangles.
    - x,y = bas gauche
    - w,h = largeur/hauteur
    """
    # arrondi "visuel" : on fait un clip simple avec roundRect en surcouche
    # 1) fond arrondi (transparent visuel)
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.white)
    c.roundRect(x, y, w, h, radius, stroke=0, fill=0)

    def hex_to_rgb(hx):
        hx = hx.lstrip("#")
        return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))

    r1, g1, b1 = hex_to_rgb(left_hex)
    r2, g2, b2 = hex_to_rgb(right_hex)

    step_w = w / steps
    for i in range(steps):
        t = i / max(steps - 1, 1)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        c.setFillColor(colors.Color(r/255, g/255, b/255))
        c.setStrokeColor(colors.Color(r/255, g/255, b/255))
        c.rect(x + i * step_w, y, step_w + 0.2, h, stroke=0, fill=1)



# ===============================================================
# CHARTS (Matplotlib -> PNG -> drawImage)
# ===============================================================

def draw_donut_chart(values, labels, out_path):
    """
    values: [avs, lpp]
    """
    plt.figure(figsize=(3.0, 3.0))
    plt.pie(
        values,
        labels=None,
        startangle=90,
        wedgeprops=dict(width=0.28),
    )
    # center circle look
    centre = plt.Circle((0, 0), 0.55, fc="white")
    plt.gca().add_artist(centre)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, transparent=True)
    plt.close()
    return out_path

def draw_capital_graph(capital_history, out_path):
    ages = []
    capitals = []
    for x in (capital_history or []):
        try:
            ages.append(float(x.get("age")))
            capitals.append(float(x.get("capital")))
        except Exception:
            pass

    if not ages or not capitals:
        # avoid crash; generate empty chart
        ages = [45, 50, 55, 60, 65]
        capitals = [0, 0, 0, 0, 0]

    plt.figure(figsize=(6.5, 3.2))
    # style close to UI screenshot
    plt.plot(ages, capitals, linewidth=4)
    plt.fill_between(ages, capitals, alpha=0.15)
    plt.grid(alpha=0.25)
    plt.xlabel("Âge", fontsize=14, labelpad=12)
    plt.ylabel("CHF", fontsize=14, labelpad=10)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return out_path


# ===============================================================
# P1 — COVER
# ===============================================================

def page_cover(c, donnees):
    width, height = A4

    prenom = (donnees.get("prenom") or "").strip()
    nom = (donnees.get("nom") or "").strip()
    age_actuel = donnees.get("age_actuel")
    age_retraite = donnees.get("age_retraite")

    today = datetime.datetime.now()
    date_str = today.strftime("%d/%m/%Y")
    year = today.year

    # =========================================================
    # FOND (non blanc)
    # =========================================================
    c.setFillColor(BG)
    c.rect(0, 0, width, height, stroke=0, fill=1)

    # =========================================================
    # HEADER demi-bannière + coupe diagonale (triangle)
    # =========================================================
    header_h = 4.2 * cm

    # grand bandeau bleu en haut avec diagonale (comme ton img2)
    c.setFillColor(PRIMARY)
    c.setStrokeColor(PRIMARY)
    c.setLineWidth(0)

    # Polygone : haut plein, bas coupé en diagonale
    # (gauche plus bas, droite plus haut) -> look "triangle"
    
    p = c.beginPath()
    p.moveTo(0, height)
    p.lineTo(width, height)
    p.lineTo(width, height - header_h)
    p.lineTo(0, height - header_h * 0.55)
    p.close()
    c.drawPath(p, stroke=0, fill=1)

    # petit filet clair sous le header (léger)
    c.setStrokeColor(LIGHT)
    c.setLineWidth(1)
    c.line(2.2*cm, height - header_h - 0.25*cm, width - 2.2*cm, height - header_h - 0.25*cm)

    # =========================================================
    # LOGO (centré, sur fond clair, sous le bandeau)
    # =========================================================
    logo_path = asset_path("logo.png")
    logo_y = height - header_h - 2.6*cm

    if os.path.exists(logo_path):
        img = ImageReader(logo_path)
        iw, ih = img.getSize()
        target_w = 6.5 * cm
        scale = target_w / float(iw)
        target_h = ih * scale
        c.drawImage(
            logo_path,
            (width - target_w) / 2,
            logo_y,
            width=target_w,
            height=target_h,
            mask="auto"
        )
        logo_block_h = target_h
    else:
        # fallback texte si logo absent
        c.setFillColor(PRIMARY)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width/2, logo_y + 0.8*cm, "MA RETRAITE SUISSE")
        logo_block_h = 1.2*cm

    # =========================================================
    # TITRE / SOUS-TITRE + TRAIT GRADIENT (comme page avis)
    # =========================================================
    title_y = logo_y - 2.0*cm

    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width/2, title_y, "PROJECTION RETRAITE CERTIFIÉE")

    c.setFillColor(BLACK)
    c.setFont("Helvetica", 13)
    c.drawCentredString(width/2, title_y - 1.0*cm, "Analyse personnalisée AVS & LPP")

    # trait gradient (petit, centré)
    bar_w = 4.6 * cm
    bar_h = 0.22 * cm
    bar_x = (width - bar_w) / 2
    bar_y = title_y - 1.75 * cm
    draw_gradient_bar(
        c,
        bar_x, bar_y,
        bar_w, bar_h,
        left_hex="#1F3C88",   # bleu pro
        right_hex="#60A5FA",  # bleu clair
        steps=70,
        radius=10
    )

    # =========================================================
    # CARTE CLIENT (blanche + ombre) comme tes cards UI (img3)
    # =========================================================
    card_w = width * 0.70
    card_h = 4.4 * cm
    card_x = (width - card_w) / 2
    card_y = bar_y - 5.2 * cm

    # ombre + carte
    draw_shadow_card(c, card_x, card_y, card_w, card_h, r=16, fill=WHITE, stroke=LIGHT)

    # contenu
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(card_x + 1.2*cm, card_y + card_h - 1.35*cm, f"Client : {prenom} {nom}".strip())

    c.setFont("Helvetica", 11)
    c.setFillColor(BLACK)
    if age_actuel is not None:
        c.drawString(card_x + 1.2*cm, card_y + card_h - 2.40*cm, f"Âge actuel : {age_actuel} ans")
    if age_retraite is not None:
        c.drawString(card_x + 1.2*cm, card_y + card_h - 3.25*cm, f"Départ prévu : {age_retraite} ans")

    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10)
    c.drawString(card_x + 1.2*cm, card_y + 0.95*cm, f"Rapport généré le : {date_str}")

    # =========================================================
    # BANDEAU BAS (fin, pas épais) + mentions
    # =========================================================
    footer_band_h = 0.55 * cm
    c.setFillColor(PRIMARY)
    c.rect(0, 0, width, footer_band_h, stroke=0, fill=1)

    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(
        width/2,
        footer_band_h + 0.95*cm,
        "Ce rapport fournit une estimation indicative basée sur les informations déclarées et ne constitue pas un conseil financier contractuel."
    )

    c.setFont("Helvetica", 9)
    c.drawCentredString(width/2, footer_band_h + 0.35*cm, f"www.maretraitesuisse.ch — © {year} Ma Retraite Suisse")

    c.showPage()



# ===============================================================
# P2 — SYNTHÈSE (style UI)
# ===============================================================

def page_synthese(c, pdf):
    width, height = A4
    s = pdf.get("synthese", {}) if isinstance(pdf, dict) else {}

    total_m = s.get("total_mensuel")
    avs_m = s.get("avs_mensuel")
    lpp_m = s.get("lpp_mensuel")
    part_avs = s.get("part_avs_pct")
    part_lpp = s.get("part_lpp_pct")

    draw_top_confidential(c, width, height)

    # Title
    draw_h1(c, "Synthèse globale", 2*cm, height - 4.2*cm, color=UI_BLUE)

    # Main blue card (total)
    card_x = 2*cm
    card_w = width - 4*cm
    card_y = height - 11.0*cm
    card_h = 3.4*cm

    draw_shadow_card(c, card_x, card_y, card_w, card_h, r=16, fill=UI_BLUE, stroke=UI_BLUE)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, card_y + card_h - 1.05*cm, "Votre revenu mensuel total à la retraite")

    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(width/2, card_y + 1.15*cm, f"{fmt_int(total_m)} CHF" if total_m is not None else "—")

    # Two cards AVS/LPP
    gap = 0.8*cm
    small_w = (card_w - gap) / 2
    small_h = 3.0*cm
    small_y = card_y - (small_h + 1.2*cm)

    # AVS card
    avs_x = card_x
    draw_shadow_card(c, avs_x, small_y, small_w, small_h, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(avs_x + 1.0*cm, small_y + small_h - 1.1*cm, "AVS (1er Pilier)")
    c.setFont("Helvetica-Bold", 20)
    c.drawString(avs_x + 1.0*cm, small_y + 1.2*cm, f"{fmt_int(avs_m)} CHF" if avs_m is not None else "—")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(avs_x + 1.0*cm, small_y + 0.6*cm, f"{fmt_pct(part_avs, 1)} de votre revenu" if part_avs is not None else "")

    # LPP card
    lpp_x = avs_x + small_w + gap
    draw_shadow_card(c, lpp_x, small_y, small_w, small_h, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(lpp_x + 1.0*cm, small_y + small_h - 1.1*cm, "LPP (2ème Pilier)")
    c.setFont("Helvetica-Bold", 20)
    c.drawString(lpp_x + 1.0*cm, small_y + 1.2*cm, f"{fmt_int(lpp_m)} CHF" if lpp_m is not None else "—")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(lpp_x + 1.0*cm, small_y + 0.6*cm, f"{fmt_pct(part_lpp, 1)} de votre revenu" if part_lpp is not None else "")

    # Donut section
    donut_y = small_y - 7.0*cm
    draw_card(c, card_x, donut_y, card_w, 6.0*cm, r=16, fill=WHITE, stroke=LIGHT)

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(card_x + 1.0*cm, donut_y + 6.0*cm - 1.1*cm, "Répartition de vos revenus")

    # donut image
    donut_path = "donut_tmp.png"
    try:
        v0 = _to_float(avs_m) or 0.0
        v1 = _to_float(lpp_m) or 0.0
        values = [v0, v1]
        if values[0] + values[1] <= 0:
            values = [1, 1]
        draw_donut_chart(values, ["AVS", "LPP"], donut_path)
        c.drawImage(donut_path, card_x + 6.0*cm, donut_y + 0.9*cm, width=6.0*cm, height=4.8*cm, mask="auto")
    finally:
        if os.path.exists(donut_path):
            os.remove(donut_path)

    # labels around
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(card_x + 1.0*cm, donut_y + 3.6*cm, f"AVS (1er pilier) : {fmt_pct(part_avs, 1)}" if part_avs is not None else "AVS (1er pilier)")
    c.drawString(card_x + 1.0*cm, donut_y + 2.4*cm, f"LPP (2ème pilier) : {fmt_pct(part_lpp, 1)}" if part_lpp is not None else "LPP (2ème pilier)")

    draw_footer(c, width)
    c.showPage()


# ===============================================================
# P3 — AVS DÉTAILLÉ
# ===============================================================

def page_avs(c, avs):
    width, height = A4

    draw_top_confidential(c, width, height)
    draw_h1(c, "Détail AVS", 2*cm, height - 4.2*cm, color=UI_BLUE)

    # Extract values
    annees_validees = avs.get("annees_validees")
    annees_manquantes = avs.get("annees_manquantes")
    ramd = avs.get("ramd")
    rente_complete = avs.get("rente_complete")
    rente_finale = avs.get("rente_finale")
    impact = avs.get("impact_pct")

    # Big grid cards (2 columns)
    card_x = 2*cm
    card_w = width - 4*cm
    y0 = height - 8.5*cm

    # Cards row 1
    gap = 0.8*cm
    w2 = (card_w - gap) / 2
    h2 = 3.0*cm

    # Années validées
    draw_shadow_card(c, card_x, y0, w2, h2, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(card_x + 1.0*cm, y0 + h2 - 1.1*cm, "Années validées")
    c.setFont("Helvetica-Bold", 20)
    c.drawString(card_x + 1.0*cm, y0 + 1.0*cm, f"{fmt_int(annees_validees)}" if annees_validees is not None else "—")

    # Années manquantes
    x2 = card_x + w2 + gap
    draw_shadow_card(c, x2, y0, w2, h2, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(x2 + 1.0*cm, y0 + h2 - 1.1*cm, "Années manquantes")
    c.setFont("Helvetica-Bold", 20)
    c.drawString(x2 + 1.0*cm, y0 + 1.0*cm, f"{fmt_int(annees_manquantes)}" if annees_manquantes is not None else "—")

    # Row 2 cards
    y1 = y0 - (h2 + 1.0*cm)

    # RAMD
    draw_shadow_card(c, card_x, y1, w2, h2, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(card_x + 1.0*cm, y1 + h2 - 1.1*cm, "RAMD")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(card_x + 1.0*cm, y1 + 1.0*cm, fmt_chf(ramd, 0) if ramd is not None else "—")

    # Réduction
    draw_shadow_card(c, x2, y1, w2, h2, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(x2 + 1.0*cm, y1 + h2 - 1.1*cm, "Réduction")
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(DANGER if impact is not None else BLACK)
    c.drawString(x2 + 1.0*cm, y1 + 1.0*cm, f"-{fmt_pct(impact, 1)}" if impact is not None else "—")

    # Detail box
    box_y = y1 - 7.2*cm
    draw_card(c, card_x, box_y, card_w, 6.4*cm, r=16, fill=WHITE, stroke=LIGHT)

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(card_x + 1.0*cm, box_y + 6.4*cm - 1.1*cm, "Détail du calcul")

    lines = [
        ("Rente pour carrière complète", fmt_chf(rente_complete, 0) if rente_complete is not None else "—"),
        ("Rente mensuelle finale", fmt_chf(rente_finale, 0) if rente_finale is not None else "—"),
    ]
    c.setFont("Helvetica", 11)
    c.setFillColor(BLACK)
    yy = box_y + 6.4*cm - 2.2*cm
    for label, val in lines:
        c.setFillColor(GRAY)
        c.drawString(card_x + 1.0*cm, yy, label)
        c.setFillColor(BLACK)
        c.drawRightString(card_x + card_w - 1.0*cm, yy, val)
        yy -= 1.1*cm

    # Warning box
    missing = _to_float(annees_manquantes) or 0.0
    if missing > 0:
        warn_y = box_y - 3.2*cm
        draw_card(c, card_x, warn_y, card_w, 2.6*cm, r=14, fill=WARN_BG, stroke=colors.HexColor("#FDE68A"))
        c.setFillColor(WARN_TX)
        c.setFont("Helvetica-Bold", 11.5)
        c.drawString(card_x + 1.0*cm, warn_y + 1.65*cm, f"{fmt_int(annees_manquantes)} années manquantes")
        c.setFont("Helvetica", 10.5)
        c.drawString(card_x + 1.0*cm, warn_y + 0.85*cm, f"Votre rente AVS est réduite de {fmt_pct(impact, 1) if impact is not None else '—'}.")

    draw_footer(c, width)
    c.showPage()


# ===============================================================
# P4 — LPP DÉTAILLÉ
# ===============================================================

def page_lpp(c, lpp):
    width, height = A4
    draw_top_confidential(c, width, height)
    draw_h1(c, "Détail LPP", 2*cm, height - 4.2*cm, color=UI_BLUE)

    capital_actuel = lpp.get("capital_actuel", 0)
    capital_final = lpp.get("capital_final")
    rente_mensuelle = lpp.get("rente_mensuelle")
    annees_restantes = lpp.get("annees_restantes")
    history = lpp.get("capital_history", [])

    card_x = 2*cm
    card_w = width - 4*cm
    gap = 0.8*cm
    w2 = (card_w - gap) / 2
    h2 = 3.0*cm

    y0 = height - 8.5*cm

    # Row 1 cards
    draw_shadow_card(c, card_x, y0, w2, h2, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(card_x + 1.0*cm, y0 + h2 - 1.1*cm, "Capital actuel")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(card_x + 1.0*cm, y0 + 1.0*cm, fmt_chf(capital_actuel, 0))

    x2 = card_x + w2 + gap
    draw_shadow_card(c, x2, y0, w2, h2, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(x2 + 1.0*cm, y0 + h2 - 1.1*cm, "Capital projeté")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x2 + 1.0*cm, y0 + 1.0*cm, fmt_chf(capital_final, 0) if capital_final is not None else "—")

    # Row 2 cards
    y1 = y0 - (h2 + 1.0*cm)
    draw_shadow_card(c, card_x, y1, w2, h2, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(card_x + 1.0*cm, y1 + h2 - 1.1*cm, "Rente mensuelle")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(card_x + 1.0*cm, y1 + 1.0*cm, fmt_chf(rente_mensuelle, 0) if rente_mensuelle is not None else "—")

    draw_shadow_card(c, x2, y1, w2, h2, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(x2 + 1.0*cm, y1 + h2 - 1.1*cm, "Années restantes")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x2 + 1.0*cm, y1 + 1.0*cm, f"{fmt_int(annees_restantes)} ans" if annees_restantes is not None else "—")

    # Graph card
    graph_y = y1 - 8.2*cm
    draw_card(c, card_x, graph_y, card_w, 7.4*cm, r=16, fill=WHITE, stroke=LIGHT)

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(card_x + 1.0*cm, graph_y + 7.4*cm - 1.1*cm, "Projection de votre capital")

    graph_path = "capital_lpp_tmp.png"
    try:
        draw_capital_graph(history, graph_path)
        c.drawImage(graph_path, card_x + 1.0*cm, graph_y + 1.0*cm, width=card_w - 2.0*cm, height=5.8*cm)
    finally:
        if os.path.exists(graph_path):
            os.remove(graph_path)

    draw_footer(c, width)
    c.showPage()


# ===============================================================
# P5 — SCÉNARIOS + CONCLUSION
# ===============================================================

def page_scenarios(c, pdf):
    width, height = A4
    draw_top_confidential(c, width, height)
    draw_h1(c, "Scénarios", 2*cm, height - 4.2*cm, color=UI_BLUE)

    # "scenarios" peut être dict OU list suivant tes versions de resultats["pdf_data"]
    scenarios = {}
    if isinstance(pdf, dict):
        raw = pdf.get("scenarios")
        if isinstance(raw, dict):
            scenarios = raw
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    k = item.get("key") or item.get("name") or item.get("type")
                    if k:
                        scenarios[str(k)] = item

    # Values (if present)
    sans = scenarios.get("sans_rachat") or scenarios.get("sans") or {}
    rachat = scenarios.get("rachat_lpp") or scenarios.get("rachat") or {}

    # Top explanatory text
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(
        2*cm,
        height - 5.4*cm,
        "Voici les scénarios d'optimisation possibles selon votre situation. Les calculs sont indicatifs et dépendent de votre situation fiscale exacte."
    )

    card_x = 2*cm
    card_w = width - 4*cm

    # Sans rachat card
    y0 = height - 9.8*cm
    draw_shadow_card(c, card_x, y0, card_w, 3.0*cm, r=16, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(card_x + 1.0*cm, y0 + 1.9*cm, "Sans rachat")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(card_x + 1.0*cm, y0 + 1.0*cm, "Situation actuelle projetée")

    sans_m = (sans.get("rente_mensuelle") if isinstance(sans, dict) else None) or safe_get(pdf, ["synthese", "total_mensuel"])
    c.setFillColor(colors.HexColor("#15803d"))
    c.setFont("Helvetica-Bold", 16)
    if sans_m is not None:
        c.drawRightString(card_x + card_w - 1.0*cm, y0 + 1.45*cm, f"{fmt_int(sans_m)} CHF")
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 9.5)
        c.drawRightString(card_x + card_w - 1.0*cm, y0 + 0.85*cm, "rente mensuelle")

    # Rachat LPP card (recommended)
    y1 = y0 - 4.2*cm
    draw_shadow_card(c, card_x, y1, card_w, 4.2*cm, r=16, fill=colors.HexColor("#ECFDF5"), stroke=colors.HexColor("#bbf7d0"))
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(card_x + 1.0*cm, y1 + 3.0*cm, "Rachat LPP optimisé")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(card_x + 1.0*cm, y1 + 2.2*cm, "Rachat étalé sur 5 ans  •  Recommandé")

    rachat_m = (rachat.get("rente_mensuelle") if isinstance(rachat, dict) else None)
    c.setFillColor(colors.HexColor("#15803d"))
    c.setFont("Helvetica-Bold", 16)
    if rachat_m is not None:
        c.drawRightString(card_x + card_w - 1.0*cm, y1 + 2.7*cm, f"{fmt_int(rachat_m)} CHF")
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 9.5)
        c.drawRightString(card_x + card_w - 1.0*cm, y1 + 2.1*cm, "rente mensuelle")

    # 4 metrics line
    def rget(key):
        return rachat.get(key) if isinstance(rachat, dict) else None

    metrics = [
        ("Coût total", rget("cout_total")),
        ("Économie impôt", rget("economie_impot")),
        ("Gain mensuel", rget("gain_mensuel")),
        ("Gain sur 20 ans", rget("gain_20_ans")),
    ]

    mx = card_x + 1.0*cm
    my = y1 + 1.1*cm
    col_w = (card_w - 2.0*cm) / 4

    for i, (lab, val) in enumerate(metrics):
        x = mx + i * col_w
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 9.5)
        c.drawString(x, my + 0.65*cm, lab)
        c.setFillColor(BLACK)
        c.setFont("Helvetica-Bold", 11.5)

        if val is None:
            c.drawString(x, my, "—")
            continue

        vv = _to_float(val)
        if vv is None:
            c.drawString(x, my, str(val))
            continue

        # couleurs selon type
        if "impôt" in lab.lower() and vv < 0:
            c.setFillColor(colors.HexColor("#15803d"))
        if "gain" in lab.lower() and vv > 0:
            c.setFillColor(colors.HexColor("#2563eb"))

        c.drawString(x, my, fmt_chf(vv, 0))

    # Next steps box
    y2 = y1 - 5.0*cm
    draw_card(c, card_x, y2, card_w, 3.8*cm, r=16, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(card_x + 1.0*cm, y2 + 2.7*cm, "Prochaines étapes")

    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(card_x + 1.0*cm, y2 + 1.9*cm,
                 "Pour mettre en place ces optimisations, vous devrez fournir vos documents")
    c.drawString(card_x + 1.0*cm, y2 + 1.3*cm,
                 "officiels (extrait de compte AVS, certificats LPP). Notre équipe vous")
    c.drawString(card_x + 1.0*cm, y2 + 0.7*cm,
                 "accompagne dans toutes les démarches. Un conseiller vous contactera sous 48h.")

    draw_footer(c, width)
    c.showPage()


# ===============================================================
# GÉNÉRATEUR PRINCIPAL (signature inchangée)
# ===============================================================

def generer_pdf_retraite(donnees, resultats, output="projection_retraite.pdf"):
    """
    Ne casse pas tes branchements.
    Attend resultats["pdf_data"] comme avant.
    """
    pdf = resultats.get("pdf_data", {}) if isinstance(resultats, dict) else {}

    c = canvas.Canvas(output, pagesize=A4)

    # P1
    page_cover(c, donnees)

    # P2
    page_synthese(c, pdf)

    # P3
    avs_detail = pdf.get("avs_detail", {})
    page_avs(c, avs_detail)

    # P4
    lpp_detail = pdf.get("lpp_detail", {})
    page_lpp(c, lpp_detail)

    # P5
    page_scenarios(c, pdf)

    c.save()
    return output
