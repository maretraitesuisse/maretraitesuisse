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
    
def draw_gradient_bar(c, x, y, w, h, center_hex="#2563EB", edge_hex="#93C5FD", steps=120):
    """
    Barre style 'avis' : plus intense au centre, fade vers les bords.
    Simulé par rectangles + alpha-like via interpolation de couleur.
    """
    def hex_to_rgb(hx):
        hx = hx.lstrip("#")
        return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))

    cr, cg, cb = hex_to_rgb(center_hex)
    er, eg, eb = hex_to_rgb(edge_hex)

    step_w = w / steps
    mid = (steps - 1) / 2.0

    for i in range(steps):
        # distance normalisée au centre (0 au centre, 1 aux bords)
        d = abs(i - mid) / mid if mid != 0 else 0
        # courbe douce (plus proche visuellement de ton UI)
        t = d ** 1.7

        r = int(cr + (er - cr) * t)
        g = int(cg + (eg - cg) * t)
        b = int(cb + (eb - cb) * t)

        c.setFillColor(colors.Color(r/255, g/255, b/255))
        c.setStrokeColor(colors.Color(r/255, g/255, b/255))
        c.rect(x + i * step_w, y, step_w + 0.2, h, stroke=0, fill=1)



# ===============================================================
# CHARTS (Matplotlib -> PNG -> drawImage)
# ===============================================================

def draw_donut_chart(values, labels, out_path):
    plt.figure(figsize=(3.0, 3.0))
    plt.pie(
        values,
        labels=None,
        startangle=90,
        wedgeprops=dict(width=0.28),
    )
    centre = plt.Circle((0, 0), 0.55, fc="white")
    plt.gca().add_artist(centre)

    plt.gca().set_aspect("equal")  # <-- AJOUT CRITIQUE

    plt.tight_layout()
    plt.savefig(out_path, dpi=200, transparent=True)
    plt.close()
    return out_path


