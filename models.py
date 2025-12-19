from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    prenom = Column(String, nullable=False)
    nom = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    telephone = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"))

    statut_civil = Column(String)
    statut_pro = Column(String)

    age_actuel = Column(Integer)
    age_retraite = Column(Integer)

    salaire_actuel = Column(Numeric)
    salaire_moyen = Column(Numeric)

    annees_cotisees = Column(Integer)
    annees_be = Column(Integer)
    annees_ba = Column(Integer)

    capital_lpp = Column(Numeric)
    rente_conjoint = Column(Numeric)

    resultat = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())

