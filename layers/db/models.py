from sqlalchemy import Column, Integer, String, Date
from layers.db.db_conn import Base


class ApplePeaks(Base):
    __tablename__ = "apple_peaks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    streams = Column(Integer)
    peak_date = Column(Date)


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


class SpotifyPeaks(Base):
    __tablename__ = "spotify_peaks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    streams = Column(Integer)
    peak_date = Column(Date)
