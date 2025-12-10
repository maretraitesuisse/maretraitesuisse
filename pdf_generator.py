def draw_cover_page(c, width, height):
    # ===== DIAGONALE ROUGE =====
    path = c.beginPath()
    path.moveTo(0, height)
    path.lineTo(width, height - 3*cm)
    path.lineTo(width, height)
    path.lineTo(0, height)
    path.close()
    c.setFillColor(PRIMARY)
    c.drawPath(path, fill=1, stroke=0)

    # ===== LOGO =====
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        logo = ImageReader(logo_path)

        c.drawImage(
            logo,
            (width - 5*cm)/2,          # centre horizontal
            height - 15*cm,            # position verticale mieux placée
            width=5*cm,
            preserveAspectRatio=True,
            mask='auto'
        )
    except Exception as e:
        print("Erreur logo:", e)

    # ===== TITRE =====
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(2*cm, height - 8.5*cm,
                 "Étude de prévoyance – Ma Retraite Suisse")

    # ===== SOUS-TITRE =====
    c.setFont("Helvetica", 16)
    c.drawString(2*cm, height - 10.2*cm,
                 "AVS · LPP · 3e pilier · Projection financière")

    # ===== ANNÉE =====
    annee = datetime.datetime.now().year
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(2*cm, height - 11.8*cm,
                 f"Rapport {annee}")

    # ===== BANNIÈRE EN BAS =====
    try:
        banner_path = os.path.join(os.path.dirname(__file__), "ban.jpg")
        banner = ImageReader(banner_path)

        banner_height = height * 0.40  # belle hauteur premium
        banner_y = 0 + 20              # pour la barre rouge en dessous

        c.drawImage(
            banner,
            0,
            banner_y,
            width=width,
            height=banner_height,
            preserveAspectRatio=True,
            mask='auto'
        )

        # ===== BARRE ROUGE EN BAS =====
        c.setFillColor(PRIMARY)
        c.rect(0, 0, width, 20, fill=True, stroke=False)

    except Exception as e:
        print("Erreur bannière:", e)

    c.showPage()
