from sqlalchemy import Column, Integer, String, Float, Text
from database import Base

class Airport(Base):
    __tablename__ = "airports"
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    city = Column(String(100))
    country = Column(String(100))
    iata_code = Column(String(3))
    latitude = Column(Float)
    longitude = Column(Float)
    embedding = Column(Text)
