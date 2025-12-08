from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors

def generer_pdf_estimation(donnees, resultats, output="test.pdf"):
    c = canvas.Canvas(output, pagesize=A4)
    width, height = A4

    # Titre
    c.setFont("Helvetica-Bold", 24)
    c.drawString(2*cm, height - 2*cm, "TEST PDF – Titre OK ?")

    # Sous-titre
    c.setFont("Helvetica", 14)
    c.drawString(2*cm, height - 3.5*cm, "Sous-titre affiché ?")

    # Ligne rouge
    c.setStrokeColor(colors.red)
    c.setLineWidth(3)
    c.line(2*cm, height - 4.5*cm, width - 2*cm, height - 4.5*cm)

    # Texte simple
    c.setFont("Helvetica", 12)
    c.drawString(2*cm, height - 6*cm, "Si tu vois ceci, le canvas fonctionne.")

    # Une forme rouge (simulateur de bannière)
    c.setFillColor(colors.red)
    c.rect(0, 0, width, 4*cm, fill=True, stroke=False)

    c.showPage()
    c.save()

    return output
