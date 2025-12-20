from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func

from database import Base


class Avis(Base):
    __tablename__ = "avis"

    id = Column(Integer, primary_key=True, index=True)

    prenom = Column(String, nullable=False)
    nom = Column(String, nullable=False)
    email = Column(String, nullable=False)

    canton = Column(String, nullable=False)
    ville = Column(String, nullable=False)

    note = Column(Integer, nullable=False)  # 1 à 5
    commentaire = Column(Text, nullable=False)

    published = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
