from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from database import Base

class Avis(Base):
    __tablename__ = "avis"

    id = Column(Integer, primary_key=True)
    prenom = Column(String(100), nullable=False)
    nom = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)

    ville = Column(String(100), nullable=False)
    canton = Column(String(100), nullable=False)

    note = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)

    status = Column(String(20), default="pending")  # pending | approved | rejected

    created_at = Column(DateTime, server_default=func.now())
    published_at = Column(DateTime, nullable=True)