def draw_capital_graph(capital_history, out_path):
    """
    Bar chart style UI (comme ton img2).
    capital_history: list[{"age": ..., "capital": ...}]
    """
    ages = []
    capitals = []
    for x in (capital_history or []):
        try:
            ages.append(int(float(x.get("age"))))
            capitals.append(float(x.get("capital")))
        except Exception:
            pass

    if not ages or not capitals:
        ages = [45, 46, 47, 48, 49, 50]
        capitals = [0, 0, 0, 0, 0, 0]

    # tri au cas où
    pairs = sorted(zip(ages, capitals), key=lambda t: t[0])
    ages = [p[0] for p in pairs]
    capitals = [p[1] for p in pairs]

    plt.figure(figsize=(7.2, 3.1))
    ax = plt.gca()

    # Style "UI"
    ax.set_facecolor("white")
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_alpha(0.25)
    ax.spines["bottom"].set_alpha(0.25)

    # Barres (violet UI)
    ax.bar(ages, capitals, width=0.65, color="#4F46E5", alpha=0.95)

    # Grille légère (Y uniquement)
    ax.grid(axis="y", alpha=0.18)
    ax.grid(axis="x", alpha=0.0)

    # Ticks lisibles
    ax.tick_params(axis="x", labelsize=9)
    ax.tick_params(axis="y", labelsize=9)

    ax.set_xlabel("Âge", fontsize=11, labelpad=10)
    ax.set_ylabel("CHF", fontsize=11, labelpad=10)

    # marges propres
    ax.margins(x=0.02)

    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
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

    SHIFT_Y = -4.0 * cm   # NEGATIF = on descend. Ajuste: -1.5cm / -2.5cm etc.
    CARD_SHIFT_Y = -5.5 * cm  # négatif = on descend la carte uniquement


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
    logo_y = height - header_h - 2.6*cm + SHIFT_Y


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
    bar_h = 0.12 * cm
    bar_x = (width - bar_w) / 2
    bar_y = title_y - 1.75 * cm
    draw_gradient_bar(
        c,
        bar_x, bar_y,
        bar_w, bar_h,
        center_hex="#2563EB",
        edge_hex="#BFDBFE",
        steps=140
    )


    # =========================================================
    # CARTE CLIENT (blanche + ombre) comme tes cards UI (img3)
    # =========================================================
    card_w = width * 0.70
    card_h = 7.7 * cm
    card_x = (width - card_w) / 2
    card_y = bar_y - 5.2 * cm + CARD_SHIFT_Y


    # ombre + carte
    draw_shadow_card(c, card_x, card_y, card_w, card_h, r=16, fill=WHITE, stroke=LIGHT)

    # contenu
    # contenu (lignes propres)
    x = card_x + 1.2*cm
    y = card_y + card_h - 1.35*cm
    line = 0.95*cm  # espacement entre lignes

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, f"Client : {prenom} {nom}".strip())

    c.setFont("Helvetica", 11)
    y -= line
    if age_actuel is not None:
        c.drawString(x, y, f"Âge actuel : {age_actuel} ans")

    y -= line
    if age_retraite is not None:
        c.drawString(x, y, f"Départ prévu : {age_retraite} ans")

    # ligne "rapport généré" propre, plus petite et grise
    y -= line
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Rapport généré le : {date_str}")

    y -= line
    c.setFillColor(BLACK)
    c.setFont("Helvetica", 11)
    c.drawString(x, y, f"Année de référence : {year}")

    y -= line
    c.drawString(x, y, "Type de rapport : Projection AVS & LPP (estimative)")

    # Référence dossier (simple et pro)
    ref = f"MRS-{today.strftime('%Y%m%d')}-{(prenom[:1] + nom[:1]).upper() if prenom and nom else 'XX'}"
    y -= line
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Référence : {ref}")


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
    avs_detail = pdf.get("avs_detail", {}) if isinstance(pdf, dict) else {}

    total_m = s.get("total_mensuel")
    avs_m = s.get("avs_mensuel")
    lpp_m = s.get("lpp_mensuel")
    part_avs = s.get("part_avs_pct")
    part_lpp = s.get("part_lpp_pct")

    # Bloc orange (données AVS détail)
    annees_manquantes = avs_detail.get("annees_manquantes")
    impact_pct = avs_detail.get("impact_pct")
    rente_complete = avs_detail.get("rente_complete")
    rente_finale = avs_detail.get("rente_finale")

    # perte sur 20 ans = (écart mensuel) * 12 * 20
    loss_20 = None
    rc = _to_float(rente_complete)
    rf = _to_float(rente_finale)
    if rc is not None and rf is not None:
        diff_m = max(0.0, rc - rf)
        loss_20 = diff_m * 12.0 * 20.0

    # =========================================================
    # FOND
    # =========================================================
    c.setFillColor(BG)
    c.rect(0, 0, width, height, stroke=0, fill=1)

    draw_top_confidential(c, width, height)

    # =========================================================
    # PARAMÈTRES
    # =========================================================
    LIFT = 1.1 * cm  # remonte légèrement l'ensemble de P2 (ajuste +/- 0.2 si besoin)

    base_container_w = width - 6 * cm
    container_w = width - 3.5 * cm
    scale = container_w / base_container_w
    font_scale = min(scale, 1.10)

    container_x = (width - container_w) / 2
    container_y = 3.1 * cm + LIFT
    container_h = height - 6.8 * cm

    pad = 1.2 * cm
    inner_x = container_x + pad
    inner_w = container_w - 2 * pad
    top_y = container_y + container_h - pad

    # =========================================================
    # TITRE
    # =========================================================
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(PRIMARY)
    c.drawString(2 * cm, height - 3.3 * cm + LIFT, "SYNTHÈSE GLOBALE")

    # =========================================================
    # DESSINE LE CONTAINER EN PREMIER (visuel)
    # =========================================================
    draw_shadow_card(c, container_x, container_y, container_w, container_h, r=18, fill=WHITE, stroke=LIGHT)

    # =========================================================
    # CARTE TOTAL
    # =========================================================
    total_h = 3.6 * cm * scale
    total_y = top_y - total_h
    draw_shadow_card(c, inner_x, total_y, inner_w, total_h, r=18, fill=PRIMARY, stroke=PRIMARY)

    c.setFillColor(WHITE)
    c.setFont("Helvetica", 12 * font_scale)
    c.drawCentredString(inner_x + inner_w / 2, total_y + total_h - 1.05 * cm * scale,
                        "Votre revenu mensuel total à la retraite")

    c.setFont("Helvetica-Bold", 34 * font_scale)
    c.drawCentredString(inner_x + inner_w / 2, total_y + 1.15 * cm * scale,
                        f"{fmt_int(total_m)} CHF" if total_m is not None else "—")

    # =========================================================
    # AVS + LPP
    # =========================================================
    gap = 0.8 * cm * scale
    small_h = 3.2 * cm * scale
    small_w = (inner_w - gap) / 2
    small_y = total_y - (1.2 * cm * scale) - small_h

    draw_shadow_card(c, inner_x, small_y, small_w, small_h, r=16, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12 * font_scale)
    c.drawString(inner_x + 1.0 * cm * scale, small_y + small_h - 1.1 * cm * scale, "AVS (1er Pilier)")
    c.setFont("Helvetica-Bold", 20 * font_scale)
    c.drawString(inner_x + 1.0 * cm * scale, small_y + 1.25 * cm * scale,
                 f"{fmt_int(avs_m)} CHF" if avs_m is not None else "—")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5 * font_scale)
    c.drawString(inner_x + 1.0 * cm * scale, small_y + 0.6 * cm * scale,
                 f"{fmt_pct(part_avs, 1)} de votre revenu" if part_avs is not None else "")

    lpp_x = inner_x + small_w + gap
    draw_shadow_card(c, lpp_x, small_y, small_w, small_h, r=16, fill=WHITE, stroke=LIGHT)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12 * font_scale)
    c.drawString(lpp_x + 1.0 * cm * scale, small_y + small_h - 1.1 * cm * scale, "LPP (2ème Pilier)")
    c.setFont("Helvetica-Bold", 20 * font_scale)
    c.drawString(lpp_x + 1.0 * cm * scale, small_y + 1.25 * cm * scale,
                 f"{fmt_int(lpp_m)} CHF" if lpp_m is not None else "—")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5 * font_scale)
    c.drawString(lpp_x + 1.0 * cm * scale, small_y + 0.6 * cm * scale,
                 f"{fmt_pct(part_lpp, 1)} de votre revenu" if part_lpp is not None else "")

    # =========================================================
    # ORANGE (en bas du container)
    # =========================================================
    missing = int(_to_float(annees_manquantes) or 0)
    warn_h = 2.8 * cm * scale
    bottom_pad = 0.6 * cm * scale
    warn_y = container_y + pad + bottom_pad if missing > 0 else None

        # =========================================================
    # DONUT (auto-fit entre AVS/LPP et ORANGE)
    # => impossible de manger AVS/LPP
    # =========================================================
    desired_donut_h = 6.2 * cm * scale
    gap_donut = 0.9 * cm * scale   # espace sous AVS/LPP
    gap_warn  = 1.2 * cm * scale   # espace entre donut et orange

    # limite haute: sous AVS/LPP
    donut_top_limit = small_y - gap_donut

    # limite basse: au-dessus de l'orange (si orange existe)
    if missing > 0 and warn_y is not None:
        donut_min_y = warn_y + warn_h + gap_warn
    else:
        donut_min_y = container_y + pad + (0.6 * cm * scale)

    # hauteur dispo réelle
    available_h = donut_top_limit - donut_min_y
    if available_h < 2.8 * cm * scale:
        # si vraiment trop serré, on réduit un peu les gaps plutôt que d'overlap
        gap_donut = 0.6 * cm * scale
        gap_warn  = 0.8 * cm * scale
        donut_top_limit = small_y - gap_donut
        if missing > 0 and warn_y is not None:
            donut_min_y = warn_y + warn_h + gap_warn
        available_h = donut_top_limit - donut_min_y

    donut_h = min(desired_donut_h, max(2.8 * cm * scale, available_h))

    # position: collé au plus haut possible, mais sans dépasser
    donut_y = donut_top_limit - donut_h
    if donut_y < donut_min_y:
        donut_y = donut_min_y  # sécurité finale

    draw_card(c, inner_x, donut_y, inner_w, donut_h, r=18, fill=WHITE, stroke=LIGHT)

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.5 * font_scale)
    c.drawString(inner_x + 1.0 * cm * scale, donut_y + donut_h - 1.1 * cm * scale, "Répartition de vos revenus")

    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5 * font_scale)
    c.drawString(inner_x + 1.0 * cm * scale, donut_y + (donut_h * 0.62),
                 f"AVS (1er pilier) : {fmt_pct(part_avs, 1)}" if part_avs is not None else "AVS (1er pilier)")
    c.drawString(inner_x + 1.0 * cm * scale, donut_y + (donut_h * 0.42),
                 f"LPP (2ème pilier) : {fmt_pct(part_lpp, 1)}" if part_lpp is not None else "LPP (2ème pilier)")

    donut_path = "donut_tmp.png"
    try:
        v0 = _to_float(avs_m) or 0.0
        v1 = _to_float(lpp_m) or 0.0
        values = [v0, v1]
        if values[0] + values[1] <= 0:
            values = [1, 1]

        draw_donut_chart(values, ["AVS", "LPP"], donut_path)

        # donut image doit rester carrée, mais adaptée à la hauteur dispo
        donut_size = min(5.2 * cm * scale, donut_h - 1.2 * cm * scale)
        donut_size = max(2.0 * cm * scale, donut_size)  # plancher pour rester lisible

        donut_x = inner_x + inner_w - donut_size - 1.0 * cm * scale
        donut_img_y = donut_y + (donut_h - donut_size) / 2

        c.drawImage(donut_path, donut_x, donut_img_y, width=donut_size, height=donut_size, mask="auto")
    finally:
        if os.path.exists(donut_path):
            os.remove(donut_path)

    # =========================================================
    # DESSINE ORANGE EN DERNIER (au-dessus de tout)
    # =========================================================
    if missing > 0 and warn_y is not None:
        draw_card(c, inner_x, warn_y, inner_w, warn_h, r=14, fill=WARN_BG, stroke=colors.HexColor("#FDE68A"))

        c.setFillColor(WARN_TX)
        c.setFont("Helvetica-Bold", 11.5 * font_scale)
        c.drawString(inner_x + 1.0 * cm * scale, warn_y + warn_h - 1.05 * cm * scale,
                     f"{missing} année{'s' if missing > 1 else ''} manquante{'s' if missing > 1 else ''}")

        c.setFont("Helvetica", 10.5 * font_scale)
        ip = fmt_pct(impact_pct, 1) if impact_pct is not None else "—"
        loss_txt = fmt_chf(loss_20, 0) if loss_20 is not None else "—"

        c.drawString(inner_x + 1.0 * cm * scale, warn_y + 1.25 * cm * scale,
                     f"Votre rente AVS est réduite de {ip}.")
        c.drawString(inner_x + 1.0 * cm * scale, warn_y + 0.55 * cm * scale,
                     f"Sur 20 ans de retraite, cela représente une perte de {loss_txt}.")

    draw_footer(c, width)
    c.showPage()


