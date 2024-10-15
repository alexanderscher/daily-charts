from sqlalchemy import Column, Integer, String, Date
from .db_conn import Base


class MajorLabels(Base):
    __tablename__ = "major_labels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)


class SignedArtists(Base):
    __tablename__ = "signed_artists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
