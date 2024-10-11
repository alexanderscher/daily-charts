from sqlalchemy import Column, Integer, String, Date
from .db_conn import Base


class MajorLabels(Base):
    __tablename__ = "major_labels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)


class RosterArtists(Base):
    __tablename__ = "roster_artists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)


class RosterSongs(Base):
    __tablename__ = "roster_songs"
    id = Column(Integer, primary_key=True, index=True)
    song = Column(String)
    artist = Column(String)
    album = Column(String)


class SignedArtists(Base):
    __tablename__ = "signed_artists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)


class Prospect(Base):
    __tablename__ = "prospects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
