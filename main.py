from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# --- Variables d'environnement ---
load_dotenv()
creds_path = os.getenv("GOOGLE_CREDS_PATH")
sheet_name = os.getenv("SHEET_NAME")

# --- Connexion à Google Sheets ---
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open(sheet_name).sheet1
print(f"Connexion OK à la feuille : {sheet_name}")

# --- FastAPI app ---
app = FastAPI()

# --- Modèle des données attendues ---
class FormData(BaseModel):
    prenom: str
    nom: str
    email: str
    telephone: str
    situation: str
    date_naissance: str
    revenu: str
    annees_suisse: str
    canton: str
    souhaits: str

# --- Endpoint pour recevoir les données ---
@app.post("/submit")
def submit_form(data: FormData):
    try:
        row = [
            data.prenom,
            data.nom,
            data.email,
            data.telephone,
            data.situation,
            data.date_naissance,
            data.revenu,
            data.annees_suisse,
            data.canton,
            data.souhaits
        ]
        sheet.append_row(row)
        return {"status": "success", "message": "Données ajoutées à Google Sheets !"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
