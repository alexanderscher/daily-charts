from .db_conn import (
    SessionLocal,
)
from pytz import timezone

from .models import SignedArtists
from .models import MajorLabels
from .models import RosterArtists
from .models import RosterSongs
from .models import Prospect
from .models import SpotifyCharts
from sqlalchemy import exists
import pandas as pd
from datetime import datetime, timedelta


class FetchDB:

    def __init__(self):
        pass

    def get_signed_artists(self):
        session = SessionLocal()

        try:
            artists = session.query(SignedArtists).all()
            signed = [artist.name for artist in artists]
            return signed

        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            session.close()

    def get_major_labels(self):
        session = SessionLocal()

        try:
            labels = session.query(MajorLabels).all()
            l = [label.name for label in labels]
            return l

        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            session.close()

    def get_roster_artists(self):
        session = SessionLocal()

        try:
            artists = session.query(RosterArtists).all()
            roster = [artist.name for artist in artists]
            return roster

        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            session.close()

    def get_pub_songs(self):
        session = SessionLocal()

        try:
            roster = session.query(RosterSongs).all()
            tracks = [s.song for s in roster]
            return tracks

        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            session.close()

    def get_pub_albums(self):
        session = SessionLocal()

        try:
            roster = session.query(RosterSongs).all()
            albums = [a.album for a in roster]
            return albums

        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            session.close()

    def get_pub_artists(self):
        session = SessionLocal()

        try:
            roster = session.query(RosterSongs).all()
            artist = [a.artist for a in roster]
            return artist

        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            session.close()

    def get_prospects(self):
        session = SessionLocal()

        try:
            roster = session.query(Prospect).all()
            prospect = [p.name for p in roster]
            return prospect

        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            session.close()

    def insert_spotify_charts(self, data):
        session = SessionLocal()
        pacific_tz = timezone("America/Los_Angeles")
        current_date = datetime.now(pacific_tz).date()

        try:
            date_exists = session.query(
                exists().where(SpotifyCharts.date == current_date)
            ).scalar()

            if not date_exists:

                for (
                    chart,
                    position,
                    artist,
                    song,
                    unsigned,
                    l2tk,
                    movement,
                    days,
                    peak,
                    link,
                    label,
                    chart_date,
                ) in data.itertuples(index=False):

                    movement = str(movement) if movement is not None else "0"
                    label = str(label)

                    new_chart_entry = SpotifyCharts(
                        chart=chart,
                        position=position,
                        artist=artist,
                        song=song,
                        unsigned=unsigned,
                        l2tk=l2tk,
                        movement=movement,
                        days=days,
                        peak=peak,
                        link=link,
                        label=label,
                        chart_date=chart_date,
                        date=current_date,
                    )

                    session.add(new_chart_entry)

                session.commit()
                print("Data inserted successfully.")
            else:
                print("Data for the current date already exists in the database.")
        except Exception as e:
            session.rollback()
            print(f"An error occurred: {e}")
            raise e

        finally:
            session.close()

    def get_spotify_charts(self):
        session = SessionLocal()

        try:
            pacific_tz = timezone("America/Los_Angeles")
            today_str = datetime.now(pacific_tz).strftime("%Y-%m-%d")

            recent_date = (
                session.query(SpotifyCharts.date)
                .filter(SpotifyCharts.date != today_str)
                .order_by(SpotifyCharts.date.desc())
                .first()
            )

            if recent_date:
                most_recent_date_str = recent_date[0].strftime("%Y-%m-%d")
                print(most_recent_date_str)

                charts = (
                    session.query(SpotifyCharts)
                    .filter(SpotifyCharts.date == most_recent_date_str)
                    .all()
                )

                data = [
                    {
                        "id": chart.id,
                        "chart": chart.chart,
                        "position": chart.position,
                        "artist": chart.artist,
                        "song": chart.song,
                        "unsigned": chart.unsigned,
                        "l2tk": chart.l2tk,
                        "movement": chart.movement,
                        "days": chart.days,
                        "peak": chart.peak,
                        "link": chart.link,
                        "label": chart.label,
                        "chart_date": chart.chart_date,
                        "date": chart.date,
                    }
                    for chart in charts
                ]

                df = pd.DataFrame(data)

                return df
            else:
                print("No recent date found in Spotify charts.")
                return None

        except Exception as e:
            print(f"An error occurred: {e}")
            return None

        finally:
            session.close()
