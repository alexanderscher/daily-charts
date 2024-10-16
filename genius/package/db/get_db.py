from .db_conn import (
    SessionLocal,
)
from .models import SignedArtists
from .models import MajorLabels
from .models import RosterArtists
from .models import RosterSongs
from .models import Prospect
from db.models import GeniusCharts
from datetime import datetime
from pytz import timezone
from sqlalchemy import exists
import pandas as pd


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

    def get_genius_charts(self):
        session = SessionLocal()

        try:
            pacific_tz = timezone("America/Los_Angeles")
            today_str = datetime.now(pacific_tz).strftime("%Y-%m-%d")

            recent_date = (
                session.query(GeniusCharts.date)
                .filter(GeniusCharts.date != today_str)
                .order_by(GeniusCharts.date.desc())
                .first()
            )

            if recent_date:
                most_recent_date_str = recent_date[0].strftime("%Y-%m-%d")
                print(most_recent_date_str)

                charts = (
                    session.query(GeniusCharts)
                    .filter(GeniusCharts.date == most_recent_date_str)
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
                        "views": chart.views,
                        "movement": chart.movement,
                        "link": chart.link,
                        "label": chart.label,
                        "date": chart.date,
                    }
                    for chart in charts
                ]

                df = pd.DataFrame(data)

                return df
            else:
                print("No recent date found in Apple charts.")
                return None

        except Exception as e:
            print(f"An error occurred: {e}")
            return None

        finally:
            session.close()

    def insert_genius_charts(self, data):
        session = SessionLocal()
        pacific_tz = timezone("America/Los_Angeles")
        current_date = datetime.now(pacific_tz).date()

        try:
            date_exists = session.query(
                exists().where(GeniusCharts.date == current_date)
            ).scalar()

            if not date_exists:

                for (
                    chart,
                    position,
                    artist,
                    song,
                    unsigned,
                    l2tk,
                    views,
                    movement,
                    link,
                    label,
                ) in data.itertuples(index=False):

                    movement = str(movement) if movement is not None else "0"
                    label = str(label)

                    new_chart_entry = GeniusCharts(
                        chart=chart,
                        position=position,
                        artist=artist,
                        song=song,
                        unsigned=unsigned,
                        l2tk=l2tk,
                        views=views,
                        movement=movement,
                        link=link,
                        label=label,
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