# ===============================================================
# P3 — AVS DÉTAILLÉ
# ===============================================================

def page_avs(c, avs):
    width, height = A4

    # =========================
    # Fond + header (comme P2)
    # =========================
    c.setFillColor(BG)
    c.rect(0, 0, width, height, stroke=0, fill=1)
    draw_top_confidential(c, width, height)

    # =========================
    # Titre (PRIMARY, MAJ)
    # =========================
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(PRIMARY)
    c.drawString(2 * cm, height - 3.3 * cm, "DÉTAIL AVS")

    # =========================
    # Container global (comme P2)
    # =========================
    container_w = width - 3.5 * cm
    container_x = (width - container_w) / 2
    container_y = 2.8 * cm
    container_h = height - 6.6 * cm

    draw_shadow_card(c, container_x, container_y, container_w, container_h, r=18, fill=WHITE, stroke=LIGHT)

    pad = 1.2 * cm
    inner_x = container_x + pad
    inner_w = container_w - 2 * pad
    top_y = container_y + container_h - pad

    # =========================
    # Données AVS
    # =========================
    annees_validees = avs.get("annees_validees")
    annees_manquantes = avs.get("annees_manquantes")
    ramd = avs.get("ramd")

    rente_complete = avs.get("rente_complete")
    rente_finale = avs.get("rente_finale")

    impact = avs.get("impact_pct")  # ex: 20.4
    bonifications = avs.get("bonifications", 0)

    # Optionnel (si tu l'ajoutes plus tard dans pdf_data["avs_detail"])
    salaire_moyen = avs.get("salaire_moyen") or avs.get("salaire_moyen_carriere")

    # Réduction théorique demandée: X années * 2.27%
    missing = int(_to_float(annees_manquantes) or 0)
    reduc_theorique = missing * 2.27  # en %

    # =========================
    # 4 cartes KPI (2x2)
    # =========================
        # =========================
    # 4 cartes KPI (2x2) — version demandée
    # =========================
    gap = 0.8 * cm
    card_w = (inner_w - gap) / 2
    card_h = 3.0 * cm

    y0 = top_y - card_h
    x1 = inner_x
    x2 = inner_x + card_w + gap

    # valeurs
    val_ok = int(_to_float(annees_validees) or 0)
    val_missing = int(_to_float(annees_manquantes) or 0)
    cotise_str = f"{val_ok}/44" if val_ok > 0 else "—/44"

    rente_avs_m = rente_finale  # CHF
    reduc_display = _to_float(impact)
    if reduc_display is None:
        reduc_display = reduc_theorique if val_missing > 0 else None

    # --- Carte 1: Années cotisées (35/44) + sous-texte "9 années manquantes"
    draw_shadow_card(c, x1, y0, card_w, card_h, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(x1 + 1.0 * cm, y0 + card_h - 1.1 * cm, "Années Cotisées")
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(x1 + 1.0 * cm, y0 + 1.15 * cm, cotise_str)
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(x1 + 1.0 * cm, y0 + 0.55 * cm, f"{val_missing} année{'s' if val_missing > 1 else ''} manquante{'s' if val_missing > 1 else ''}" if val_missing > 0 else "")

    # --- Carte 2: Rente mensuelle AVS
    draw_shadow_card(c, x2, y0, card_w, card_h, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(x2 + 1.0 * cm, y0 + card_h - 1.1 * cm, "Rente mensuelle AVS")
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x2 + 1.0 * cm, y0 + 1.15 * cm, fmt_chf(rente_avs_m, 0) if rente_avs_m is not None else "—")

    # Ligne 2
    y1 = y0 - (card_h + 1.0 * cm)

    # --- Carte 3: RAMD
    
    draw_shadow_card(c, x1, y1, card_w, card_h, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(x1 + 1.0 * cm, y1 + card_h - 1.1 * cm, "RAMD")
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x1 + 1.0 * cm, y1 + 1.15 * cm, fmt_chf(ramd, 0) if ramd is not None else "—")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(x1 + 1.0 * cm, y1 + 0.55 * cm, "Revenu annuel moyen")

    # --- Carte 4: Réduction + sous-texte "Dû aux lacunes"
    draw_shadow_card(c, x2, y1, card_w, card_h, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(x2 + 1.0 * cm, y1 + card_h - 1.1 * cm, "Réduction")
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(DANGER if reduc_display is not None else BLACK)
    c.drawString(x2 + 1.0 * cm, y1 + 1.15 * cm, f"-{fmt_pct(reduc_display, 1)}" if reduc_display is not None else "—")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(x2 + 1.0 * cm, y1 + 0.55 * cm, "Dû aux lacunes")

    # =========================
    # Détail du calcul (avec séparateurs)
    # =========================
    box_h = 8.2 * cm
    box_y = y1 - (1.1 * cm + box_h)

    draw_card(c, inner_x, box_y, inner_w, box_h, r=16, fill=WHITE, stroke=LIGHT)

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(inner_x + 1.0 * cm, box_y + box_h - 1.1 * cm, "Détail du calcul")

    # Lignes demandées
    rows = [
        ("Salaire moyen de carrière", fmt_chf(salaire_moyen, 0) if salaire_moyen is not None else "—"),
        ("Bonifications (éducation + assistance)", (("+" + fmt_chf(bonifications, 0)) if _to_float(bonifications) not in (None, 0) else "—")),
        ("RAMD calculé", fmt_chf(ramd, 0) if ramd is not None else "—"),
        ("Rente pour carrière complète", fmt_chf(rente_complete, 0) if rente_complete is not None else "—"),
        (f"Réduction ({missing} année{'s' if missing > 1 else ''} × 2,27%)", (f"-{fmt_pct(reduc_theorique, 1)}" if missing > 0 else "—")),
        ("Rente mensuelle finale", fmt_chf(rente_finale, 0) if rente_finale is not None else "—"),
    ]

    left_x = inner_x + 1.0 * cm
    right_x = inner_x + inner_w - 1.0 * cm

    # zone texte dans box
    start_y = box_y + box_h - 2.3 * cm
    row_h = 1.05 * cm

    for i, (lab, val) in enumerate(rows):
        yy = start_y - i * row_h

        # label
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 10.8)
        c.drawString(left_x, yy, lab)

        # valeur
        c.setFillColor(BLACK)
        c.setFont("Helvetica-Bold", 11.5)

        # couleurs spécifiques
        if "Bonifications" in lab and isinstance(val, str) and val.startswith("+"):
            c.setFillColor(colors.HexColor("#15803d"))
        if lab.startswith("Réduction") and isinstance(val, str) and val.startswith("-"):
            c.setFillColor(DANGER)

        c.drawRightString(right_x, yy, val)

        # divider léger sous chaque ligne (sauf la dernière)
        if i < len(rows) - 1:
            y_div = yy - 0.42 * cm
            draw_divider(c, left_x, y_div, right_x, color=LIGHT)

    # =========================
    # Bloc avertissement (orange) sous la box (dans le container)
    # =========================
    if missing > 0:
        warn_h = 2.6 * cm
        warn_y = box_y - (0.9 * cm + warn_h)

        # sécurité: ne pas sortir du container
        min_y = container_y + pad
        if warn_y < min_y:
            warn_y = min_y

        draw_card(c, inner_x, warn_y, inner_w, warn_h, r=14, fill=WARN_BG, stroke=colors.HexColor("#FDE68A"))
        c.setFillColor(WARN_TX)
        c.setFont("Helvetica-Bold", 11.5)
        c.drawString(inner_x + 1.0 * cm, warn_y + 1.65 * cm, f"{missing} année{'s' if missing > 1 else ''} manquante{'s' if missing > 1 else ''}")
        c.setFont("Helvetica", 10.5)
        ip = _to_float(impact)
        if ip is None:
            ip = reduc_theorique if missing > 0 else None
        c.drawString(inner_x + 1.0 * cm, warn_y + 0.85 * cm, f"Votre rente AVS est réduite de {fmt_pct(ip, 1) if ip is not None else '—'}.")

    draw_footer(c, width)
    c.showPage()


# ===============================================================
# P4 — LPP DÉTAILLÉ
# ===============================================================

def page_lpp(c, lpp):
    width, height = A4

    # Fond + header
    c.setFillColor(BG)
    c.rect(0, 0, width, height, stroke=0, fill=1)
    draw_top_confidential(c, width, height)

    # TITRE
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(PRIMARY)
    c.drawString(2 * cm, height - 2.7 * cm, "DÉTAIL LPP")

    # Container global
    container_w = width - 3.5 * cm
    container_x = (width - container_w) / 2
    container_y = 2.2 * cm
    container_h = height - 5.4 * cm
    draw_shadow_card(c, container_x, container_y, container_w, container_h, r=18, fill=WHITE, stroke=LIGHT)

    pad = 1.2 * cm
    inner_x = container_x + pad
    inner_w = container_w - 2 * pad
    top_y = container_y + container_h - pad
    bottom_y = container_y + pad  # bas "utile" à l'intérieur du container

    # Données LPP
    capital_actuel = lpp.get("capital_actuel", 0)
    capital_final = lpp.get("capital_final")
    rente_mensuelle = lpp.get("rente_mensuelle")
    annees_restantes = lpp.get("annees_restantes")
    history = lpp.get("capital_history", [])

    salaire_coordonne = lpp.get("salaire_coordonne")
    total_cotisations = lpp.get("total_cotisations")
    total_interets = lpp.get("total_interets")

    taux_conv = lpp.get("taux_conversion")
    if taux_conv is None:
        taux_conv = 6.8

    # =========================
    # 1) KPI (2x2)
    # =========================
    gap = 0.8 * cm
    card_w = (inner_w - gap) / 2
    card_h = 3.0 * cm

    y0 = top_y - card_h
    x1 = inner_x
    x2 = inner_x + card_w + gap

    # Capital actuel
    draw_shadow_card(c, x1, y0, card_w, card_h, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(x1 + 1.0 * cm, y0 + card_h - 1.1 * cm, "Capital Actuel")
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x1 + 1.0 * cm, y0 + 1.15 * cm, fmt_chf(capital_actuel, 0))

    # Capital projeté
    draw_shadow_card(c, x2, y0, card_w, card_h, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(x2 + 1.0 * cm, y0 + card_h - 1.1 * cm, "Capital Projeté")
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x2 + 1.0 * cm, y0 + 1.15 * cm, fmt_chf(capital_final, 0) if capital_final is not None else "—")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(x2 + 1.0 * cm, y0 + 0.55 * cm, "À 65 ans")

    # Ligne 2 KPI
    y1 = y0 - (card_h + 1.0 * cm)

    # Rente mensuelle
    draw_shadow_card(c, x1, y1, card_w, card_h, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(x1 + 1.0 * cm, y1 + card_h - 1.1 * cm, "Rente Mensuelle")
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x1 + 1.0 * cm, y1 + 1.15 * cm, fmt_chf(rente_mensuelle, 0) if rente_mensuelle is not None else "—")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(x1 + 1.0 * cm, y1 + 0.55 * cm, f"Taux : {taux_conv:.1f} %".replace(".", ","))

    # Années restantes
    draw_shadow_card(c, x2, y1, card_w, card_h, r=14, fill=WHITE, stroke=LIGHT)
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(x2 + 1.0 * cm, y1 + card_h - 1.1 * cm, "Années Restantes")
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x2 + 1.0 * cm, y1 + 1.15 * cm, f"{fmt_int(annees_restantes)} ans" if annees_restantes is not None else "—")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(x2 + 1.0 * cm, y1 + 0.55 * cm, "Jusqu'à la retraite")

    # =========================
    # 2) BOX "Détails des cotisations" (ANCRÉE EN BAS)
    # =========================
    box_h = 5.9 * cm
    box_y = bottom_y  # ancré bas
    draw_card(c, inner_x, box_y, inner_w, box_h, r=16, fill=WHITE, stroke=LIGHT)

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(inner_x + 1.0 * cm, box_y + box_h - 1.1 * cm, "Détails des cotisations")

    rows = [
        ("Salaire coordonné actuel", fmt_chf(salaire_coordonne, 0) if salaire_coordonne is not None else "—"),
        ("Total cotisations futures", (("+" + fmt_chf(total_cotisations, 0)) if _to_float(total_cotisations) not in (None, 0) else "—")),
        ("Total intérêts projetés", (("+" + fmt_chf(total_interets, 0)) if _to_float(total_interets) not in (None, 0) else "—")),
        ("Capital final projeté", fmt_chf(capital_final, 0) if capital_final is not None else "—"),
    ]

    left_x = inner_x + 1.0 * cm
    right_x = inner_x + inner_w - 1.0 * cm
    start_y = box_y + box_h - 2.3 * cm
    row_h = 1.05 * cm

    for i, (lab, val) in enumerate(rows):
        yy = start_y - i * row_h

        c.setFillColor(GRAY)
        c.setFont("Helvetica", 10.8)
        c.drawString(left_x, yy, lab)

        c.setFillColor(BLACK)
        c.setFont("Helvetica-Bold", 11.5)

        if isinstance(val, str) and val.startswith("+"):
            c.setFillColor(colors.HexColor("#15803d"))

        if lab == "Capital final projeté" and val != "—":
            c.setFillColor(PRIMARY)

        c.drawRightString(right_x, yy, val)

        if i < len(rows) - 1:
            y_div = yy - 0.42 * cm
            draw_divider(c, left_x, y_div, right_x, color=LIGHT)

    # =========================
    # 3) CARTE GRAPH (placée ENTRE KPI et BOX, donc jamais de débordement)
    # =========================
    gap_after_kpi = 1.0 * cm
    gap_above_box = 1.0 * cm

    graph_card_top = y1 - gap_after_kpi
    graph_card_y = box_y + box_h + gap_above_box
    graph_card_h = graph_card_top - graph_card_y

    # sécurité si l'espace devient trop petit
    if graph_card_h < 5.8 * cm:
        # on grignote un peu les gaps plutôt que de casser
        gap_after_kpi = 0.6 * cm
        gap_above_box = 0.7 * cm
        graph_card_top = y1 - gap_after_kpi
        graph_card_y = box_y + box_h + gap_above_box
        graph_card_h = graph_card_top - graph_card_y

    draw_card(c, inner_x, graph_card_y, inner_w, graph_card_h, r=16, fill=WHITE, stroke=LIGHT)

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(inner_x + 1.0 * cm, graph_card_y + graph_card_h - 1.1 * cm, "Projection de votre capital")

    # zone image: on réserve une "bande titre" fixe
    title_band = 1.4 * cm
    img_pad_bottom = 0.9 * cm
    img_pad_side = 0.9 * cm

    img_x = inner_x + img_pad_side
    img_y = graph_card_y + img_pad_bottom
    img_w = inner_w - 2 * img_pad_side
    img_h = graph_card_h - title_band - img_pad_bottom

    graph_path = "capital_lpp_tmp.png"
    try:
        draw_capital_graph(history, graph_path)
        c.drawImage(
            graph_path,
            img_x, img_y,
            width=img_w, height=img_h,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
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

    # Fond + header
    c.setFillColor(BG)
    c.rect(0, 0, width, height, stroke=0, fill=1)
    draw_top_confidential(c, width, height)

    # TITRE (PRIMARY + MAJ)
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(PRIMARY)
    c.drawString(2 * cm, height - 3.3 * cm, "SCÉNARIOS")

    # =========================
    # Container global (comme P2/P3/P4)
    # =========================
    container_w = width - 3.5 * cm
    container_x = (width - container_w) / 2
    container_y = 2.8 * cm
    container_h = height - 6.6 * cm
    draw_shadow_card(c, container_x, container_y, container_w, container_h, r=18, fill=WHITE, stroke=LIGHT)

    pad = 1.2 * cm
    inner_x = container_x + pad
    inner_w = container_w - 2 * pad
    top_y = container_y + container_h - pad

    # =========================
    # Texte intro (wrapping -> plus jamais coupé)
    # =========================
    intro_lines = [
        "Voici les scénarios d'optimisation possibles selon votre situation.",
        "Les calculs sont indicatifs et dépendent de votre situation fiscale exacte."
    ]
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    intro_y = top_y
    for line in intro_lines:
        c.drawString(inner_x, intro_y, line)
        intro_y -= 0.65 * cm

    # =========================
    # Extraction scénarios (inchangé)
    # =========================
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

    sans = scenarios.get("sans_rachat") or scenarios.get("sans") or {}
    rachat = scenarios.get("rachat_lpp") or scenarios.get("rachat") or {}

    # =========================
    # Cartes
    # =========================
    card_w = inner_w
    card_x = inner_x

    # Sans rachat
    y0 = intro_y - 0.9 * cm
    h_sans = 3.0 * cm
    draw_shadow_card(c, card_x, y0 - h_sans, card_w, h_sans, r=16, fill=WHITE, stroke=LIGHT)

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(card_x + 1.0 * cm, y0 - 1.1 * cm, "Sans rachat")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(card_x + 1.0 * cm, y0 - 2.0 * cm, "Situation actuelle projetée")

    sans_m = (sans.get("rente_mensuelle") if isinstance(sans, dict) else None) or safe_get(pdf, ["synthese", "total_mensuel"])
    if sans_m is not None:
        c.setFillColor(colors.HexColor("#15803d"))
        c.setFont("Helvetica-Bold", 16)
        c.drawRightString(card_x + card_w - 1.0 * cm, y0 - 1.25 * cm, f"{fmt_int(sans_m)} CHF")
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 9.5)
        c.drawRightString(card_x + card_w - 1.0 * cm, y0 - 1.95 * cm, "rente mensuelle")

    # ESPACE entre les deux blocs (léger)
    gap_cards = 0.8 * cm

    # Rachat LPP optimisé
    y1_top = (y0 - h_sans) - gap_cards
    h_rachat = 4.2 * cm
    draw_shadow_card(
        c, card_x, y1_top - h_rachat, card_w, h_rachat,
        r=16, fill=colors.HexColor("#ECFDF5"), stroke=colors.HexColor("#bbf7d0")
    )

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(card_x + 1.0 * cm, y1_top - 1.1 * cm, "Rachat LPP optimisé")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(card_x + 1.0 * cm, y1_top - 1.9 * cm, "Rachat étalé sur 5 ans  •  Recommandé")

    rachat_m = (rachat.get("rente_mensuelle") if isinstance(rachat, dict) else None)
    if rachat_m is not None:
        c.setFillColor(colors.HexColor("#15803d"))
        c.setFont("Helvetica-Bold", 16)
        c.drawRightString(card_x + card_w - 1.0 * cm, y1_top - 1.25 * cm, f"{fmt_int(rachat_m)} CHF")
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 9.5)
        c.drawRightString(card_x + card_w - 1.0 * cm, y1_top - 1.95 * cm, "rente mensuelle")

    # 4 métriques
    def rget(key):
        return rachat.get(key) if isinstance(rachat, dict) else None

    metrics = [
        ("Coût total", rget("cout_total")),
        ("Économie impôt", rget("economie_impot")),
        ("Gain mensuel", rget("gain_mensuel")),
        ("Gain sur 20 ans", rget("gain_20_ans")),
    ]

    mx = card_x + 1.0 * cm
    my = y1_top - 3.1 * cm
    col_w = (card_w - 2.0 * cm) / 4

    for i, (lab, val) in enumerate(metrics):
        x = mx + i * col_w
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 9.5)
        c.drawString(x, my + 0.65 * cm, lab)
        c.setFillColor(BLACK)
        c.setFont("Helvetica-Bold", 11.5)

        if val is None:
            c.drawString(x, my, "—")
            continue

        vv = _to_float(val)
        if vv is None:
            c.drawString(x, my, str(val))
            continue

        if "impôt" in lab.lower() and vv < 0:
            c.setFillColor(colors.HexColor("#15803d"))
        if "gain" in lab.lower() and vv > 0:
            c.setFillColor(colors.HexColor("#2563eb"))

        c.drawString(x, my, fmt_chf(vv, 0))

    # Prochaines étapes
    y2_top = (y1_top - h_rachat) - 1.2 * cm
    h_next = 3.8 * cm
    draw_card(c, card_x, y2_top - h_next, card_w, h_next, r=16, fill=WHITE, stroke=LIGHT)

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(card_x + 1.0 * cm, y2_top - 1.1 * cm, "Prochaines étapes")

    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.5)
    c.drawString(card_x + 1.0 * cm, y2_top - 2.0 * cm,
                 "Pour mettre en place ces optimisations, vous devrez fournir vos documents")
    c.drawString(card_x + 1.0 * cm, y2_top - 2.6 * cm,
                 "officiels (extrait de compte AVS, certificats LPP). Notre équipe vous")
    c.drawString(card_x + 1.0 * cm, y2_top - 3.2 * cm,
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
